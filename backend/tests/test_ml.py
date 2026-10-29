import pandas as pd
import pytest
from sqlalchemy import select

from app.config import cargar_tipos_campana
from app.db import SessionLocal
from app.models import AnalisisBloque
from app.services import ml
from ml.entrenar import evaluar
from ml.generar_dataset import ETIQUETAS_REALES, generar, reales
from tests.conftest import ASESOR, iniciar_sesion
from tests.test_analisis import encuesta, preparar_bloques

TIPOS = cargar_tipos_campana()


@pytest.fixture(scope="module")
def entrenado():
    """Modelo pequeño (rápido) entrenado una sola vez para todas las pruebas de este archivo."""
    return evaluar(generar(n_por_tipo=40), reales(), arboles=30)


def fila(categoria, mes, **cambios):
    return ml.caracteristicas(encuesta(**cambios), categoria, mes)


# ---------- Dataset ----------

def test_dataset_sintetico_es_reproducible_y_cubre_todos_los_tipos():
    a, b = generar(n_por_tipo=5, semilla=1), generar(n_por_tipo=5, semilla=1)
    pd.testing.assert_frame_equal(a, b)
    assert set(a["tipo"]) == set(TIPOS) and len(a) == 5 * len(TIPOS)
    assert list(a.columns) == ml.VARIABLES + ["tipo"]


def test_encuestas_reales_sin_datos_personales_y_con_tipos_validos():
    datos = reales()
    assert len(datos) == 20 and set(ETIQUETAS_REALES) <= set(TIPOS)
    assert "nombre" not in datos.columns and "telefono" not in datos.columns


def test_caracteristicas_no_incluyen_datos_personales():
    datos = fila("insumos_agricolas", 10) | {}
    assert set(datos) == set(ml.VARIABLES)
    assert datos["credito_vigente"] == 0 and datos["mes"] == 10


# ---------- Entrenamiento y predicción ----------

def test_entrenamiento_produce_metricas(entrenado):
    _, m = entrenado
    assert m["prueba"]["exactitud"] > 0.7
    assert set(m["prueba"]["por_tipo"]) == set(TIPOS)
    assert len(m["reales"]["filas"]) == 20
    assert sum(i["valor"] for i in m["importancia"]) == pytest.approx(1, abs=0.01)
    assert {i["variable"] for i in m["importancia"]} == set(ml.VARIABLES)


@pytest.mark.parametrize("categoria, mes, cambios, esperado", [
    ("insumos_agricolas", 10, {}, "agro_siembra"),
    ("navidad", 11, {"sector": "comerciante", "temporada_necesidad": "todo_el_anio",
                     "riesgo_principal": "bajas_ventas", "frecuencia_ingresos": "diaria"}, "campana_navidena"),
    ("vehiculo", 6, {"sector": "taxista", "garantia": "vehiculo", "frecuencia_ingresos": "diaria"}, "movilidad"),
    ("salud", 3, {"sector": "ambulante", "riesgo_principal": "salud", "temporada_necesidad": "todo_el_anio"}, "salud_emergencia"),
])
def test_predice_casos_claros(entrenado, categoria, mes, cambios, esperado):
    modelo, _ = entrenado
    datos = pd.DataFrame([fila(categoria, mes, **cambios)], columns=ml.VARIABLES)
    assert modelo.predict(datos)[0] == esperado


def test_sugerir_elige_el_tipo_mas_frecuente(entrenado, monkeypatch):
    monkeypatch.setattr(ml, "cargar_modelo", lambda: entrenado[0])
    filas = [fila("insumos_agricolas", 10)] * 3 + [fila("vehiculo", 6, sector="taxista", garantia="vehiculo")]
    s = ml.sugerir(filas)
    assert s["sugerida"] == "agro_siembra" and s["nombre"] == TIPOS["agro_siembra"]["nombre"]
    assert s["reparto"][0]["cantidad"] == 3 and s["reparto"][0]["porcentaje"] == 75.0
    assert sum(r["cantidad"] for r in s["reparto"]) == 4


def test_modelo_del_repositorio_carga_y_predice():
    """El modelo guardado en ml/modelo.joblib debe cargar con la versión instalada de scikit-learn."""
    ml.cargar_modelo.cache_clear()
    s = ml.sugerir([fila("insumos_agricolas", 10)])
    assert s is not None and s["sugerida"] in TIPOS
    assert ml.leer_metricas()["n_sintetico"] > 0


# ---------- Integración con el análisis del bloque ----------

def test_analisis_guarda_la_campana_sugerida(client, entrenado, monkeypatch):
    monkeypatch.setattr(ml, "cargar_modelo", lambda: entrenado[0])
    b1, _, _ = preparar_bloques()  # 2 encuestas agrícolas: semillas y abono
    iniciar_sesion(client, ASESOR)
    client.post(f"/analisis/{b1}")
    with SessionLocal() as db:
        analisis = db.scalar(select(AnalisisBloque))
        assert analisis.tipo_campana_sugerida == "agro_siembra"
        assert analisis.indicadores["campana_modelo"]["reparto"][0]["cantidad"] == 2
    pagina = client.get(f"/analisis?bloque_id={b1}").text
    assert TIPOS["agro_siembra"]["nombre"] in pagina


def test_sin_modelo_el_analisis_sigue_funcionando(client, monkeypatch):
    monkeypatch.setattr(ml, "cargar_modelo", lambda: None)
    b1, _, _ = preparar_bloques()
    iniciar_sesion(client, ASESOR)
    client.post(f"/analisis/{b1}")
    with SessionLocal() as db:
        analisis = db.scalar(select(AnalisisBloque))
        assert analisis.tipo_campana_sugerida is None and analisis.indicadores["total"] == 2
    assert "no está entrenado" in client.get(f"/analisis?bloque_id={b1}").text


def test_pagina_de_metricas(client, entrenado, monkeypatch):
    iniciar_sesion(client, ASESOR)
    monkeypatch.setattr(ml, "leer_metricas", lambda: entrenado[1])
    pagina = client.get("/analisis/modelo").text
    assert "Matriz de confusión" in pagina and "sintéticos" in pagina
    monkeypatch.setattr(ml, "leer_metricas", lambda: None)
    assert "todavía no está entrenado" in client.get("/analisis/modelo").text
