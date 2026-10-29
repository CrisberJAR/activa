import json
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.config import hoy_peru, settings
from app.db import SessionLocal
from app.models import Campana
from app.schemas import CampanaEntrada
from app.services import campanas as servicio
from app.services import ia
from tests.conftest import ASESOR, GERENTE, iniciar_sesion
from tests.test_analisis import preparar_bloques


def datos_campana(**cambios) -> dict:
    datos = {
        "tipo_campana": "agro_siembra", "bloque_id": "", "temporada": "lluvias",
        "publico_objetivo": "Agricultores del valle", "necesidad": "Comprar semillas y abono antes de la siembra",
        "monto_maximo": "5000", "plazo_meses": "8", "zona": "Pillco Marca", "tipo_cliente": "ambos",
        "periodo_gracia_meses": "1", "fecha_inicio": hoy_peru().isoformat(), "duracion_semanas": "8",
        "presupuesto_difusion": "600", "meta_creditos": "25",
    }
    return {k: v for k, v in (datos | cambios).items() if v is not None}


def contenido_valido(**cambios) -> dict:
    datos = {
        "nombre": "Siembra Segura 2026",
        "propuesta_valor": "Crédito para comprar semillas y abono antes de las lluvias, sujeto a evaluación.",
        "decisiones_gerencia": ["Aprobar S/ 600 de difusión", "Asignar 2 asesores en Pillco Marca"],
        "capacitacion": {
            "speech": "Buenos días, en Grupo Activa le ayudamos a preparar su siembra antes de las lluvias.",
            "objeciones": [{"objecion": "No tengo garantía", "respuesta": "Evaluamos su negocio y su historial."}],
        },
        "marketing": {"canales": ["WhatsApp", "Visitas"], "gancho": "¡Siembra tranquilo!",
                      "mensaje_whatsapp": "Hola 👋 ¿Preparando la siembra? Tenemos un crédito para ti, sujeto a evaluación."},
    }
    return datos | cambios


def crear_campana(client, **cambios) -> int:
    client.post("/campanas/nueva", data=datos_campana(**cambios))
    with SessionLocal() as db:
        return db.scalars(select(Campana).order_by(Campana.id.desc())).first().id


def obtener(campana_id) -> Campana:
    with SessionLocal() as db:
        return db.get(Campana, campana_id)


# ---------- Reglas: tasas y promesas ----------

@pytest.mark.parametrize("texto", [
    "Crédito con TEA de 25% anual",
    "Tasa de interés del 3,5 % mensual",
    "Solo 2% de interés",
    "¡Aprobación garantizada!",
    "Crédito seguro para tu negocio",
    "Préstamo sin evaluación ni papeleo",
    "100% aprobado",
    "Te aprobamos hoy mismo",
])
def test_detecta_tasas_y_promesas(texto):
    assert servicio.infracciones(contenido_valido(propuesta_valor=texto + " para tu siembra."))


@pytest.mark.parametrize("texto", [
    "Crédito sujeto a evaluación para tu siembra.",
    "La gerencia define la tasa según la política vigente.",
    "Meta: llegar a un 30% más de clientes que el año pasado.",
])
def test_permite_textos_correctos(texto):
    assert servicio.infracciones(contenido_valido(propuesta_valor=texto)) == []


def test_validar_contenido():
    assert servicio.validar_contenido(json.dumps(contenido_valido()))["nombre"] == "Siembra Segura 2026"
    with pytest.raises(ia.ErrorIA) as e:
        servicio.validar_contenido("esto no es JSON")
    assert e.value.reintentable
    with pytest.raises(ia.ErrorIA, match="tasa"):
        servicio.validar_contenido(json.dumps(contenido_valido(nombre="Campaña TEA 20% anual")))
    with pytest.raises(ia.ErrorIA):
        servicio.validar_contenido(json.dumps({"nombre": "Incompleta"}))


def test_plantilla_es_valida_y_respeta_las_reglas():
    for tipo in ("agro_siembra", "campana_navidena", "salud_emergencia"):
        entrada = CampanaEntrada(**datos_campana(tipo_campana=tipo, monto_maximo=""))
        contenido = servicio.contenido_plantilla(entrada)
        assert servicio.infracciones(contenido) == []
        assert "sujeto a evaluación" in contenido["propuesta_valor"].lower()


def test_si_un_modelo_inventa_una_tasa_se_usa_el_siguiente(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "clave-falsa")
    monkeypatch.setattr(settings, "gemini_modelo", "principal")
    monkeypatch.setattr(settings, "gemini_modelos_respaldo", "respaldo")
    respuestas = {
        "principal": json.dumps(contenido_valido(propuesta_valor="Crédito con TEA de 30% anual para tu siembra.")),
        "respaldo": json.dumps(contenido_valido()),
    }
    monkeypatch.setattr(ia, "llamar_modelo", lambda prompt, modelo, json=False, timeout=25: respuestas[modelo])
    contenido, generado_con, error = servicio.generar_contenido(CampanaEntrada(**datos_campana()), [])
    assert generado_con == "respaldo" and error is None
    assert contenido["nombre"] == "Siembra Segura 2026"


def test_vigencia_y_estado_visible():
    hoy = hoy_peru()
    entrada = CampanaEntrada(**datos_campana(fecha_inicio=hoy.isoformat(), duracion_semanas="2"))
    desde, hasta = servicio.vigencia(entrada)
    assert desde == hoy and hasta == hoy + timedelta(days=13)
    c = Campana(estado="publicada", vigente_desde=desde, vigente_hasta=hasta)
    assert servicio.estado_visible(c, hoy) == "vigente"
    assert servicio.estado_visible(c, hoy - timedelta(days=1)) == "programada"
    assert servicio.estado_visible(c, hasta + timedelta(days=1)) == "finalizada"


# ---------- Flujo web y permisos ----------

def test_asesor_genera_borrador_sin_enviar_datos_personales(client, monkeypatch):
    enviados = []

    def gemini_falso(prompt, **opciones):
        enviados.append(prompt)
        if "validar" not in opciones:  # texto del análisis del bloque
            return "Los agricultores necesitan insumos.", "modelo-prueba"
        return opciones["validar"](json.dumps(contenido_valido())), "modelo-prueba"

    monkeypatch.setattr(ia, "llamar_gemini", gemini_falso)
    b1, _, _ = preparar_bloques()
    iniciar_sesion(client, ASESOR)
    client.post(f"/analisis/{b1}")  # el análisis del bloque da contexto a la campaña
    campana_id = crear_campana(client, bloque_id=str(b1))
    c = obtener(campana_id)
    assert c.estado == "borrador" and c.generado_con == "modelo-prueba" and c.bloque_id == b1
    prompt = enviados[-1]
    assert "Secreto" not in prompt and "98765432" not in prompt
    assert "Datos del bloque" in prompt and "NO menciones tasas" in prompt
    assert "Siembra Segura 2026" in client.get(f"/campanas/{campana_id}").text


def test_sin_gemini_se_crea_con_plantilla(client):
    iniciar_sesion(client, ASESOR)
    r = client.post("/campanas/nueva", data=datos_campana())
    assert "plantilla automática" in r.text
    c = obtener(crear_campana(client))
    assert c.generado_con == "plantilla" and c.estado == "borrador"


def test_formulario_valida_en_el_servidor(client):
    iniciar_sesion(client, ASESOR)
    r = client.post("/campanas/nueva", data=datos_campana(tipo_campana="inventado", duracion_semanas="40"))
    assert r.status_code == 422
    assert "Elige un tipo de campaña" in r.text and "menor o igual a 26" in r.text


def test_formulario_se_prellena_con_el_analisis(client):
    b1, _, _ = preparar_bloques()
    iniciar_sesion(client, ASESOR)
    client.post(f"/analisis/{b1}")
    pagina = client.get(f"/campanas/nueva?bloque_id={b1}").text
    assert "Sugerido por el Random Forest" in pagina
    assert 'value="Insumos agrícolas' in pagina and "Amarilis" in pagina


def test_asesor_no_edita_ni_publica(client):
    iniciar_sesion(client, ASESOR)
    campana_id = crear_campana(client)
    assert client.get(f"/campanas/{campana_id}/editar").status_code == 403
    for accion in ("editar", "regenerar", "publicar", "eliminar"):
        assert client.post(f"/campanas/{campana_id}/{accion}").status_code == 403
    assert obtener(campana_id).estado == "borrador"
    assert "el gerente la revisa" in client.get(f"/campanas/{campana_id}").text


def formulario_edicion(**cambios) -> dict:
    datos = {
        "nombre": "Siembra Activa", "propuesta_valor": "Crédito para la siembra, sujeto a evaluación.",
        "decisiones_gerencia": "Aprobar difusión\nAsignar asesores", "speech": "Hola, le presento nuestra campaña de siembra.",
        "objecion_0": "No tengo aval", "respuesta_0": "Evaluamos su caso", "canales": "WhatsApp\nRadio local",
        "gancho": "¡Siembra con Activa!", "mensaje_whatsapp": "Hola 👋 tenemos un crédito para tu siembra.",
        "fecha_inicio": hoy_peru().isoformat(), "duracion_semanas": "4",
    }
    return datos | cambios


def test_gerente_edita_publica_y_retira(client):
    iniciar_sesion(client, GERENTE)
    campana_id = crear_campana(client)
    assert client.get(f"/campanas/{campana_id}/editar").status_code == 200
    r = client.post(f"/campanas/{campana_id}/editar", data=formulario_edicion(), follow_redirects=False)
    assert r.status_code == 303
    c = obtener(campana_id)
    assert c.nombre == "Siembra Activa" and c.contenido["marketing"]["canales"] == ["WhatsApp", "Radio local"]
    assert c.vigente_hasta == hoy_peru() + timedelta(days=27)

    assert client.get("/api/campanas/vigentes").json() == []  # borrador: aún no es vigente
    client.post(f"/campanas/{campana_id}/publicar")
    assert obtener(campana_id).estado == "publicada"
    vigentes = client.get("/api/campanas/vigentes").json()
    assert [v["id"] for v in vigentes] == [campana_id] and vigentes[0]["estado"] == "vigente"

    assert client.post(f"/campanas/{campana_id}/editar", data=formulario_edicion()).status_code == 409
    client.post(f"/campanas/{campana_id}/retirar")
    assert obtener(campana_id).estado == "retirada"
    assert client.get("/api/campanas/vigentes").json() == []


def test_edicion_invalida_muestra_errores(client):
    iniciar_sesion(client, GERENTE)
    campana_id = crear_campana(client)
    r = client.post(f"/campanas/{campana_id}/editar",
                    data=formulario_edicion(objecion_0="", respuesta_0="", gancho="", duracion_semanas="0"))
    assert r.status_code == 422
    assert "is-invalid" in r.text and "mayor o igual a 1" in r.text
    assert obtener(campana_id).nombre != "Siembra Activa"


def test_campana_programada_no_es_vigente_y_fecha_pasada_no_se_publica(client):
    iniciar_sesion(client, GERENTE)
    futura = crear_campana(client, fecha_inicio=(hoy_peru() + timedelta(days=10)).isoformat())
    client.post(f"/campanas/{futura}/publicar")
    assert client.get("/api/campanas/vigentes").json() == []
    assert "programada" in client.get("/campanas").text

    pasada = crear_campana(client, fecha_inicio=(hoy_peru() - timedelta(days=60)).isoformat(), duracion_semanas="2")
    assert "fecha de fin ya pasó" in client.post(f"/campanas/{pasada}/publicar").text
    assert obtener(pasada).estado == "borrador"


def test_gerente_elimina_borrador(client):
    iniciar_sesion(client, GERENTE)
    campana_id = crear_campana(client)
    client.post(f"/campanas/{campana_id}/eliminar")
    assert obtener(campana_id) is None


def test_api_vigentes_requiere_sesion(client):
    assert client.get("/api/campanas/vigentes").status_code == 401
