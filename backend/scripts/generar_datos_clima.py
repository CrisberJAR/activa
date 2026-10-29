"""Genera 8 semanas de registros diarios SIMULADOS para probar el análisis estacional sin esperar.

Los datos van directo a la tabla registros_diarios (no pasan por Firebase) con un sensor "sim-...".
Cada vez que se ejecuta, reemplaza los datos simulados anteriores.

Uso (desde backend/, con el entorno activado):
    python -m scripts.generar_datos_clima --escenario lluvias     # llegada de las lluvias
    python -m scripts.generar_datos_clima --escenario invierno    # llegada del invierno
    python -m scripts.generar_datos_clima --escenario verano      # llegada del verano
    python -m scripts.generar_datos_clima --borrar                # elimina los datos simulados
"""
import argparse
import random
from datetime import date, timedelta

from sqlalchemy import delete, select

from app.config import hoy_peru
from app.db import SessionLocal
from app.models import RegistroDiario, Sensor
from app.services.clima import diagnostico_actual, guardar_diagnostico
from app.services.consolidacion import obtener_o_crear_sensor

SENSOR_SIMULADO = "sim-huanuco-01"

# Promedio semanal (temperatura °C, humedad %) de la semana 1 a la 8; la 8 es la actual
ESCENARIOS = {
    "lluvias": [(20.0, 60), (20.0, 61), (20.5, 60), (20.0, 62), (20.0, 61), (19.5, 63), (19.0, 70), (18.5, 81)],
    "invierno": [(18.0, 56), (18.0, 55), (17.5, 56), (17.5, 55), (17.0, 54), (16.0, 55), (14.0, 54), (10.5, 53)],
    "verano": [(19.0, 58), (19.0, 57), (19.5, 57), (19.5, 56), (20.0, 55), (21.0, 54), (22.0, 52), (25.5, 50)],
}


def generar_registros(escenario: str, hoy: date, semanas: int = 8, semilla: int = 7) -> list[dict]:
    """Un registro por día, terminando hoy, con pequeñas variaciones aleatorias (reproducibles)."""
    azar = random.Random(semilla)
    semanales = ESCENARIOS[escenario][-semanas:]
    total = 7 * semanas
    registros = []
    for i in range(total):
        temp_semana, hum_semana = semanales[i // 7]
        temp = round(temp_semana + azar.uniform(-0.6, 0.6), 2)
        hum = round(min(100, max(0, hum_semana + azar.uniform(-1.5, 1.5))), 2)
        registros.append({
            "fecha": hoy - timedelta(days=total - 1 - i),
            "temp_promedio": temp,
            "temp_min": round(temp - azar.uniform(3, 5), 1),
            "temp_max": round(temp + azar.uniform(3, 5), 1),
            "humedad_promedio": hum,
            "humedad_min": round(max(0, hum - azar.uniform(6, 10)), 1),
            "humedad_max": round(min(100, hum + azar.uniform(6, 10)), 1),
            "n_lecturas": 48,
        })
    return registros


def borrar_simulados(db) -> None:
    sensor = db.scalar(select(Sensor).where(Sensor.codigo == SENSOR_SIMULADO))
    if sensor:
        db.execute(delete(RegistroDiario).where(RegistroDiario.sensor_id == sensor.id))


def main():
    parser = argparse.ArgumentParser(description="Genera datos de clima simulados")
    parser.add_argument("--escenario", choices=ESCENARIOS, default="lluvias")
    parser.add_argument("--borrar", action="store_true", help="solo borra los datos simulados")
    args = parser.parse_args()

    with SessionLocal() as db:
        borrar_simulados(db)
        if args.borrar:
            db.commit()
            print("Datos simulados eliminados.")
            return
        sensor = obtener_o_crear_sensor(db, SENSOR_SIMULADO, "agricola", "Simulado – Huánuco (datos de prueba)")
        registros = generar_registros(args.escenario, hoy_peru())
        db.add_all(RegistroDiario(sensor_id=sensor.id, **r) for r in registros)
        db.commit()
        print(f"Escenario «{args.escenario}»: {len(registros)} días simulados en {SENSOR_SIMULADO}")

        diag = diagnostico_actual(db, SENSOR_SIMULADO)
        guardar_diagnostico(db, diag)
        print(f"Estación actual: {diag['estacion_nombre']}  ({diag['promedio']['temperatura']} °C, {diag['promedio']['humedad']} %)")
        print(f"Temporada próxima: {diag['temporada_nombre']}")
        print(f"Mensaje: {diag['mensaje']}")


if __name__ == "__main__":
    main()
