from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Bloque, Encuesta, Usuario
from app.schemas import BloqueEntrada, errores_es
from app.security import requiere_rol, usuario_web
from app.services.auditoria import registrar
from app.templating import avisar, templates

router = APIRouter(prefix="/bloques")

# Todos ven los bloques; solo el gerente los crea, abre y cierra
solo_gerente = requiere_rol("gerente")


def _pagina(request: Request, usuario: Usuario, db: Session, v=None, errores=None, status_code=200):
    filas = db.execute(
        select(Bloque, func.count(Encuesta.id))
        .outerjoin(Encuesta)
        .group_by(Bloque.id)
        .order_by(Bloque.fecha_inicio.desc(), Bloque.id.desc())
    ).all()
    return templates.TemplateResponse(
        request,
        "bloques.html",
        {"usuario": usuario, "filas": filas, "v": v or {}, "errores": errores or {}},
        status_code=status_code,
    )


@router.get("")
def listar(request: Request, usuario: Usuario = Depends(usuario_web), db: Session = Depends(get_db)):
    return _pagina(request, usuario, db)


@router.post("")
async def crear(request: Request, usuario: Usuario = Depends(solo_gerente), db: Session = Depends(get_db)):
    datos = dict(await request.form())
    try:
        entrada = BloqueEntrada(**datos)
    except ValidationError as e:
        return _pagina(request, usuario, db, datos, errores_es(e), status.HTTP_422_UNPROCESSABLE_ENTITY)
    bloque = Bloque(**entrada.model_dump(), creado_por=usuario.id, activo=True)
    db.add(bloque)
    db.flush()
    registrar(db, "bloque_creado", usuario, f"bloque {bloque.id}")
    db.commit()
    avisar(request, f"Bloque «{bloque.nombre}» creado y abierto para encuestas")
    return RedirectResponse("/bloques", status.HTTP_303_SEE_OTHER)


@router.post("/{bloque_id}/estado")
def abrir_o_cerrar(
    bloque_id: int, request: Request, usuario: Usuario = Depends(solo_gerente), db: Session = Depends(get_db)
):
    bloque = db.get(Bloque, bloque_id)
    if not bloque:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bloque no encontrado")
    bloque.activo = not bloque.activo
    registrar(db, "bloque_abierto" if bloque.activo else "bloque_cerrado", usuario, f"bloque {bloque.id}")
    db.commit()
    avisar(request, f"Bloque «{bloque.nombre}» {'abierto' if bloque.activo else 'cerrado'}")
    return RedirectResponse("/bloques", status.HTTP_303_SEE_OTHER)
