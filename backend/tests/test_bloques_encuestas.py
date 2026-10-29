from datetime import date

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Bloque, Encuesta, Usuario
from tests.conftest import ASESOR, ASESOR2, GERENTE, iniciar_sesion


def crear_bloque(client, nombre="Bloque prueba"):
    """Prepara un bloque abierto directamente en la base (como si lo hubiera creado el gerente)."""
    with SessionLocal() as db:
        gerente = db.scalar(select(Usuario).where(Usuario.email == GERENTE["email"]))
        bloque = Bloque(nombre=nombre, fecha_inicio=date(2026, 10, 1), activo=True, creado_por=gerente.id)
        db.add(bloque)
        db.commit()
        return bloque.id


def cerrar_bloque(bloque_id):
    with SessionLocal() as db:
        db.get(Bloque, bloque_id).activo = False
        db.commit()


def datos_encuesta(bloque_id, **cambios):
    datos = {
        "bloque_id": str(bloque_id), "nombre": "Cliente Prueba", "telefono": "987654321", "zona": "Amarilis",
        "sector": "agricola", "ingreso_mensual": "1500", "anios_negocio": "5", "trabajadores": "1",
        "frecuencia_ingresos": "cosecha", "credito_vigente": "false", "garantia": "ninguna",
        "necesidad": "Comprar semillas antes de las lluvias", "monto": "3000", "plazo_meses": "6",
        "temporada_necesidad": "lluvias", "riesgo_principal": "lluvias", "interes_campana": "true",
        "contacto_preferido": "whatsapp", "consentimiento": "on",
    }
    datos.update(cambios)
    return {k: v for k, v in datos.items() if v is not None}


def contar_encuestas():
    with SessionLocal() as db:
        return len(db.scalars(select(Encuesta)).all())


def test_gerente_crea_bloque_y_queda_abierto(client):
    iniciar_sesion(client, GERENTE)
    r = client.post("/bloques", data={"nombre": "Bloque nuevo", "fecha_inicio": "2026-10-01"}, follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        assert db.scalar(select(Bloque).where(Bloque.nombre == "Bloque nuevo")).activo is True
    assert "Bloque nuevo" in client.get("/bloques").text


def test_gerente_abre_y_cierra_bloques(client):
    iniciar_sesion(client, GERENTE)
    bloque_id = crear_bloque(client)
    assert client.post(f"/bloques/{bloque_id}/estado", follow_redirects=False).status_code == 303
    with SessionLocal() as db:
        assert db.get(Bloque, bloque_id).activo is False


def test_asesor_no_puede_crear_bloques(client):
    iniciar_sesion(client, ASESOR)
    r = client.post("/bloques", data={"nombre": "Intento", "fecha_inicio": "2026-10-01"})
    assert r.status_code == 403
    with SessionLocal() as db:
        assert db.scalar(select(Bloque).where(Bloque.nombre == "Intento")) is None


def test_asesor_no_puede_abrir_ni_cerrar_bloques(client):
    bloque_id = crear_bloque(client)
    iniciar_sesion(client, ASESOR)
    assert client.post(f"/bloques/{bloque_id}/estado").status_code == 403
    with SessionLocal() as db:
        assert db.get(Bloque, bloque_id).activo is True


def test_asesor_ve_bloques_sin_formulario_ni_botones(client):
    crear_bloque(client, "Bloque visible")
    iniciar_sesion(client, ASESOR)
    texto = client.get("/bloques").text
    assert "Bloque visible" in texto
    assert "Crear bloque" not in texto and "/estado" not in texto


def test_asesor_ve_encuestas_de_otros_pero_sin_boton_editar(client):
    bloque_id = crear_bloque(client)
    iniciar_sesion(client, ASESOR2)
    client.post("/encuestas/nueva", data=datos_encuesta(bloque_id, nombre="Cliente De Otro"))
    client.get("/logout")
    iniciar_sesion(client, ASESOR)
    texto = client.get(f"/encuestas?bloque_id={bloque_id}").text
    assert "Cliente De Otro" in texto
    assert "/editar" not in texto


def test_varios_bloques_abiertos_a_la_vez(client):
    iniciar_sesion(client, ASESOR)
    a, b = crear_bloque(client, "Bloque A"), crear_bloque(client, "Bloque B")
    with SessionLocal() as db:
        assert db.get(Bloque, a).activo and db.get(Bloque, b).activo
    # El asesor registra en ambos
    assert client.post("/encuestas/nueva", data=datos_encuesta(a), follow_redirects=False).status_code == 303
    assert client.post("/encuestas/nueva", data=datos_encuesta(b), follow_redirects=False).status_code == 303


def test_bloque_con_fecha_fin_anterior_es_rechazado(client):
    iniciar_sesion(client, GERENTE)
    r = client.post("/bloques", data={"nombre": "Malo", "fecha_inicio": "2026-10-10", "fecha_fin": "2026-10-01"})
    assert r.status_code == 422
    assert "anterior" in r.text


def test_encuesta_valida_se_guarda(client):
    iniciar_sesion(client, ASESOR)
    bloque_id = crear_bloque(client)
    r = client.post("/encuestas/nueva", data=datos_encuesta(bloque_id), follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        e = db.scalar(select(Encuesta))
        assert e.bloque_id == bloque_id and e.consentimiento is True and e.interes_campana is True


def test_sin_consentimiento_no_se_guarda(client):
    iniciar_sesion(client, ASESOR)
    bloque_id = crear_bloque(client)
    r = client.post("/encuestas/nueva", data=datos_encuesta(bloque_id, consentimiento=None))
    assert r.status_code == 422
    assert "Ley 29733" in r.text
    assert contar_encuestas() == 0


def test_validaciones_del_servidor(client):
    iniciar_sesion(client, ASESOR)
    bloque_id = crear_bloque(client)
    casos = [
        {"telefono": "12345"},
        {"monto": "0"},
        {"plazo_meses": "100"},
        {"sector": "pescador"},
        {"anios_negocio": "-1"},
        {"credito_vigente": None},
    ]
    for cambio in casos:
        r = client.post("/encuestas/nueva", data=datos_encuesta(bloque_id, **cambio))
        assert r.status_code == 422, cambio
    assert contar_encuestas() == 0


def test_no_se_registra_en_bloque_cerrado(client):
    iniciar_sesion(client, ASESOR)
    bloque_id = crear_bloque(client)
    cerrar_bloque(bloque_id)
    r = client.post("/encuestas/nueva", data=datos_encuesta(bloque_id))
    assert r.status_code == 422
    assert contar_encuestas() == 0


def test_lista_filtrada_por_bloque(client):
    iniciar_sesion(client, ASESOR)
    a, b = crear_bloque(client, "Bloque A"), crear_bloque(client, "Bloque B")
    client.post("/encuestas/nueva", data=datos_encuesta(a, nombre="Cliente Del A"))
    client.post("/encuestas/nueva", data=datos_encuesta(b, nombre="Cliente Del B"))
    texto = client.get(f"/encuestas?bloque_id={a}").text
    assert "Cliente Del A" in texto and "Cliente Del B" not in texto


def test_asesor_edita_su_encuesta(client):
    iniciar_sesion(client, ASESOR)
    bloque_id = crear_bloque(client)
    client.post("/encuestas/nueva", data=datos_encuesta(bloque_id))
    with SessionLocal() as db:
        encuesta_id = db.scalar(select(Encuesta)).id
    r = client.post(f"/encuestas/{encuesta_id}/editar", data=datos_encuesta(bloque_id, monto="4500"),
                    follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        assert db.get(Encuesta, encuesta_id).monto == 4500


def test_otro_asesor_no_puede_editar(client):
    iniciar_sesion(client, ASESOR)
    bloque_id = crear_bloque(client)
    client.post("/encuestas/nueva", data=datos_encuesta(bloque_id))
    with SessionLocal() as db:
        encuesta_id = db.scalar(select(Encuesta)).id
    client.get("/logout")
    iniciar_sesion(client, ASESOR2)
    assert client.get(f"/encuestas/{encuesta_id}/editar").status_code == 403
    r = client.post(f"/encuestas/{encuesta_id}/editar", data=datos_encuesta(bloque_id, monto="1"))
    assert r.status_code == 403


def test_gerente_puede_editar_cualquier_encuesta(client):
    iniciar_sesion(client, ASESOR)
    bloque_id = crear_bloque(client)
    client.post("/encuestas/nueva", data=datos_encuesta(bloque_id))
    with SessionLocal() as db:
        encuesta_id = db.scalar(select(Encuesta)).id
    client.get("/logout")
    iniciar_sesion(client, GERENTE)
    r = client.post(f"/encuestas/{encuesta_id}/editar", data=datos_encuesta(bloque_id, nombre="Nombre Corregido"),
                    follow_redirects=False)
    assert r.status_code == 303
    assert "Nombre Corregido" in client.get(f"/encuestas/{encuesta_id}").text


def test_editar_encuesta_de_bloque_cerrado_sin_moverla(client):
    iniciar_sesion(client, ASESOR)
    bloque_id = crear_bloque(client)
    client.post("/encuestas/nueva", data=datos_encuesta(bloque_id))
    cerrar_bloque(bloque_id)
    with SessionLocal() as db:
        encuesta_id = db.scalar(select(Encuesta)).id
    r = client.post(f"/encuestas/{encuesta_id}/editar", data=datos_encuesta(bloque_id, zona="Ambo"),
                    follow_redirects=False)
    assert r.status_code == 303


def test_paginas_requieren_sesion(client):
    for url in ("/bloques", "/encuestas", "/encuestas/nueva"):
        r = client.get(url, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login"
