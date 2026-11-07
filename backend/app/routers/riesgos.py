"""Riesgos: bandeja de evaluaciones preliminares, umbrales versionados y alertas de seguridad."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Solicitud, Usuario
from app.security import requiere_rol
from app.services import negocios, riesgos
from app.services.auditoria import ACCIONES
from app.templating import templates

router = APIRouter(prefix="/riesgos")
roles_riesgos = requiere_rol("analista_riesgos", "gerente")


@router.get("")
def bandeja(request: Request, semaforo: str = "", usuario: Usuario = Depends(roles_riesgos), db: Session = Depends(get_db)):
    filas = []
    for s in db.scalars(select(Solicitud).where(Solicitud.estado.in_(riesgos.ESTADOS_ACTIVOS)).order_by(Solicitud.id)).all():
        ev = riesgos.ultima_evaluacion(s)
        filas.append({"s": s, "ev": ev, "semaforo": ev.semaforo if ev else "sin_evaluar"})
    conteo = {k: sum(1 for f in filas if f["semaforo"] == k) for k in ("rojo", "amarillo", "verde", "sin_evaluar")}
    if semaforo:
        filas = [f for f in filas if f["semaforo"] == semaforo]
    # Primero lo más urgente: rojo, sin evaluar, amarillo, verde
    orden = {"rojo": 0, "sin_evaluar": 1, "amarillo": 2, "verde": 3}
    filas.sort(key=lambda f: (orden[f["semaforo"]], f["s"].id))
    cfg = riesgos.config()
    return templates.TemplateResponse(
        request, "riesgos.html",
        {"usuario": usuario, "filas": filas, "conteo": conteo, "semaforo": semaforo, "cfg": cfg,
         "estados": negocios.ESTADOS_TEXTO, "colores": negocios.ESTADOS_COLOR, "productos": negocios.productos()},
    )


@router.get("/seguridad")
def seguridad(request: Request, dias: int = 7, usuario: Usuario = Depends(roles_riesgos), db: Session = Depends(get_db)):
    dias = min(max(dias, 1), 90)
    return templates.TemplateResponse(
        request, "riesgos_seguridad.html",
        {"usuario": usuario, "datos": riesgos.alertas_seguridad(db, dias), "acciones": ACCIONES},
    )
