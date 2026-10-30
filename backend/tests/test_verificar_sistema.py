from app.config import settings
from app.services import firebase
from scripts import verificar_sistema as v
from tests.test_chatbot import crear_campana_db


def estados(resultados) -> dict:
    return {nombre: estado for estado, nombre, _ in resultados}


def test_revision_informa_sin_romperse(monkeypatch):
    """Sin clave de Gemini, sin Firebase y sin migraciones (SQLite de pruebas): avisa, no se cae."""
    monkeypatch.setattr(firebase, "leer_ultimas", lambda: (_ for _ in ()).throw(ConnectionError()))
    r = estados(v.revisar(probar_gemini=False))
    assert r["Base de datos"] == v.OK and r["Usuarios"] == v.OK and r["Random Forest"] == v.OK
    assert r["Migraciones"] == v.ERROR
    assert r["Campañas vigentes"] == v.AVISO and r["Clima"] == v.AVISO
    assert r["Gemini"] == v.AVISO and r["Firebase"] == v.AVISO
    assert r["Datos de la empresa"] == v.AVISO  # quedan campos [COMPLETAR]


def test_revision_con_campana_vigente_y_gemini(monkeypatch):
    crear_campana_db("Siembra Segura 2026")
    monkeypatch.setattr(settings, "gemini_api_key", "clave-falsa")
    monkeypatch.setattr(v.ia, "llamar_gemini", lambda *a, **k: ("OK", "principal"))
    r = {nombre: (estado, detalle) for estado, nombre, detalle in v.revisar()}
    assert r["Campañas vigentes"] == (v.OK, "Siembra Segura 2026")
    assert r["Gemini"] == (v.OK, "Responde (modelo principal)")
