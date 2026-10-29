"""Tarea automática: cada hora consolida las lecturas de Firebase y guarda el diagnóstico del día."""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.db import SessionLocal
from app.services.clima import diagnostico_actual, guardar_diagnostico
from app.services.consolidacion import consolidar

log = logging.getLogger("activa.scheduler")


def tarea_horaria() -> None:
    try:
        with SessionLocal() as db:
            resultado = consolidar(db)
            guardar_diagnostico(db, diagnostico_actual(db))
        log.info("Consolidación OK: %s", resultado)
    except Exception:
        # Si Firebase o Supabase fallan, se intenta de nuevo en la siguiente hora
        log.exception("Falló la consolidación automática")


def iniciar() -> BackgroundScheduler:
    planificador = BackgroundScheduler(timezone="UTC")
    planificador.add_job(tarea_horaria, "interval", hours=1, next_run_time=datetime.now(timezone.utc), id="consolidar")
    planificador.start()
    return planificador
