from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalogos import TEMPORADAS
from app.config import HORA_PERU, cargar_umbrales, hoy_peru
from app.db import get_db
from app.models import Sensor, Usuario
from app.services import firebase
from app.services.clima import cargar_registros, diagnostico_actual, guardar_diagnostico
from app.services.consolidacion import consolidar
from app.services.estacion import Dia, comparar_periodos
from app.security import requiere_rol, usuario_web, usuario_web_o_api
from app.templating import avisar, templates

router = APIRouter()


def _ultimas_lecturas() -> tuple[list[dict], str | None]:
    """Última lectura de cada sensor en Firebase (en vivo). Si Firebase falla, devuelve el error."""
    try:
        ultimas = firebase.leer_ultimas()
    except firebase.ErrorFirebase as e:
        return [], str(e)
    return [
        {
            "sensor": codigo,
            "sector": lec.get("sector"),
            "temperatura": lec.get("temperatura"),
            "humedad": lec.get("humedad"),
            "hora": datetime.fromtimestamp(lec["ts"] / 1000, tz=HORA_PERU).isoformat() if lec.get("ts") else None,
        }
        for codigo, lec in ultimas.items()
    ], None


# ---------- Web ----------

@router.get("/clima")
def pagina(
    request: Request,
    sensor: str | None = None,
    usuario: Usuario = Depends(usuario_web),
    db: Session = Depends(get_db),
):
    hoy = hoy_peru()
    sensor = sensor or None
    ultimas, error_firebase = _ultimas_lecturas()
    return templates.TemplateResponse(
        request,
        "clima.html",
        {
            "usuario": usuario,
            "diag": diagnostico_actual(db, sensor),
            "registros": cargar_registros(db, hoy - timedelta(days=56), hoy, sensor),
            "sensores": db.scalars(select(Sensor).order_by(Sensor.codigo)).all(),
            "sensor": sensor,
            "ultimas": ultimas,
            "error_firebase": error_firebase,
            "nombres": TEMPORADAS,
            "umbrales": cargar_umbrales(),
        },
    )


@router.post("/clima/consolidar")
def consolidar_ahora(
    request: Request, usuario: Usuario = Depends(requiere_rol("gerente")), db: Session = Depends(get_db)
):
    try:
        resultado = consolidar(db)
    except firebase.ErrorFirebase as e:
        avisar(request, f"No se pudo leer Firebase: {e}")
        return RedirectResponse("/clima", status.HTTP_303_SEE_OTHER)
    guardar_diagnostico(db, diagnostico_actual(db))
    avisar(request, f"Datos actualizados: {resultado['sensores']} sensor(es), {resultado['registros']} día(s) consolidados")
    return RedirectResponse("/clima", status.HTTP_303_SEE_OTHER)


# ---------- API (web y app móvil) ----------

@router.get("/api/clima/registros")
def api_registros(
    dias: int = Query(28, ge=1, le=366),
    sensor: str | None = None,
    usuario: Usuario = Depends(usuario_web_o_api),
    db: Session = Depends(get_db),
):
    hoy = hoy_peru()
    return cargar_registros(db, hoy - timedelta(days=dias), hoy, sensor)


@router.get("/api/clima/analisis")
def api_analisis(
    periodo: int = Query(7),
    sensor: str | None = None,
    usuario: Usuario = Depends(usuario_web_o_api),
    db: Session = Depends(get_db),
):
    umbrales = cargar_umbrales()
    if periodo not in umbrales["cambios"]["periodos_dias"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"periodo debe ser uno de {umbrales['cambios']['periodos_dias']}")
    hoy = hoy_peru()
    registros = cargar_registros(db, hoy - timedelta(days=2 * periodo), hoy, sensor)
    dias = [Dia(datetime.fromisoformat(r["fecha"]).date(), r["temperatura"], r["humedad"]) for r in registros]
    return comparar_periodos(dias, periodo, hoy, umbrales)


@router.get("/api/clima/diagnostico")
def api_diagnostico(
    sensor: str | None = None, usuario: Usuario = Depends(usuario_web_o_api), db: Session = Depends(get_db)
):
    return diagnostico_actual(db, sensor)


@router.get("/api/clima/sensores")
def api_sensores(usuario: Usuario = Depends(usuario_web_o_api), db: Session = Depends(get_db)):
    return [
        {"codigo": s.codigo, "sector": s.sector, "ubicacion": s.ubicacion}
        for s in db.scalars(select(Sensor).where(Sensor.activo.is_(True)).order_by(Sensor.codigo))
    ]


@router.get("/api/clima/ultima")
def api_ultima(usuario: Usuario = Depends(usuario_web_o_api)):
    ultimas, error = _ultimas_lecturas()
    if error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, error)
    return ultimas
