from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Bloque, Encuesta, Usuario
from app.schemas import CAMPOS_ENCUESTA, EncuestaEntrada, errores_es
from app.security import usuario_web
from app.services.auditoria import registrar
from app.templating import avisar, templates

router = APIRouter(prefix="/encuestas")


def puede_editar(usuario: Usuario, encuesta: Encuesta) -> bool:
    """Edita quien registró la encuesta, o el gerente."""
    return usuario.rol == "gerente" or encuesta.asesor_id == usuario.id


def _bloques_para_formulario(db: Session, bloque_actual_id: int | None = None) -> list[Bloque]:
    # Bloques abiertos; al editar también se muestra el bloque actual aunque esté cerrado
    condicion = Bloque.activo.is_(True)
    if bloque_actual_id:
        condicion = or_(condicion, Bloque.id == bloque_actual_id)
    return db.scalars(select(Bloque).where(condicion).order_by(Bloque.fecha_inicio.desc())).all()


def _leer_formulario(form) -> dict:
    datos = dict(form)
    datos["consentimiento"] = "consentimiento" in form  # casilla sin marcar no se envía
    return datos


def _valores_de(encuesta: Encuesta) -> dict:
    valores = {}
    for campo in CAMPOS_ENCUESTA:
        valor = getattr(encuesta, campo)
        if campo != "consentimiento" and isinstance(valor, bool):
            valor = "true" if valor else "false"
        valores[campo] = valor if campo == "consentimiento" else str(valor)
    return valores


def _validar(db: Session, datos: dict, bloque_actual_id: int | None = None):
    try:
        entrada = EncuestaEntrada(**datos)
    except ValidationError as e:
        return None, errores_es(e)
    bloque = db.get(Bloque, entrada.bloque_id)
    if not bloque or (not bloque.activo and bloque.id != bloque_actual_id):
        return None, {"bloque_id": "Elige un bloque abierto"}
    return entrada, {}


def _formulario(request, usuario, db, v, errores, encuesta=None, status_code=200):
    return templates.TemplateResponse(
        request,
        "encuesta_form.html",
        {
            "usuario": usuario,
            "v": v,
            "errores": errores,
            "encuesta": encuesta,
            "bloques": _bloques_para_formulario(db, encuesta.bloque_id if encuesta else None),
        },
        status_code=status_code,
    )


def _obtener(db: Session, encuesta_id: int) -> Encuesta:
    encuesta = db.get(Encuesta, encuesta_id)
    if not encuesta:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Encuesta no encontrada")
    return encuesta


def _verificar_permiso(usuario: Usuario, encuesta: Encuesta) -> None:
    if not puede_editar(usuario, encuesta):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo quien registró la encuesta o el gerente pueden editarla")


@router.get("")
def listar(
    request: Request,
    bloque_id: int | None = None,
    usuario: Usuario = Depends(usuario_web),
    db: Session = Depends(get_db),
):
    if bloque_id is None:
        bloque_id = request.session.get("bloque_id")
    bloque = db.get(Bloque, bloque_id) if bloque_id else None
    encuestas = []
    if bloque:
        request.session["bloque_id"] = bloque.id
        encuestas = db.scalars(
            select(Encuesta).where(Encuesta.bloque_id == bloque.id).order_by(Encuesta.id.desc())
        ).all()
    bloques = db.scalars(select(Bloque).order_by(Bloque.fecha_inicio.desc(), Bloque.id.desc())).all()
    return templates.TemplateResponse(
        request,
        "encuestas.html",
        {
            "usuario": usuario,
            "bloques": bloques,
            "bloque": bloque,
            "encuestas": encuestas,
            "puede_editar": puede_editar,
        },
    )


@router.get("/nueva")
def nueva(request: Request, usuario: Usuario = Depends(usuario_web), db: Session = Depends(get_db)):
    return _formulario(request, usuario, db, {"bloque_id": str(request.session.get("bloque_id", ""))}, {})


@router.post("/nueva")
async def crear(request: Request, usuario: Usuario = Depends(usuario_web), db: Session = Depends(get_db)):
    datos = _leer_formulario(await request.form())
    entrada, errores = _validar(db, datos)
    if errores:
        return _formulario(request, usuario, db, datos, errores, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    encuesta = Encuesta(**entrada.model_dump(), asesor_id=usuario.id)
    db.add(encuesta)
    db.flush()
    registrar(db, "encuesta_creada", usuario, f"encuesta {encuesta.id} · bloque {encuesta.bloque_id}")
    db.commit()
    request.session["bloque_id"] = encuesta.bloque_id
    avisar(request, f"Encuesta de {encuesta.nombre} guardada")
    return RedirectResponse(f"/encuestas?bloque_id={encuesta.bloque_id}", status.HTTP_303_SEE_OTHER)


@router.get("/{encuesta_id}")
def detalle(
    encuesta_id: int, request: Request, usuario: Usuario = Depends(usuario_web), db: Session = Depends(get_db)
):
    encuesta = _obtener(db, encuesta_id)
    return templates.TemplateResponse(
        request,
        "encuesta_detalle.html",
        {"usuario": usuario, "e": encuesta, "editable": puede_editar(usuario, encuesta)},
    )


@router.get("/{encuesta_id}/editar")
def editar_form(
    encuesta_id: int, request: Request, usuario: Usuario = Depends(usuario_web), db: Session = Depends(get_db)
):
    encuesta = _obtener(db, encuesta_id)
    _verificar_permiso(usuario, encuesta)
    return _formulario(request, usuario, db, _valores_de(encuesta), {}, encuesta)


@router.post("/{encuesta_id}/editar")
async def editar(
    encuesta_id: int, request: Request, usuario: Usuario = Depends(usuario_web), db: Session = Depends(get_db)
):
    encuesta = _obtener(db, encuesta_id)
    _verificar_permiso(usuario, encuesta)
    datos = _leer_formulario(await request.form())
    entrada, errores = _validar(db, datos, bloque_actual_id=encuesta.bloque_id)
    if errores:
        return _formulario(
            request, usuario, db, datos, errores, encuesta, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    for campo, valor in entrada.model_dump().items():
        setattr(encuesta, campo, valor)
    registrar(db, "encuesta_editada", usuario, f"encuesta {encuesta.id}")
    db.commit()
    avisar(request, f"Encuesta de {encuesta.nombre} actualizada")
    return RedirectResponse(f"/encuestas/{encuesta.id}", status.HTTP_303_SEE_OTHER)
