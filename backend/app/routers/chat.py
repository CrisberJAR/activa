"""API pública del asesor virtual (la usa el widget de la página de inicio)."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Conversacion
from app.services import chatbot

router = APIRouter(prefix="/api/chat")


class Inicio(BaseModel):
    campana_id: int | None = None


class Mensaje(BaseModel):
    conversacion_id: str = Field(min_length=32, max_length=32)
    texto: str = Field(min_length=1, max_length=1000)


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconocida"


def _conversacion(db: Session, conversacion_id: str) -> Conversacion:
    conv = db.get(Conversacion, conversacion_id)
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversación no encontrada")
    return conv


@router.post("/iniciar")
def iniciar(datos: Inicio, request: Request, db: Session = Depends(get_db)):
    try:
        return chatbot.iniciar(db, _ip(request), datos.campana_id)
    except chatbot.LimiteExcedido as e:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(e))


@router.post("/mensaje")
def mensaje(datos: Mensaje, db: Session = Depends(get_db)):
    conv = _conversacion(db, datos.conversacion_id)
    resultado = chatbot.procesar(db, conv, datos.texto)
    db.commit()
    return resultado


@router.get("/{conversacion_id}")
def ver(conversacion_id: str, db: Session = Depends(get_db)):
    return chatbot.historial(_conversacion(db, conversacion_id))
