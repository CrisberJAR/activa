"""Random Forest que sugiere el tipo de campaña (Fase 5b).

El modelo se entrena aparte (python -m ml.entrenar) y aquí solo se carga una vez y se usa.
Si el archivo del modelo no existe, el análisis sigue funcionando sin sugerencia.
"""
import json
from collections import Counter
from functools import lru_cache

from app.config import BASE_DIR, cargar_tipos_campana

RUTA_MODELO = BASE_DIR / "ml" / "modelo.joblib"
RUTA_METRICAS = BASE_DIR / "ml" / "metricas.json"

# Variables del modelo (nunca nombre ni teléfono)
CATEGORICAS = ["sector", "categoria_necesidad", "temporada_necesidad", "riesgo_principal", "frecuencia_ingresos", "garantia"]
NUMERICAS = ["mes", "ingreso_mensual", "monto", "plazo_meses", "anios_negocio", "trabajadores", "credito_vigente"]
VARIABLES = CATEGORICAS + NUMERICAS


def caracteristicas(encuesta: dict, categoria: str, mes: int) -> dict:
    """Convierte una encuesta en la fila que recibe el modelo."""
    fila = {c: encuesta[c] for c in CATEGORICAS if c != "categoria_necesidad"}
    fila["categoria_necesidad"] = categoria
    fila["mes"] = mes
    for c in ("ingreso_mensual", "monto", "plazo_meses", "anios_negocio", "trabajadores"):
        fila[c] = float(encuesta[c])
    fila["credito_vigente"] = int(bool(encuesta["credito_vigente"]))
    return fila


@lru_cache(maxsize=1)
def cargar_modelo():
    """Carga el modelo una sola vez (queda en memoria). None si no está entrenado."""
    if not RUTA_MODELO.exists():
        return None
    import joblib  # se importa aquí para que el servidor arranque rápido

    return joblib.load(RUTA_MODELO)


def sugerir(filas: list[dict]) -> dict | None:
    """Predice un tipo por cliente y sugiere el más frecuente para el bloque."""
    modelo = cargar_modelo()
    if modelo is None or not filas:
        return None
    import pandas as pd

    datos = pd.DataFrame(filas, columns=VARIABLES)
    predicciones = [str(p) for p in modelo.predict(datos)]
    confianza = modelo.predict_proba(datos).max(axis=1)  # probabilidad del tipo elegido
    tipos = cargar_tipos_campana()
    conteo = Counter(predicciones)
    # En empate gana el tipo con mayor confianza promedio
    conf_por_tipo = {t: float(confianza[[p == t for p in predicciones]].mean()) for t in conteo}
    orden = sorted(conteo, key=lambda t: (-conteo[t], -conf_por_tipo[t]))
    reparto = [
        {
            "tipo": t,
            "nombre": tipos.get(t, {}).get("nombre", t),
            "cantidad": conteo[t],
            "porcentaje": round(100 * conteo[t] / len(filas), 1),
            "confianza": round(100 * conf_por_tipo[t], 1),
        }
        for t in orden
    ]
    return {"sugerida": orden[0], "nombre": reparto[0]["nombre"], "reparto": reparto, "por_cliente": predicciones}


def leer_metricas() -> dict | None:
    if not RUTA_METRICAS.exists():
        return None
    return json.loads(RUTA_METRICAS.read_text(encoding="utf-8"))
