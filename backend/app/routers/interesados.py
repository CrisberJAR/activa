"""Clientes captados por el chatbot (panel interno para asesores y gerentes)."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import cargar_yaml
from app.db import get_db
from app.models import Conversacion, Interesado, Usuario
from app.security import requiere_rol
from app.services.auditoria import registrar
from app.templating import avisar, templates

router = APIRouter(prefix="/interesados")


def enlace_whatsapp(i: Interesado, empresa: str) -> str:
    campana = f" por la campaña «{i.campana.nombre}»" if i.campana else ""
    texto = f"Hola {i.nombre.split()[0]}, le saluda un asesor de {empresa}. Le escribo{campana} que consultó en nuestra web."
    return f"https://wa.me/51{i.telefono}?text={quote(texto)}"


@router.get("")
def listar(
    request: Request,
    estado: str = "pendientes",
    usuario: Usuario = Depends(requiere_rol("asesor", "gerente")),
    db: Session = Depends(get_db),
):
    consulta = select(Interesado).order_by(Interesado.creado_en.desc(), Interesado.id.desc())
    if estado == "pendientes":
        consulta = consulta.where(Interesado.atendido.is_(False))
    elif estado == "atendidos":
        consulta = consulta.where(Interesado.atendido.is_(True))
    interesados = db.scalars(consulta).all()
    conversaciones = {
        c.id: c for c in db.scalars(
            select(Conversacion).where(Conversacion.id.in_([i.conversacion_id for i in interesados if i.conversacion_id]))
        )
    }
    empresa = cargar_yaml("institucion")["nombre"]
    oficios = cargar_yaml("chatbot")["oficios"]
    return templates.TemplateResponse(
        request, "interesados.html",
        {"usuario": usuario, "interesados": interesados, "estado": estado, "conversaciones": conversaciones,
         "whatsapp": {i.id: enlace_whatsapp(i, empresa) for i in interesados}, "oficios": oficios},
    )


@router.post("/{interesado_id}/atendido")
def cambiar_atendido(
    interesado_id: int,
    request: Request,
    estado: str = "pendientes",
    usuario: Usuario = Depends(requiere_rol("asesor", "gerente")),
    db: Session = Depends(get_db),
):
    interesado = db.get(Interesado, interesado_id)
    if not interesado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interesado no encontrado")
    interesado.atendido = not interesado.atendido
    registrar(db, "interesado_atendido" if interesado.atendido else "interesado_reabierto", usuario, f"interesado {interesado.id}")
    db.commit()
    avisar(request, f"{interesado.nombre}: {'marcado como atendido' if interesado.atendido else 'vuelve a pendientes'}")
    volver = estado if estado in ("pendientes", "atendidos", "todos") else "pendientes"
    return RedirectResponse(f"/interesados?estado={volver}", status.HTTP_303_SEE_OTHER)
