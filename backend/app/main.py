import logging
import threading
from urllib.parse import urlsplit
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR, settings
from app.db import SessionLocal, get_db
from app.routers import (admin, analisis, auth, bloques, campanas, chat, clima, encuestas, interesados, menu, negocios,
                         prospectos, publico, recuperaciones, riesgos)
from app.services import ml
from app.templating import templates

log = logging.getLogger("activa")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # Carga el modelo de ML en segundo plano para que el primer análisis no espere
    threading.Thread(target=ml.cargar_modelo, daemon=True).start()
    planificador = None
    if settings.scheduler_activo:
        from app.scheduler import iniciar

        planificador = iniciar()
    yield
    if planificador:
        planificador.shutdown(wait=False)


app = FastAPI(title="ACTIVA 360° – Plataforma inteligente de inclusión y gestión financiera", lifespan=ciclo_de_vida)

# Sesión de la web en cookie firmada (dura 8 horas)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, max_age=8 * 3600, same_site="lax", https_only=settings.cookie_segura)
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")

app.include_router(auth.router)
app.include_router(menu.router)
app.include_router(bloques.router)
app.include_router(encuestas.router)
app.include_router(clima.router)
app.include_router(analisis.router)
app.include_router(campanas.router)
app.include_router(publico.router)
app.include_router(chat.router)
app.include_router(interesados.router)
# ACTIVA 360°
app.include_router(prospectos.router)
app.include_router(negocios.router)
app.include_router(riesgos.router)
app.include_router(recuperaciones.router)
app.include_router(admin.router)


@app.middleware("http")
async def proteger_csrf(request: Request, call_next):
    """Protección CSRF: un formulario de la web solo se acepta si viene de esta misma página.

    Complementa la cookie SameSite=Lax. Los navegadores envían Origin (o Referer) en los POST;
    si apunta a otro sitio, se rechaza. La API móvil usa token y no depende de la cookie.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and not request.url.path.startswith("/api/"):
        origen = request.headers.get("origin") or request.headers.get("referer")
        if origen:
            host_origen = urlsplit(origen).netloc
            if host_origen and host_origen != request.headers.get("host"):
                return JSONResponse({"detail": "Solicitud bloqueada: origen no permitido"}, status_code=403)
    return await call_next(request)


def _auditar_acceso_denegado(request: Request) -> None:
    """Deja en la auditoría los intentos de entrar a páginas sin permiso (usuario con sesión)."""
    usuario_id = request.session.get("usuario_id") if "session" in request.scope else None
    if not usuario_id:
        return
    try:
        with SessionLocal() as db:
            from app.models import Usuario
            from app.services.auditoria import registrar

            usuario = db.get(Usuario, usuario_id)
            if usuario:
                registrar(db, "acceso_denegado", usuario, f"{request.method} {request.url.path}"[:200])
                db.commit()
    except Exception:
        log.exception("No se pudo registrar el acceso denegado")


@app.exception_handler(StarletteHTTPException)
async def errores_http(request: Request, exc: StarletteHTTPException):
    # En la web mostramos una página amigable para "sin permiso"; la API responde JSON
    if exc.status_code == 403:
        _auditar_acceso_denegado(request)
        if not request.url.path.startswith("/api"):
            return templates.TemplateResponse(request, "403.html", {"mensaje": exc.detail}, status_code=403)
    return await http_exception_handler(request, exc)


@app.get("/api/salud")
def salud(db: Session = Depends(get_db)):
    """Verifica que el backend responde y que la base de datos (Supabase) está conectada."""
    try:
        db.execute(text("SELECT 1"))
        return {"estado": "ok", "base_de_datos": "conectada"}
    except Exception:
        # El detalle va al registro: esta ruta es pública y no debe mostrar datos de conexión
        log.exception("La base de datos no responde")
        return JSONResponse({"estado": "error", "base_de_datos": "sin conexión"}, status_code=503)
