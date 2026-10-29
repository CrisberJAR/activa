"""Une la base de datos con la lógica estacional: carga días, genera y guarda diagnósticos."""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import cargar_umbrales, hoy_peru
from app.models import Diagnostico, RegistroDiario, Sensor
from app.services.estacion import Dia, diagnosticar


def cargar_registros(db: Session, desde: date, hasta: date, sensor: str | None = None) -> list[dict]:
    """Registros diarios entre dos fechas; si hay varios sensores, se promedian por día."""
    consulta = (
        select(
            RegistroDiario.fecha,
            func.avg(RegistroDiario.temp_promedio),
            func.avg(RegistroDiario.humedad_promedio),
            func.min(RegistroDiario.temp_min),
            func.max(RegistroDiario.temp_max),
            func.min(RegistroDiario.humedad_min),
            func.max(RegistroDiario.humedad_max),
            func.sum(RegistroDiario.n_lecturas),
        )
        .where(RegistroDiario.fecha > desde, RegistroDiario.fecha <= hasta)
        .group_by(RegistroDiario.fecha)
        .order_by(RegistroDiario.fecha)
    )
    if sensor:
        consulta = consulta.join(Sensor).where(Sensor.codigo == sensor)
    return [
        {
            "fecha": f.isoformat(),
            "temperatura": round(float(t), 1),
            "humedad": round(float(h), 1),
            "temp_min": float(tmin),
            "temp_max": float(tmax),
            "humedad_min": float(hmin),
            "humedad_max": float(hmax),
            "n_lecturas": int(n),
        }
        for f, t, h, tmin, tmax, hmin, hmax, n in db.execute(consulta).all()
    ]


def diagnostico_actual(db: Session, sensor: str | None = None, hoy: date | None = None) -> dict:
    hoy = hoy or hoy_peru()
    umbrales = cargar_umbrales()
    # Se necesitan 2 periodos completos del más largo para comparar
    dias_atras = 2 * max(umbrales["cambios"]["periodos_dias"] + [umbrales["estacion"]["periodo_dias"]])
    registros = cargar_registros(db, hoy - timedelta(days=dias_atras), hoy, sensor)
    dias = [Dia(date.fromisoformat(r["fecha"]), r["temperatura"], r["humedad"]) for r in registros]
    return diagnosticar(dias, hoy, umbrales)


def guardar_diagnostico(db: Session, diag: dict) -> None:
    """Guarda (o actualiza) el diagnóstico del día, uno por periodo, como historial."""
    if diag["estacion_actual"] is None:
        return
    fecha = date.fromisoformat(diag["fecha"])
    for comp in diag["comparaciones"]:
        fila = db.scalar(
            select(Diagnostico).where(Diagnostico.fecha == fecha, Diagnostico.periodo_dias == comp["periodo"])
        )
        if not fila:
            fila = Diagnostico(fecha=fecha, periodo_dias=comp["periodo"])
            db.add(fila)
        fila.estacion_actual = diag["estacion_actual"]
        fila.temporada_proxima = comp["temporada_proxima"]
        fila.cambio_humedad = comp.get("cambio_humedad")
        fila.cambio_temperatura = comp.get("cambio_temperatura")
        fila.alerta = comp["alerta"]
        fila.mensaje = comp["mensaje"]
    db.commit()
