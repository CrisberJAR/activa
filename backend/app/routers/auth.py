from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Usuario
from app.security import autenticar, crear_token, usuario_api
from app.services import auditoria
from app.templating import templates

router = APIRouter()


def destino(usuario: Usuario) -> str:
    return "/panel"


def ingresar(db: Session, email: str, password: str) -> tuple[Usuario | None, str | None]:
    """Verifica la contraseña respetando el límite de intentos y deja todo en la auditoría."""
    email = email.strip().lower()[:160]
    if auditoria.esta_bloqueado(db, email):
        auditoria.registrar(db, "login_bloqueado", email=email)
        db.commit()
        return None, auditoria.mensaje_bloqueo()
    usuario = autenticar(db, email, password)
    if not usuario:
        auditoria.registrar(db, "login_fallido", email=email)
        db.commit()
        return None, "Correo o contraseña incorrectos"
    auditoria.registrar(db, "login_ok", usuario)
    db.commit()
    return usuario, None


@router.get("/login")
def login_form(request: Request, db: Session = Depends(get_db)):
    usuario_id = request.session.get("usuario_id")
    usuario = db.get(Usuario, usuario_id) if usuario_id else None
    if usuario:
        return RedirectResponse(destino(usuario), status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", {"error": None, "email": ""})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    usuario, error = ingresar(db, email, password)
    if error:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": error, "email": email},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS if error == auditoria.mensaje_bloqueo() else status.HTTP_401_UNAUTHORIZED,
        )
    request.session.clear()
    request.session["usuario_id"] = usuario.id
    return RedirectResponse(destino(usuario), status.HTTP_303_SEE_OTHER)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status.HTTP_303_SEE_OTHER)


# ---------- API (app móvil) ----------

@router.post("/api/auth/token")
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario, error = ingresar(db, form.username, form.password)
    if error:
        codigo = status.HTTP_429_TOO_MANY_REQUESTS if error == auditoria.mensaje_bloqueo() else status.HTTP_401_UNAUTHORIZED
        raise HTTPException(codigo, error)
    return {"access_token": crear_token(usuario), "token_type": "bearer", "rol": usuario.rol}


@router.get("/api/auth/yo")
def yo(usuario: Usuario = Depends(usuario_api)):
    return {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email, "rol": usuario.rol}
