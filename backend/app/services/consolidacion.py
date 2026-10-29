"""Convierte las lecturas de Firebase en registros diarios (promedio, mínimo y máximo por sensor y día)."""
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import HORA_PERU, hoy_peru
from app.models import RegistroDiario, Sensor
from app.services import firebase


def agrupar_por_dia(lecturas: list[dict]) -> dict[date, dict]:
    """Agrupa lecturas por día en hora de Perú y calcula promedio, mínimo y máximo."""
    por_dia = defaultdict(list)
    for lec in lecturas:
        try:
            dia = datetime.fromtimestamp(lec["ts"] / 1000, tz=HORA_PERU).date()
            por_dia[dia].append((float(lec["temperatura"]), float(lec["humedad"])))
        except (KeyError, TypeError, ValueError):
            continue  # lectura incompleta: se ignora
    resumen = {}
    for dia, valores in por_dia.items():
        temps = [t for t, _ in valores]
        hums = [h for _, h in valores]
        resumen[dia] = {
            "temp_promedio": round(sum(temps) / len(temps), 2),
            "temp_min": min(temps),
            "temp_max": max(temps),
            "humedad_promedio": round(sum(hums) / len(hums), 2),
            "humedad_min": min(hums),
            "humedad_max": max(hums),
            "n_lecturas": len(valores),
        }
    return resumen


def obtener_o_crear_sensor(db: Session, codigo: str, sector: str, ubicacion: str | None = None) -> Sensor:
    sensor = db.scalar(select(Sensor).where(Sensor.codigo == codigo))
    if not sensor:
        sensor = Sensor(codigo=codigo, sector=sector, ubicacion=ubicacion)
        db.add(sensor)
        db.flush()
    return sensor


def guardar_registros(db: Session, sensor: Sensor, resumen: dict[date, dict]) -> int:
    """Crea o actualiza el registro diario de cada día (volver a correrlo no duplica)."""
    for dia, valores in resumen.items():
        registro = db.scalar(
            select(RegistroDiario).where(RegistroDiario.sensor_id == sensor.id, RegistroDiario.fecha == dia)
        )
        if registro:
            for campo, valor in valores.items():
                setattr(registro, campo, valor)
        else:
            db.add(RegistroDiario(sensor_id=sensor.id, fecha=dia, **valores))
    return len(resumen)


def consolidar(db: Session, dias: int = 2) -> dict:
    """Lee de Firebase los últimos `dias` días (incluido hoy) de cada sensor y guarda sus registros diarios."""
    desde = datetime.combine(hoy_peru() - timedelta(days=dias - 1), datetime.min.time(), tzinfo=HORA_PERU)
    desde_ms = int(desde.timestamp() * 1000)
    sensores = registros = 0
    for codigo, ultima in firebase.leer_ultimas().items():
        sensor = obtener_o_crear_sensor(db, codigo, ultima.get("sector", "agricola"))
        registros += guardar_registros(db, sensor, agrupar_por_dia(firebase.leer_lecturas(codigo, desde_ms)))
        sensores += 1
    db.commit()
    return {"sensores": sensores, "registros": registros}
