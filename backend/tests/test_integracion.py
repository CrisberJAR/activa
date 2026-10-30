"""Prueba de punta a punta (Fase 7): recorre el sistema completo como lo usarían las personas.

Gerente crea bloque → asesor registra encuestas → análisis + Random Forest → campaña (borrador)
→ gerente publica → aparece en la página pública → cliente conversa con Uku → queda como
interesado → asesor lo atiende. Además: la app móvil lee el clima con su token.

Gemini se simula caído a propósito: el sistema debe funcionar igual con sus plantillas,
y ningún nombre ni teléfono real debe aparecer en lo que se le habría enviado.
"""
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import cargar_tipos_campana, settings
from app.db import SessionLocal
from app.main import app
from app.models import AnalisisBloque, Bloque, Campana, Encuesta, Interesado
from app.services import ia
from tests.conftest import ASESOR, GERENTE, iniciar_sesion
from tests.test_bloques_encuestas import datos_encuesta
from tests.test_campanas import datos_campana
from tests.test_chatbot import Chat
from tests.test_clima import cargar_escenario

CLIENTES = [
    ("Rosa Quispe Tarazona", "987111001", "Comprar semillas y abono antes de las lluvias"),
    ("Juan Ñaupari Cóndor", "987111002", "Semillas de papa para la siembra"),
    ("Elena Ramos Vela", "987111003", "Comprar abono y fertilizante"),
    ("Pedro Huamán Soto", "987111004", "Semillas mejoradas de maíz"),
    ("Lucía Torres Ayala", "987111005", "Abono para la chacra"),
]
CLIENTE_CHAT = ("María Huamán", "987222333")


def test_flujo_completo_del_sistema(client, monkeypatch):
    # Gemini "caído": registra lo que se le enviaría y falla para que se usen las plantillas
    enviados = []

    def gemini_caido(prompt, modelo, json=False, timeout=25):
        enviados.append(prompt)
        raise ia.ErrorIA("503 simulado", reintentable=True)

    monkeypatch.setattr(settings, "gemini_api_key", "clave-falsa")
    monkeypatch.setattr(ia, "llamar_modelo", gemini_caido)

    # 0. El sensor IoT ya consolidó 8 semanas de clima (llegan las lluvias)
    cargar_escenario("lluvias")

    gerente, asesor, publico = client, TestClient(app), TestClient(app)
    iniciar_sesion(gerente, GERENTE)
    iniciar_sesion(asesor, ASESOR)

    # 1. El gerente crea un bloque de encuestas
    r = gerente.post("/bloques", data={"nombre": "Valle de Pillco Marca", "fecha_inicio": "2026-10-01"},
                     follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        bloque_id = db.scalar(select(Bloque.id).where(Bloque.nombre == "Valle de Pillco Marca"))

    # 2. El asesor registra las encuestas en ese bloque
    for nombre, telefono, necesidad in CLIENTES:
        r = asesor.post("/encuestas/nueva", data=datos_encuesta(bloque_id, nombre=nombre, telefono=telefono,
                                                                necesidad=necesidad), follow_redirects=False)
        assert r.status_code == 303
    with SessionLocal() as db:
        assert len(db.scalars(select(Encuesta).where(Encuesta.bloque_id == bloque_id)).all()) == len(CLIENTES)

    # 3. Análisis del bloque: ranking, estación del IoT y tipo sugerido por el Random Forest
    assert asesor.post(f"/analisis/{bloque_id}", follow_redirects=False).status_code == 303
    with SessionLocal() as db:
        analisis = db.scalar(select(AnalisisBloque).where(AnalisisBloque.bloque_id == bloque_id))
        assert analisis.ranking_necesidades[0]["categoria"] == "insumos_agricolas"
        assert analisis.indicadores["estacion_actual"] == "transicion"  # promedio de 28 días; las lluvias recién llegan
        assert analisis.indicadores["fuente_texto"] == "plantilla"
        sugerido = analisis.tipo_campana_sugerida
    assert sugerido in cargar_tipos_campana()
    assert "Insumos agrícolas" in asesor.get(f"/analisis?bloque_id={bloque_id}").text

    # 4. El asesor genera la campaña con la sugerencia: queda en borrador y no puede publicarla
    r = asesor.post("/campanas/nueva", data=datos_campana(tipo_campana=sugerido, bloque_id=str(bloque_id)),
                    follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        campana = db.scalars(select(Campana).order_by(Campana.id.desc())).first()
        campana_id, nombre_campana = campana.id, campana.nombre
        assert campana.estado == "borrador" and campana.generado_con == "plantilla"
        assert campana.bloque_id == bloque_id
    assert asesor.post(f"/campanas/{campana_id}/publicar").status_code == 403
    assert nombre_campana not in publico.get("/").text

    # 5. El gerente la publica: aparece en la API para el chatbot y en la página pública
    assert gerente.post(f"/campanas/{campana_id}/publicar", follow_redirects=False).status_code == 303
    vigentes = asesor.get("/api/campanas/vigentes").json()
    assert [c["id"] for c in vigentes] == [campana_id]
    assert nombre_campana in publico.get("/").text

    # 6. Un cliente pulsa "Me interesa", conversa con Uku y deja sus datos
    nombre, telefono = CLIENTE_CHAT
    chat = Chat(publico, campana_id=campana_id)
    chat("Agricultor")
    assert chat.ultimo["estado"] == "oferta" and nombre_campana in chat.texto()
    chat("Sí, me interesa")
    assert "Ley 29733" in chat.texto()
    chat("Sí, acepto")
    chat(nombre)
    chat("987 222 333")
    assert chat.ultimo["estado"] == "derivado"
    with SessionLocal() as db:
        interesado = db.scalar(select(Interesado))
        assert (interesado.nombre, interesado.telefono) == (nombre, telefono)
        assert interesado.consentimiento and interesado.campana_id == campana_id and not interesado.atendido

    # 7. El asesor lo ve en su panel con WhatsApp y lo marca como atendido
    panel = asesor.get("/interesados").text
    assert nombre in panel and f"wa.me/51{telefono}" in panel
    asesor.post(f"/interesados/{interesado.id}/atendido")  # sigue la redirección y consume el aviso
    assert nombre not in asesor.get("/interesados?estado=pendientes").text
    assert nombre in asesor.get("/interesados?estado=atendidos").text

    # 8. La app móvil consulta el clima con su token
    token = publico.post("/api/auth/token", data={"username": ASESOR["email"], "password": ASESOR["password"]})
    d = publico.get("/api/clima/diagnostico", headers={"Authorization": f"Bearer {token.json()['access_token']}"})
    assert d.status_code == 200 and d.json()["temporada_proxima"] == "lluvias"

    # Privacidad: Gemini fue consultado, pero nunca con nombres ni teléfonos reales
    assert enviados
    todo = "\n".join(enviados)
    for nombre_real, telefono_real, _ in CLIENTES + [CLIENTE_CHAT + ("",)]:
        assert telefono_real not in todo
        assert all(parte not in todo for parte in nombre_real.split())
