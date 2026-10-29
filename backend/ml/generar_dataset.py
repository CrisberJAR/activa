"""Dataset SINTÉTICO para entrenar el Random Forest (no son clientes reales).

No existe historial real de campañas, así que cada cliente se genera a partir de un tipo de
campaña con un "perfil" de reglas del negocio (sector, necesidad, mes, temporada, montos)
y se le agrega ruido aleatorio para que no sea perfecto. Se declara como limitación.

Uso (desde backend/):  python -m ml.generar_dataset
"""
import random

import pandas as pd

from app.config import BASE_DIR, cargar_necesidades
from app.services.analisis import clasificar
from app.services.ml import VARIABLES, caracteristicas

RUIDO = 0.10  # probabilidad de alterar la necesidad, el mes o la temporada de un cliente
TODOS_MESES = list(range(1, 13))
TODAS_TEMPORADAS = ["lluvias", "invierno", "verano", "transicion", "todo_el_anio"]
RIESGO_POR_TEMPORADA = {"lluvias": "lluvias", "invierno": "heladas", "verano": "sequia"}

# Perfil de cada tipo: pesos de sector y de categoría de necesidad, meses, temporadas, riesgos y montos
PERFILES = {
    "campana_navidena": dict(
        sectores={"comerciante": 6, "ambulante": 3}, categorias={"navidad": 5, "mercaderia": 4, "capital_trabajo": 1},
        meses=[9, 10, 11, 12], temporadas=["lluvias", "transicion", "verano", "todo_el_anio"],
        riesgos=["bajas_ventas", "alza_precios"], monto=(1500, 12000), plazo=(3, 8)),
    "campana_escolar": dict(
        sectores={"comerciante": 6, "ambulante": 3}, categorias={"escolar": 6, "mercaderia": 3, "capital_trabajo": 1},
        meses=[12, 1, 2, 3], temporadas=["verano", "lluvias", "todo_el_anio"],
        riesgos=["bajas_ventas", "alza_precios"], monto=(1000, 10000), plazo=(3, 8)),
    "campana_fiestas_patrias": dict(
        sectores={"comerciante": 6, "ambulante": 3}, categorias={"fiestas_patrias": 5, "mercaderia": 4, "capital_trabajo": 1},
        meses=[5, 6, 7], temporadas=["invierno", "transicion", "todo_el_anio"],
        riesgos=["bajas_ventas", "alza_precios"], monto=(1000, 10000), plazo=(3, 6)),
    "campana_dia_madre_padre": dict(
        sectores={"comerciante": 7, "ambulante": 3}, categorias={"dia_madre_padre": 6, "mercaderia": 3, "equipamiento": 1},
        meses=[3, 4, 5, 6], temporadas=["transicion", "invierno", "todo_el_anio"],
        riesgos=["bajas_ventas", "alza_precios"], monto=(800, 8000), plazo=(2, 6)),
    "campana_cyber_black": dict(
        sectores={"comerciante": 7, "ambulante": 2}, categorias={"ecommerce": 7, "mercaderia": 3},
        meses=[4, 5, 6, 7, 10, 11], temporadas=["todo_el_anio"],
        riesgos=["bajas_ventas", "alza_precios"], monto=(2000, 15000), plazo=(3, 10)),
    "comercio_temporada": dict(
        sectores={"comerciante": 5, "ambulante": 5},
        categorias={"mercaderia": 5, "proteccion_clima": 3, "capital_trabajo": 2, "equipamiento": 1},
        meses=TODOS_MESES, temporadas=["lluvias", "invierno", "verano"],
        riesgos=None, monto=(500, 6000), plazo=(3, 8)),
    "agro_siembra": dict(
        sectores={"agricola": 1}, categorias={"insumos_agricolas": 6, "mano_obra": 3, "capital_trabajo": 1},
        meses=[8, 9, 10, 11, 12, 1, 4, 5, 6], temporadas=["lluvias", "transicion"],
        riesgos=["lluvias", "alza_precios", "bajas_ventas"], monto=(1500, 10000), plazo=(4, 12)),
    "agro_clima": dict(
        sectores={"agricola": 1}, categorias={"proteccion_clima": 5, "riego": 4, "construccion": 1},
        meses=TODOS_MESES, temporadas=["invierno", "verano", "lluvias"],
        riesgos=None, monto=(1500, 12000), plazo=(6, 18)),
    "agro_pecuaria": dict(
        sectores={"agricola": 1}, categorias={"pecuario": 8, "insumos_agricolas": 1, "capital_trabajo": 1},
        meses=TODOS_MESES, temporadas=TODAS_TEMPORADAS,
        riesgos=["heladas", "salud", "alza_precios"], monto=(1500, 15000), plazo=(6, 18)),
    "equipamiento": dict(
        sectores={"comerciante": 4, "ambulante": 3, "agricola": 2, "taxista": 1},
        categorias={"equipamiento": 8, "capital_trabajo": 1, "mercaderia": 1},
        meses=TODOS_MESES, temporadas=TODAS_TEMPORADAS,
        riesgos=["bajas_ventas", "alza_precios"], monto=(1500, 20000), plazo=(6, 24)),
    "movilidad": dict(
        sectores={"taxista": 1}, categorias={"vehiculo": 9, "capital_trabajo": 1},
        meses=TODOS_MESES, temporadas=TODAS_TEMPORADAS,
        riesgos=["lluvias", "alza_precios", "salud"], monto=(800, 6000), plazo=(3, 12)),
    "credito_vehicular": dict(
        sectores={"taxista": 6, "ambulante": 2, "comerciante": 2}, categorias={"compra_vehiculo": 9, "vehiculo": 1},
        meses=TODOS_MESES, temporadas=["todo_el_anio"],
        riesgos=["bajas_ventas", "alza_precios"], monto=(8000, 45000), plazo=(18, 48)),
    "capital_trabajo": dict(
        sectores={"comerciante": 4, "ambulante": 3, "taxista": 1, "agricola": 1},
        categorias={"capital_trabajo": 5, "mercaderia": 3, "deudas": 2},
        meses=TODOS_MESES, temporadas=["todo_el_anio", "transicion"],
        riesgos=["bajas_ventas", "alza_precios", "otro"], monto=(500, 6000), plazo=(3, 12)),
    "construccion_vivienda": dict(
        sectores={"comerciante": 3, "agricola": 3, "taxista": 2, "ambulante": 2}, categorias={"construccion": 9, "otros": 1},
        meses=TODOS_MESES, temporadas=["todo_el_anio", "lluvias"],
        riesgos=["lluvias", "otro"], monto=(3000, 25000), plazo=(12, 36)),
    "salud_emergencia": dict(
        sectores={"comerciante": 3, "agricola": 3, "taxista": 2, "ambulante": 2}, categorias={"salud": 9, "otros": 1},
        meses=TODOS_MESES, temporadas=["todo_el_anio"],
        riesgos=["salud"], monto=(500, 5000), plazo=(3, 12)),
}

# Datos generales según el sector
INGRESO = {"agricola": (900, 3000), "comerciante": (1500, 5000), "ambulante": (700, 2000), "taxista": (1500, 3500)}
FRECUENCIA = {"agricola": ["cosecha", "cosecha", "mensual"], "comerciante": ["diaria", "semanal"],
              "ambulante": ["diaria"], "taxista": ["diaria"]}
GARANTIA = {"agricola": ["propiedad", "aval", "ninguna"], "comerciante": ["aval", "ninguna", "propiedad"],
            "ambulante": ["ninguna", "aval"], "taxista": ["vehiculo", "aval", "ninguna"]}
TRABAJADORES = {"agricola": 5, "comerciante": 3, "ambulante": 1, "taxista": 1}


def _elegir(rng: random.Random, pesos: dict) -> str:
    return rng.choices(list(pesos), weights=list(pesos.values()))[0]


def generar(n_por_tipo: int = 100, semilla: int = 42) -> pd.DataFrame:
    """Genera n clientes por cada tipo de campaña. Misma semilla = mismo dataset."""
    rng = random.Random(semilla)
    todas_categorias = list(cargar_necesidades()["categorias"]) + ["otros"]
    filas = []
    for tipo, p in PERFILES.items():
        for _ in range(n_por_tipo):
            sector = _elegir(rng, p["sectores"])
            categoria = _elegir(rng, p["categorias"])
            mes = rng.choice(p["meses"])
            temporada = rng.choice(p["temporadas"])
            riesgo = rng.choice(p["riesgos"]) if p["riesgos"] else RIESGO_POR_TEMPORADA[temporada]
            # Ruido: algunos clientes no siguen el perfil
            if rng.random() < RUIDO:
                categoria = rng.choice(todas_categorias)
            if rng.random() < RUIDO:
                mes = rng.choice(TODOS_MESES)
            if rng.random() < RUIDO:
                temporada = rng.choice(TODAS_TEMPORADAS)
            encuesta = {
                "sector": sector,
                "temporada_necesidad": temporada,
                "riesgo_principal": riesgo,
                "frecuencia_ingresos": rng.choice(FRECUENCIA[sector]),
                "garantia": rng.choice(GARANTIA[sector]),
                "ingreso_mensual": round(rng.uniform(*INGRESO[sector]), -1),
                "monto": round(rng.uniform(*p["monto"]), -2),
                "plazo_meses": rng.randint(*p["plazo"]),
                "anios_negocio": rng.randint(1, 30),
                "trabajadores": rng.randint(0, TRABAJADORES[sector]),
                "credito_vigente": rng.random() < 0.3,
            }
            filas.append(caracteristicas(encuesta, categoria, mes) | {"tipo": tipo})
    return pd.DataFrame(filas, columns=VARIABLES + ["tipo"])


# Tipo correcto de las 20 encuestas de ejemplo (scripts/seed_encuestas.py), en el mismo orden.
# Etiquetadas a mano según el criterio del negocio; sirven como prueba con datos que el modelo no vio.
ETIQUETAS_REALES = [
    # Bloque 1 – Mercado Modelo
    "campana_navidena", "construccion_vivienda", "capital_trabajo", "comercio_temporada",
    "comercio_temporada", "equipamiento", "campana_fiestas_patrias",
    # Bloque 2 – Valle agrícola
    "agro_siembra", "agro_clima", "agro_clima", "agro_clima", "agro_siembra", "agro_siembra", "agro_clima",
    # Bloque 3 – Taxistas y ambulantes
    "movilidad", "movilidad", "movilidad", "equipamiento", "comercio_temporada", "movilidad",
]
MES_REALES = 10  # las encuestas de ejemplo se registraron en octubre


def reales() -> pd.DataFrame:
    """Las 20 encuestas de ejemplo con su tipo correcto (sin nombre ni teléfono)."""
    from scripts.seed_encuestas import ENCUESTAS

    config = cargar_necesidades()
    filas = []
    for f, tipo in zip(ENCUESTAS, ETIQUETAS_REALES, strict=True):
        encuesta = {
            "sector": f[3], "ingreso_mensual": f[4], "anios_negocio": f[5], "trabajadores": f[6],
            "frecuencia_ingresos": f[7], "credito_vigente": f[8], "garantia": f[9], "monto": f[11],
            "plazo_meses": f[12], "temporada_necesidad": f[13], "riesgo_principal": f[14],
        }
        fila = caracteristicas(encuesta, clasificar(f[10], config), MES_REALES)
        filas.append(fila | {"tipo": tipo, "necesidad": f[10]})
    return pd.DataFrame(filas, columns=VARIABLES + ["tipo", "necesidad"])


def main():
    sintetico = generar()
    sintetico.to_csv(BASE_DIR / "ml" / "dataset_sintetico.csv", index=False, encoding="utf-8")
    reales().to_csv(BASE_DIR / "ml" / "encuestas_reales_etiquetadas.csv", index=False, encoding="utf-8")
    print(f"Dataset sintético: {len(sintetico)} filas ({sintetico['tipo'].nunique()} tipos) -> ml/dataset_sintetico.csv")
    print("Encuestas reales etiquetadas: 20 -> ml/encuestas_reales_etiquetadas.csv")


if __name__ == "__main__":
    main()
