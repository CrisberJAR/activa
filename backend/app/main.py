import logging
import threading
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
from app.db import get_db
from app.routers import analisis, auth, bloques, campanas, chat, clima, encuestas, interesados, menu, publico
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


app = FastAPI(title="ACTIVA – Diagnóstico estacional y campañas crediticias", lifespan=ciclo_de_vida)

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


@app.exception_handler(StarletteHTTPException)
async def errores_http(request: Request, exc: StarletteHTTPException):
    # En la web mostramos una página amigable para "sin permiso"; la API responde JSON
    if exc.status_code == 403 and not request.url.path.startswith("/api"):
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
