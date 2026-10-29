from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Usuario
from app.security import autenticar, crear_token, usuario_api
from app.templating import templates

router = APIRouter()


def destino(usuario: Usuario) -> str:
    return "/gerente" if usuario.rol == "gerente" else "/asesor"


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
    usuario = autenticar(db, email, password)
    if not usuario:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Correo o contraseña incorrectos", "email": email},
            status_code=status.HTTP_401_UNAUTHORIZED,
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
    usuario = autenticar(db, form.username, form.password)
    if not usuario:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos")
    return {"access_token": crear_token(usuario), "token_type": "bearer", "rol": usuario.rol}


@router.get("/api/auth/yo")
def yo(usuario: Usuario = Depends(usuario_api)):
    return {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email, "rol": usuario.rol}
