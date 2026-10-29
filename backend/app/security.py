"""Contraseñas, sesión web (cookie) y token JWT (app móvil)."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Usuario


def cifrar_password(password: str) -> str:
    # bcrypt solo usa los primeros 72 bytes
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verificar_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode()[:72], password_hash.encode())


def autenticar(db: Session, email: str, password: str) -> Usuario | None:
    usuario = db.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))
    if usuario and usuario.activo and verificar_password(password, usuario.password_hash):
        return usuario
    return None


# ---------- Web del asesor (sesión en cookie firmada) ----------

def usuario_web(request: Request, db: Session = Depends(get_db)) -> Usuario:
    usuario_id = request.session.get("usuario_id")
    usuario = db.get(Usuario, usuario_id) if usuario_id else None
    if not usuario or not usuario.activo:
        request.session.clear()
        raise HTTPException(status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return usuario


def requiere_rol(*roles: str):
    """Dependencia que deja pasar solo a los roles indicados."""

    def verificar(usuario: Usuario = Depends(usuario_web)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para ver esta página")
        return usuario

    return verificar


# ---------- API para la app móvil (token JWT) ----------

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def crear_token(usuario: Usuario) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_minutos)
    datos = {"sub": str(usuario.id), "rol": usuario.rol, "exp": expira}
    return jwt.encode(datos, settings.secret_key, algorithm="HS256")


oauth2_opcional = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

NO_AUTORIZADO = HTTPException(
    status.HTTP_401_UNAUTHORIZED, "Token inválido o vencido", headers={"WWW-Authenticate": "Bearer"}
)


def usuario_api(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> Usuario:
    try:
        datos = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise NO_AUTORIZADO
    usuario = db.get(Usuario, int(datos["sub"]))
    if not usuario or not usuario.activo:
        raise NO_AUTORIZADO
    return usuario


def usuario_web_o_api(
    request: Request, token: str | None = Depends(oauth2_opcional), db: Session = Depends(get_db)
) -> Usuario:
    """Acepta la sesión de la web o el token de la app (para la API de clima)."""
    usuario_id = request.session.get("usuario_id")
    usuario = db.get(Usuario, usuario_id) if usuario_id else None
    if usuario and usuario.activo:
        return usuario
    if token:
        return usuario_api(token, db)
    raise NO_AUTORIZADO
