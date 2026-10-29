from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.config import HORA_PERU, hoy_peru
from app.db import SessionLocal
from app.models import Diagnostico, RegistroDiario, Sensor
from app.services import firebase
from scripts.generar_datos_clima import generar_registros
from tests.conftest import ASESOR, GERENTE, iniciar_sesion


def ts_hoy(hora):
    momento = datetime.combine(hoy_peru(), datetime.min.time(), tzinfo=HORA_PERU) + timedelta(hours=hora)
    return int(momento.timestamp() * 1000)


LECTURAS = {
    "sensor-agricola-01": [
        {"temperatura": 18.0, "humedad": 70.0, "sector": "agricola", "ts": ts_hoy(8)},
        {"temperatura": 20.0, "humedad": 74.0, "sector": "agricola", "ts": ts_hoy(9)},
    ]
}


@pytest.fixture(autouse=True)
def firebase_simulado(monkeypatch):
    """Reemplaza Firebase por datos fijos: las pruebas no salen a internet."""
    monkeypatch.setattr(firebase, "leer_ultimas", lambda: {k: v[-1] for k, v in LECTURAS.items()})
    monkeypatch.setattr(firebase, "leer_lecturas", lambda sensor, desde_ms: LECTURAS[sensor])


def cargar_escenario(escenario="lluvias"):
    with SessionLocal() as db:
        sensor = Sensor(codigo="sim-test", sector="agricola")
        db.add(sensor)
        db.flush()
        db.add_all(RegistroDiario(sensor_id=sensor.id, **r) for r in generar_registros(escenario, hoy_peru()))
        db.commit()


def test_gerente_consolida_desde_firebase(client):
    iniciar_sesion(client, GERENTE)
    assert client.post("/clima/consolidar", follow_redirects=False).status_code == 303
    client.post("/clima/consolidar")  # volver a correrlo no duplica
    with SessionLocal() as db:
        sensor = db.scalar(select(Sensor).where(Sensor.codigo == "sensor-agricola-01"))
        assert sensor.sector == "agricola"
        registros = db.scalars(select(RegistroDiario)).all()
        assert len(registros) == 1
        assert registros[0].temp_promedio == 19.0 and registros[0].humedad_promedio == 72.0
        assert registros[0].n_lecturas == 2 and registros[0].fecha == hoy_peru()


def test_asesor_no_puede_consolidar(client):
    iniciar_sesion(client, ASESOR)
    assert client.post("/clima/consolidar").status_code == 403


def test_diagnostico_por_api_con_sesion(client):
    cargar_escenario("lluvias")
    iniciar_sesion(client, ASESOR)
    d = client.get("/api/clima/diagnostico").json()
    assert d["temporada_proxima"] == "lluvias" and d["alerta"]
    assert "aumento de la humedad" in d["mensaje"]


def test_api_funciona_con_token_de_la_app(client):
    cargar_escenario("verano")
    token = client.post("/api/auth/token", data={"username": ASESOR["email"], "password": ASESOR["password"]}).json()["access_token"]
    r = client.get("/api/clima/diagnostico", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["temporada_proxima"] == "verano"


def test_api_sin_autenticacion(client):
    assert client.get("/api/clima/diagnostico").status_code == 401


def test_api_registros_y_analisis(client):
    cargar_escenario("invierno")
    iniciar_sesion(client, ASESOR)
    registros = client.get("/api/clima/registros?dias=28").json()
    assert len(registros) == 28 and registros[-1]["fecha"] == hoy_peru().isoformat()
    semana = client.get("/api/clima/analisis?periodo=7").json()
    assert semana["temporada_proxima"] == "invierno"
    assert client.get("/api/clima/analisis?periodo=10").status_code == 422


def test_filtrar_por_sensor(client):
    cargar_escenario("lluvias")
    iniciar_sesion(client, ASESOR)
    assert client.get("/api/clima/registros?sensor=otro").json() == []


def test_api_sensores(client):
    cargar_escenario("lluvias")
    iniciar_sesion(client, ASESOR)
    assert client.get("/api/clima/sensores").json() == [{"codigo": "sim-test", "sector": "agricola", "ubicacion": None}]


def test_api_ultima_lectura(client):
    iniciar_sesion(client, ASESOR)
    ultima = client.get("/api/clima/ultima").json()
    assert ultima[0]["sensor"] == "sensor-agricola-01" and ultima[0]["humedad"] == 74.0


def test_pagina_clima(client):
    cargar_escenario("lluvias")
    iniciar_sesion(client, ASESOR)
    texto = client.get("/clima").text
    assert "Estación actual" in texto and "se acerca la temporada de lluvias" in texto
    assert "Actualizar desde Firebase" not in texto  # botón solo para el gerente


def test_pagina_clima_sin_datos(client):
    iniciar_sesion(client, GERENTE)
    assert "Todavía no hay registros diarios" in client.get("/clima").text


def test_consolidar_guarda_diagnostico(client):
    cargar_escenario("lluvias")
    iniciar_sesion(client, GERENTE)
    client.post("/clima/consolidar")
    with SessionLocal() as db:
        filas = db.scalars(select(Diagnostico)).all()
        assert {f.periodo_dias for f in filas} == {7, 28}
        assert any(f.alerta for f in filas)
