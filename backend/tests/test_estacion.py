from datetime import date, datetime, timedelta, timezone

import pytest

from app.config import cargar_umbrales
from app.services.consolidacion import agrupar_por_dia
from app.services.estacion import Dia, clasificar_estacion, comparar_periodos, diagnosticar
from scripts.generar_datos_clima import generar_registros

U = cargar_umbrales()
HOY = date(2026, 11, 30)


def dias_constantes(valores_por_semana):
    """Construye días terminando en HOY; cada tupla (temp, hum) es una semana."""
    total = 7 * len(valores_por_semana)
    return [
        Dia(HOY - timedelta(days=total - 1 - i), *valores_por_semana[i // 7])
        for i in range(total)
    ]


@pytest.mark.parametrize("temp, hum, esperado", [
    (20, 75, "lluvias"),       # límite exacto de humedad
    (20, 74.9, "transicion"),
    (12, 60, "invierno"),      # límite exacto de invierno
    (12.1, 60, "transicion"),
    (24, 60, "verano"),        # límite exacto de verano
    (23.9, 60, "transicion"),
    (10, 80, "lluvias"),       # la humedad tiene prioridad sobre la temperatura
    (30, 90, "lluvias"),
])
def test_clasificar_estacion(temp, hum, esperado):
    assert clasificar_estacion(temp, hum, U) == esperado


def test_umbrales_se_toman_de_la_configuracion():
    otros = {**U, "estacion": {**U["estacion"], "lluvias_humedad_min": 60}}
    assert clasificar_estacion(20, 65, U) == "transicion"
    assert clasificar_estacion(20, 65, otros) == "lluvias"


def test_aumento_de_humedad_anuncia_lluvias():
    dias = dias_constantes([(20, 60), (20, 72)])
    r = comparar_periodos(dias, 7, HOY, U)
    assert r["alerta"] and r["alerta_humedad"] and not r["alerta_temperatura"]
    assert r["cambio_humedad"] == 12.0
    assert r["temporada_proxima"] == "lluvias"
    assert r["mensaje"] == ("Esta semana se detectó un aumento de la humedad (+12,0 %), "
                            "y eso significa que se acerca la temporada de lluvias.")


def test_baja_de_temperatura_anuncia_invierno():
    r = comparar_periodos(dias_constantes([(16, 55), (13, 55)]), 7, HOY, U)
    assert r["temporada_proxima"] == "invierno"
    assert "disminución de la temperatura (−3,0 °C)" in r["mensaje"]


def test_subida_de_temperatura_anuncia_verano():
    r = comparar_periodos(dias_constantes([(20, 55), (23, 55)]), 7, HOY, U)
    assert r["temporada_proxima"] == "verano"


def test_baja_de_humedad_anuncia_fin_de_lluvias():
    r = comparar_periodos(dias_constantes([(20, 82), (20, 70)]), 7, HOY, U)
    assert r["temporada_proxima"] == "transicion"


def test_cambio_pequeno_no_genera_alerta():
    r = comparar_periodos(dias_constantes([(20, 60), (22.4, 67.9)]), 7, HOY, U)
    assert not r["alerta"] and r["temporada_proxima"] is None
    assert "no se detectaron cambios" in r["mensaje"]


def test_cambio_justo_en_el_umbral_si_alerta():
    r = comparar_periodos(dias_constantes([(20, 60), (22.5, 68)]), 7, HOY, U)
    assert r["alerta_humedad"] and r["alerta_temperatura"]
    assert "humedad (+8,0 %) y un aumento de la temperatura (+2,5 °C)" in r["mensaje"]


def test_sin_datos_suficientes():
    r = comparar_periodos(dias_constantes([(20, 60)]), 7, HOY, U)
    assert not r["suficientes_datos"] and not r["alerta"]


def test_comparacion_mensual():
    dias = dias_constantes([(20, 60)] * 4 + [(20, 70)] * 4)
    r = comparar_periodos(dias, 28, HOY, U)
    assert r["cambio_humedad"] == 10.0 and r["temporada_proxima"] == "lluvias"
    assert r["mensaje"].startswith("En los últimos 28 días")


def test_diagnostico_sin_datos():
    d = diagnosticar([], HOY, U)
    assert d["estacion_actual"] is None and not d["alerta"]


@pytest.mark.parametrize("escenario, temporada", [
    ("lluvias", "lluvias"), ("invierno", "invierno"), ("verano", "verano"),
])
def test_escenarios_simulados_detectan_su_temporada(escenario, temporada):
    registros = generar_registros(escenario, HOY)
    assert len(registros) == 56 and registros[-1]["fecha"] == HOY
    dias = [Dia(r["fecha"], r["temp_promedio"], r["humedad_promedio"]) for r in registros]
    d = diagnosticar(dias, HOY, U)
    assert d["alerta"] and d["temporada_proxima"] == temporada


def test_agrupar_por_dia_usa_hora_de_peru():
    def ms(año, mes, dia, hora):
        return int(datetime(año, mes, dia, hora, tzinfo=timezone.utc).timestamp() * 1000)

    lecturas = [
        {"ts": ms(2026, 10, 29, 3), "temperatura": 10, "humedad": 80},   # 22:00 del 28 en Perú
        {"ts": ms(2026, 10, 29, 4), "temperatura": 14, "humedad": 70},   # 23:00 del 28 en Perú
        {"ts": ms(2026, 10, 29, 15), "temperatura": 20, "humedad": 60},  # 10:00 del 29 en Perú
        {"ts": ms(2026, 10, 29, 16), "temperatura": "x"},               # incompleta: se ignora
    ]
    r = agrupar_por_dia(lecturas)
    assert set(r) == {date(2026, 10, 28), date(2026, 10, 29)}
    d28 = r[date(2026, 10, 28)]
    assert d28["temp_promedio"] == 12 and d28["temp_min"] == 10 and d28["temp_max"] == 14
    assert d28["humedad_promedio"] == 75 and d28["n_lecturas"] == 2
