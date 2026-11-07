"""Panel principal de ACTIVA 360°: indicadores calculados con los registros guardados, según el rol."""
from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import hoy_peru
from app.db import get_db
from app.models import Bloque, Campana, Encuesta, Interesado, Solicitud, Usuario
from app.security import requiere_rol, usuario_web
from app.services import comercial, negocios, riesgos
from app.services import recuperaciones as rec
from app.services.campanas import estado_visible, vigentes
from app.templating import templates

router = APIRouter()


def _comercial(db: Session, usuario: Usuario) -> dict:
    emb = comercial.embudo(db, usuario)
    hoy = hoy_peru()
    sub = comercial.visibles(usuario).subquery()
    # Prospectos registrados por semana (últimas 8 semanas)
    inicio = hoy - timedelta(weeks=7, days=hoy.weekday())
    semanas = [inicio + timedelta(weeks=i) for i in range(8)]
    fechas = [f.date() if hasattr(f, "date") else f for f in db.scalars(select(sub.c.creado_en)).all() if f]
    por_semana = [sum(1 for f in fechas if s <= f < s + timedelta(weeks=1)) for s in semanas]
    campanas = db.scalars(select(Campana)).all()
    return {
        "embudo": emb,
        "nuevos": emb["conteo"].get("nuevo", 0),
        "contactados": emb["conteo"].get("contactado", 0) + emb["conteo"].get("interesado", 0),
        "solicitudes_iniciadas": emb["conteo"].get("solicitud", 0) + emb["conteo"].get("evaluacion", 0),
        "vigentes": len(vigentes(db)),
        "pendientes_aprobacion": sum(1 for c in campanas if c.estado == "pendiente"),
        "borradores": sum(1 for c in campanas if estado_visible(c) == "borrador"),
        "mejores_campanas": comercial.desempeno_campanas(db),
        "actividades": comercial.pendientes(db, usuario),
        "interesados_pendientes": db.scalar(select(func.count(Interesado.id)).where(Interesado.atendido.is_(False))) or 0,
        "encuestas": db.scalar(select(func.count(Encuesta.id))) or 0,
        "bloques_abiertos": db.scalar(select(func.count(Bloque.id)).where(Bloque.activo.is_(True))) or 0,
        "grafico_semanas": {"etiquetas": [s.strftime("%d/%m") for s in semanas], "valores": por_semana},
    }


def _negocios(db: Session, usuario: Usuario) -> dict:
    consulta = select(Solicitud.estado, func.count()).group_by(Solicitud.estado)
    if usuario.rol == "asesor":
        consulta = consulta.where(Solicitud.asesor_id == usuario.id)
    elif usuario.rol == "analista_riesgos":
        consulta = consulta.where(Solicitud.estado != "borrador")
    conteo = dict(db.execute(consulta).all())
    return {"conteo": conteo, "estados": negocios.ESTADOS_TEXTO, "colores": negocios.ESTADOS_COLOR,
            "total": sum(conteo.values()), "en_curso": sum(conteo.get(e, 0) for e in riesgos.ESTADOS_ACTIVOS)}


def _riesgos(db: Session) -> dict:
    conteo = {"rojo": 0, "amarillo": 0, "verde": 0, "sin_evaluar": 0}
    for s in db.scalars(select(Solicitud).where(Solicitud.estado.in_(riesgos.ESTADOS_ACTIVOS))).all():
        ev = riesgos.ultima_evaluacion(s)
        conteo[ev.semaforo if ev else "sin_evaluar"] += 1
    por_tomar = db.scalar(select(func.count(Solicitud.id)).where(Solicitud.estado == "enviada")) or 0
    seguridad = sum(f["cantidad"] for f in riesgos.alertas_seguridad(db, 7)["filas"])
    return {"conteo": conteo, "por_tomar": por_tomar, "seguridad": seguridad}


def _recuperaciones(db: Session, usuario: Usuario) -> dict:
    hoy = hoy_peru()
    resumenes = [rec.resumen(cr, hoy) for cr in rec.creditos_de(db, usuario)]
    saldo = sum((r["saldo"] for r in resumenes), Decimal("0"))
    vencido = sum((r["vencido"] for r in resumenes), Decimal("0"))
    alertas = rec.alertas(db, usuario, hoy)
    return {
        "creditos": len(resumenes), "saldo": saldo, "vencido": vencido,
        "en_mora": sum(1 for r in resumenes if r["dias_atraso"] > 0),
        "pct_mora": round(100 * float(vencido) / float(saldo), 1) if saldo else 0,
        "alertas": len(alertas),
        "vencen_pronto": sum(1 for a in alertas if a["tipo"] == "proximo_vencimiento"),
    }


@router.get("/panel")
def panel(request: Request, usuario: Usuario = Depends(usuario_web), db: Session = Depends(get_db)):
    rol = usuario.rol
    datos = {"usuario": usuario, "rol": rol, "hoy": hoy_peru()}
    if rol in ("asesor", "gerente"):
        datos["com"] = _comercial(db, usuario)
    if rol in ("asesor", "gerente", "analista_riesgos"):
        datos["neg"] = _negocios(db, usuario)
    if rol in ("analista_riesgos", "gerente"):
        datos["rie"] = _riesgos(db)
    if rol in ("gestor_recuperaciones", "gerente"):
        rec.actualizar_compromisos(db)
        datos["rec"] = _recuperaciones(db, usuario)
    return templates.TemplateResponse(request, "panel.html", datos)


# Rutas anteriores (Fase 0): se mantienen para no romper enlaces guardados
@router.get("/asesor")
def menu_asesor(usuario: Usuario = Depends(requiere_rol("asesor", "gerente"))):
    return RedirectResponse("/panel", status.HTTP_303_SEE_OTHER)


@router.get("/gerente")
def menu_gerente(usuario: Usuario = Depends(requiere_rol("gerente"))):
    return RedirectResponse("/panel", status.HTTP_303_SEE_OTHER)
