"""Administración (solo gerente): usuarios y roles, y registro de auditoría."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalogos import ROLES_TEXTO
from app.db import get_db
from app.models import Auditoria, Usuario
from app.security import cifrar_password, requiere_rol
from app.services import auditoria
from app.templating import avisar, templates

router = APIRouter()
solo_gerente = requiere_rol("gerente")


# ---------- Usuarios ----------

def _pagina_usuarios(request, usuario, db, v=None, errores=None, status_code=200):
    usuarios = db.scalars(select(Usuario).order_by(Usuario.activo.desc(), Usuario.rol, Usuario.nombre)).all()
    return templates.TemplateResponse(
        request, "usuarios.html",
        {"usuario": usuario, "usuarios": usuarios, "v": v or {}, "errores": errores or {}},
        status_code=status_code,
    )


@router.get("/usuarios")
def usuarios(request: Request, usuario: Usuario = Depends(solo_gerente), db: Session = Depends(get_db)):
    return _pagina_usuarios(request, usuario, db)


@router.post("/usuarios")
def crear_usuario(
    request: Request,
    nombre: str = Form(""),
    email: str = Form(""),
    rol: str = Form(""),
    password: str = Form(""),
    usuario: Usuario = Depends(solo_gerente),
    db: Session = Depends(get_db),
):
    v = {"nombre": nombre.strip(), "email": email.strip().lower(), "rol": rol}
    errores = {}
    if len(v["nombre"]) < 3:
        errores["nombre"] = "Escribe el nombre completo"
    if "@" not in v["email"] or len(v["email"]) > 160:
        errores["email"] = "Correo inválido"
    elif db.scalar(select(Usuario).where(Usuario.email == v["email"])):
        errores["email"] = "Ya existe un usuario con ese correo"
    if rol not in ROLES_TEXTO:
        errores["rol"] = "Elige un rol"
    if len(password) < 10 or password.isalpha() or password.isdigit():
        errores["password"] = "Mínimo 10 caracteres, con letras y números"
    if errores:
        return _pagina_usuarios(request, usuario, db, v, errores, status.HTTP_422_UNPROCESSABLE_ENTITY)
    nuevo = Usuario(nombre=v["nombre"], email=v["email"], rol=rol, password_hash=cifrar_password(password))
    db.add(nuevo)
    db.flush()
    auditoria.registrar(db, "usuario_creado", usuario, f"usuario {nuevo.id} · rol {rol}")
    db.commit()
    avisar(request, f"Usuario {nuevo.email} creado como {ROLES_TEXTO[rol]}")
    return RedirectResponse("/usuarios", status.HTTP_303_SEE_OTHER)


@router.post("/usuarios/{usuario_id}/estado")
def activar_o_desactivar(
    usuario_id: int, request: Request, usuario: Usuario = Depends(solo_gerente), db: Session = Depends(get_db)
):
    otro = db.get(Usuario, usuario_id)
    if not otro:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    if otro.id == usuario.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "No puedes desactivar tu propia cuenta")
    otro.activo = not otro.activo
    auditoria.registrar(db, "usuario_activado" if otro.activo else "usuario_desactivado", usuario, f"usuario {otro.id}")
    db.commit()
    avisar(request, f"{otro.email}: {'activado' if otro.activo else 'desactivado'}")
    return RedirectResponse("/usuarios", status.HTTP_303_SEE_OTHER)


# ---------- Auditoría ----------

@router.get("/auditoria")
def ver_auditoria(
    request: Request,
    accion: str = "",
    usuario_id: str = "",
    pagina: int = 1,
    usuario: Usuario = Depends(solo_gerente),
    db: Session = Depends(get_db),
):
    por_pagina = auditoria.config()["auditoria"]["por_pagina"]
    pagina = max(pagina, 1)
    usuario_id = int(usuario_id) if usuario_id.isdigit() else None
    filtro = select(Auditoria)
    if accion:
        filtro = filtro.where(Auditoria.accion == accion)
    if usuario_id:
        filtro = filtro.where(Auditoria.usuario_id == usuario_id)
    total = db.scalar(select(func.count()).select_from(filtro.subquery())) or 0
    registros = db.scalars(
        filtro.order_by(Auditoria.creado_en.desc(), Auditoria.id.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina)
    ).all()
    return templates.TemplateResponse(
        request, "auditoria.html",
        {
            "usuario": usuario, "registros": registros, "acciones": auditoria.ACCIONES, "accion": accion,
            "usuario_id": usuario_id, "usuarios": db.scalars(select(Usuario).order_by(Usuario.nombre)).all(),
            "pagina": pagina, "paginas": max(1, -(-total // por_pagina)), "total": total,
        },
    )
