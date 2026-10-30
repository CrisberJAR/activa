"""Cronometra cuánto tarda el sistema en cada paso (columna "después" de docs/tiempos.md).

Usa las encuestas reales de un bloque y Gemini real, pero NO guarda nada en la base.

Uso (desde backend/, con el entorno activado):
    python -m scripts.medir_tiempos                 # primer bloque con encuestas
    python -m scripts.medir_tiempos --bloque 2 --repeticiones 3
"""
import argparse
import statistics
import time

from sqlalchemy import select

from app.config import cargar_necesidades
from app.db import SessionLocal
from app.models import Bloque, Encuesta
from app.schemas import CampanaEntrada
from app.services import campanas, ia, ml
from app.services.analisis import (calcular_indicadores, encuestas_del_bloque, ranking_necesidades,
                                   sugerencia_modelo)
from app.services.clima import diagnostico_actual


def cronometrar(funcion):
    inicio = time.perf_counter()
    resultado = funcion()
    return resultado, time.perf_counter() - inicio


def segundos(valores: list[float]) -> str:
    mediana = statistics.median(valores)
    return f"{mediana * 1000:.0f} ms" if mediana < 1 else f"{mediana:.1f} s"


def main():
    parser = argparse.ArgumentParser(description="Mide los tiempos del sistema")
    parser.add_argument("--bloque", type=int, help="id del bloque (por defecto, el primero con encuestas)")
    parser.add_argument("--repeticiones", type=int, default=3)
    args = parser.parse_args()

    with SessionLocal() as db:
        bloque_id = args.bloque or db.scalar(select(Encuesta.bloque_id).order_by(Encuesta.bloque_id))
        bloque = db.get(Bloque, bloque_id)
        diag = diagnostico_actual(db)
        estacion = diag if diag.get("estacion_actual") else None
        (encuestas, nombres), t_lectura = cronometrar(lambda: encuestas_del_bloque(db, bloque_id))

        _, t_carga = cronometrar(ml.cargar_modelo)
        config = cargar_necesidades()
        tiempos = {"indicadores": [], "modelo": [], "texto": [], "campana": []}
        fuentes = set()
        for i in range(args.repeticiones):
            print(f"Repetición {i + 1} de {args.repeticiones}...")
            (indicadores, ranking), t = cronometrar(
                lambda: (calcular_indicadores(encuestas), ranking_necesidades(encuestas, config)))
            tiempos["indicadores"].append(t)
            sugerencia, t = cronometrar(lambda: sugerencia_modelo(encuestas, config))
            tiempos["modelo"].append(t)
            textos = [ia.anonimizar(e["necesidad"], nombres) for e in encuestas]
            patron, t = cronometrar(lambda: ia.texto_patron(indicadores, ranking, textos, estacion, sugerencia))
            tiempos["texto"].append(t)
            fuentes.add(patron["modelo"] or "plantilla")

            entrada = CampanaEntrada(**campanas.valores_sugeridos(db, bloque_id, estacion) | {
                "tipo_campana": sugerencia["sugerida"], "temporada": indicadores["temporada_frecuente"],
                "publico_objetivo": f"Clientes del bloque {bloque.nombre}", "necesidad": ranking[0]["nombre"],
                "zona": ", ".join(list(indicadores["por_zona"])[:3]),
            })
            contexto = campanas.contexto_bloque(db, bloque_id, estacion)
            (_, generado_con, _), t = cronometrar(lambda: campanas.generar_contenido(entrada, contexto))
            tiempos["campana"].append(t)
            fuentes.add(generado_con)

    total = t_lectura + sum(statistics.median(v) for v in tiempos.values())
    print(f"\nBloque «{bloque.nombre}» ({len(encuestas)} encuestas). Mediana de {args.repeticiones} repeticiones.")
    print(f"Generado con: {', '.join(sorted(fuentes))}\n")
    print("| Paso | Tiempo del sistema |")
    print("|---|---|")
    print(f"| Leer las encuestas del bloque | {segundos([t_lectura])} |")
    print(f"| Indicadores y ranking de necesidades | {segundos(tiempos['indicadores'])} |")
    print(f"| Sugerencia del Random Forest | {segundos(tiempos['modelo'])} (carga inicial del modelo: {segundos([t_carga])}) |")
    print(f"| Texto del patrón con Gemini | {segundos(tiempos['texto'])} |")
    print(f"| Campaña completa con Gemini | {segundos(tiempos['campana'])} |")
    print(f"| **Total: de las encuestas a la campaña en borrador** | **{segundos([total])}** |")


if __name__ == "__main__":
    main()
