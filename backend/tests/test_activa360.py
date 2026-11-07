"""Pruebas de ACTIVA 360°: base (seguridad), comercial, negocios, riesgos y recuperaciones."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import (Auditoria, Campana, Cliente, CompromisoPago, ContactoProspecto, Credito, Interesado,
                        Prospecto, Reprogramacion, Solicitud, Usuario)
from app.security import cifrar_password
from app.services import comercial, ia, recuperaciones as rec, riesgos
from app.services.simulador import numero_cuotas, simular, tasa_periodica
from tests.conftest import ASESOR, ASESOR2, GERENTE, iniciar_sesion

ANALISTA = {"email": "analista@test.pe", "password": "clave-analista"}
GESTOR = {"email": "gestor@test.pe", "password": "clave-gestor"}
GESTOR2 = {"email": "gestor2@test.pe", "password": "clave-gestor2"}


@pytest.fixture(autouse=True)
def usuarios_360():
    with SessionLocal() as db:
        db.add_all([
            Usuario(nombre="Ana Analista", email=ANALISTA["email"], password_hash=cifrar_password(ANALISTA["password"]), rol="analista_riesgos"),
            Usuario(nombre="Gino Gestor", email=GESTOR["email"], password_hash=cifrar_password(GESTOR["password"]), rol="gestor_recuperaciones"),
            Usuario(nombre="Gina Gestora", email=GESTOR2["email"], password_hash=cifrar_password(GESTOR2["password"]), rol="gestor_recuperaciones"),
        ])
        db.commit()


def uid(email: str) -> int:
    with SessionLocal() as db:
        return db.scalar(select(Usuario.id).where(Usuario.email == email))


def entrar(client, cred):
    r = iniciar_sesion(client, cred)
    assert r.status_code == 303, r.text
    return client


PROSPECTO = {
    "nombre": "Rosa Quispe Mamani", "telefono": "987654321", "dni": "", "segmento": "comerciante",
    "actividad": "Venta de abarrotes", "necesidad": "Capital para comprar mercadería de campaña escolar",
    "region": "la_libertad", "ubicacion": "Trujillo", "monto_solicitado": "3000", "contacto_preferido": "whatsapp",
    "campana_id": "", "asesor_id": "", "proxima_accion": "", "consentimiento": "on",
}

CLIENTE = {
    "dni": "45678912", "nombres": "Rosa Quispe Mamani", "telefono": "987654321", "email": "", "segmento": "comerciante",
    "ocupacion": "Venta de abarrotes", "region": "la_libertad", "ubicacion": "Trujillo", "ingresos_mensuales": "4000",
    "gastos_mensuales": "1500", "antiguedad_meses": "36", "cuotas_otras_deudas": "300", "saldo_otras_deudas": "2000",
    "necesidades": "", "consentimiento": "on",
}

SOLICITUD = {
    "producto": "capital_trabajo", "monto": "5000", "plazo_meses": "12", "frecuencia": "mensual",
    "destino": "Compra de mercadería", "campana_id": "", "perfil_giro": "Abarrotes",
    "perfil_ventas_mensuales": "9000", "perfil_costo_ventas": "5500",
}


def crear_cliente(client, datos=None) -> int:
    r = client.post("/clientes/nuevo", data=datos or CLIENTE, follow_redirects=False)
    assert r.status_code == 303, r.text
    return int(r.headers["location"].rsplit("/", 1)[1])


def crear_solicitud(client, cliente_id, datos=None) -> int:
    r = client.post(f"/clientes/{cliente_id}/solicitud/nueva", data=datos or SOLICITUD, follow_redirects=False)
    assert r.status_code == 303, r.text
    return int(r.headers["location"].rsplit("/", 1)[1])


def validar_documentos(client, solicitud_id):
    with SessionLocal() as db:
        ids = [d.id for d in db.get(Solicitud, solicitud_id).documentos]
    for d in ids:
        assert client.post(f"/solicitudes/{solicitud_id}/documentos/{d}", data={"estado": "validado"}, follow_redirects=False).status_code == 303


# =====================================================================
# Fase 8 · Base 360°: roles, auditoría, intentos, CSRF
# =====================================================================

def test_bloqueo_tras_intentos_fallidos_y_auditoria(client):
    for _ in range(5):
        assert iniciar_sesion(client, {"email": ASESOR["email"], "password": "mala"}).status_code == 401
    # Aunque ahora la contraseña sea correcta, queda bloqueado durante la ventana
    r = iniciar_sesion(client, ASESOR)
    assert r.status_code == 429 and "Demasiados intentos" in r.text
    r = client.post("/api/auth/token", data={"username": ASESOR["email"], "password": ASESOR["password"]})
    assert r.status_code == 429
    with SessionLocal() as db:
        acciones = [a.accion for a in db.scalars(select(Auditoria).where(Auditoria.email == ASESOR["email"]))]
    assert acciones.count("login_fallido") == 5 and "login_bloqueado" in acciones
    # Otro usuario no se ve afectado
    assert iniciar_sesion(client, GERENTE).status_code == 303


def test_login_correcto_reinicia_el_contador(client):
    for _ in range(4):
        iniciar_sesion(client, {"email": ASESOR["email"], "password": "mala"})
    assert iniciar_sesion(client, ASESOR).status_code == 303
    client.get("/logout")
    for _ in range(4):
        iniciar_sesion(client, {"email": ASESOR["email"], "password": "mala"})
    assert iniciar_sesion(client, ASESOR).status_code == 303


def test_csrf_rechaza_formularios_de_otro_sitio(client):
    r = client.post("/login", data=ASESOR, headers={"origin": "https://sitio-malicioso.com"}, follow_redirects=False)
    assert r.status_code == 403
    r = client.post("/login", data=ASESOR, headers={"origin": "http://testserver"}, follow_redirects=False)
    assert r.status_code == 303


def test_acceso_denegado_queda_auditado(client):
    entrar(client, ASESOR)
    assert client.get("/usuarios").status_code == 403
    with SessionLocal() as db:
        a = db.scalar(select(Auditoria).where(Auditoria.accion == "acceso_denegado"))
    assert a and "/usuarios" in a.detalle and a.usuario_id == uid(ASESOR["email"])


def test_menu_lateral_segun_rol(client):
    entrar(client, ANALISTA)
    r = client.get("/panel")
    assert r.status_code == 200
    assert 'href="/riesgos"' in r.text and 'href="/prospectos"' not in r.text and 'href="/recuperaciones"' not in r.text
    assert client.get("/prospectos").status_code == 403
    client.get("/logout")
    entrar(client, GESTOR)
    r = client.get("/panel")
    assert 'href="/recuperaciones"' in r.text and 'href="/clientes"' not in r.text
    assert client.get("/clientes").status_code == 403
    assert client.get("/simulador").status_code == 200  # el simulador es para todos


def test_gerente_crea_y_desactiva_usuarios(client):
    entrar(client, GERENTE)
    r = client.post("/usuarios", data={"nombre": "Nuevo Gestor", "email": "nuevo@test.pe", "rol": "gestor_recuperaciones",
                                       "password": "corta"})
    assert r.status_code == 422 and "Mínimo 10 caracteres" in r.text
    r = client.post("/usuarios", data={"nombre": "Nuevo Gestor", "email": "Nuevo@Test.pe", "rol": "gestor_recuperaciones",
                                       "password": "segura12345"}, follow_redirects=False)
    assert r.status_code == 303
    nuevo = uid("nuevo@test.pe")
    assert client.post(f"/usuarios/{nuevo}/estado", follow_redirects=False).status_code == 303
    with SessionLocal() as db:
        assert db.get(Usuario, nuevo).activo is False
    # No puede desactivarse a sí mismo
    assert client.post(f"/usuarios/{uid(GERENTE['email'])}/estado").status_code == 409
    r = client.get("/auditoria?accion=usuario_creado")
    assert r.status_code == 200 and "Usuario creado" in r.text


# =====================================================================
# Fase 9 · Comercial
# =====================================================================

def test_prospecto_requiere_consentimiento_y_celular_valido(client):
    entrar(client, ASESOR)
    datos = PROSPECTO | {"telefono": "12345", "consentimiento": ""}
    datos.pop("consentimiento")
    r = client.post("/prospectos/nuevo", data=datos)
    assert r.status_code == 422
    assert "Ley 29733" in r.text and "Celular peruano" in r.text
    with SessionLocal() as db:
        assert db.scalar(select(Prospecto)) is None


def test_embudo_contactos_y_visibilidad(client):
    entrar(client, ASESOR)
    r = client.post("/prospectos/nuevo", data=PROSPECTO, follow_redirects=False)
    pid = int(r.headers["location"].rsplit("/", 1)[1])
    r = client.post(f"/prospectos/{pid}/contacto", data={"canal": "whatsapp", "resultado": "Le interesa, pide visita",
                                                         "estado_nuevo": "interesado", "proxima_accion": date.today().isoformat()},
                    follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        p = db.get(Prospecto, pid)
        assert p.estado == "interesado" and p.asesor_id == uid(ASESOR["email"])
        assert db.scalar(select(ContactoProspecto)).canal == "whatsapp"
        assert [x.id for x in comercial.pendientes(db, db.get(Usuario, uid(ASESOR["email"])))] == [pid]
    client.get("/logout")
    # Otro asesor no ve el prospecto asignado
    entrar(client, ASESOR2)
    assert client.get(f"/prospectos/{pid}").status_code == 403
    assert "Rosa Quispe" not in client.get("/prospectos").text
    client.get("/logout")
    # El gerente ve todo y la tasa de conversión
    entrar(client, GERENTE)
    client.post(f"/prospectos/{pid}/contacto", data={"canal": "visita", "resultado": "Firmó solicitud y fue aprobado",
                                                     "estado_nuevo": "convertido"})
    with SessionLocal() as db:
        emb = comercial.embudo(db, db.get(Usuario, uid(GERENTE["email"])))
    assert emb["conteo"]["convertido"] == 1 and emb["tasa_conversion"] == 100.0
    assert "Rosa Quispe" in client.get("/prospectos").text


def test_gerente_asigna_prospecto(client):
    entrar(client, GERENTE)
    r = client.post("/prospectos/nuevo", data=PROSPECTO, follow_redirects=False)
    pid = int(r.headers["location"].rsplit("/", 1)[1])
    with SessionLocal() as db:
        assert db.get(Prospecto, pid).asesor_id is None
    client.post(f"/prospectos/{pid}/asignar", data={"asesor_id": str(uid(ASESOR2["email"]))})
    with SessionLocal() as db:
        assert db.get(Prospecto, pid).asesor_id == uid(ASESOR2["email"])


def test_interesado_del_chatbot_pasa_al_embudo(client):
    with SessionLocal() as db:
        db.add_all([
            Interesado(nombre="Pedro Ramos", telefono="912345678", sector="taxista", consentimiento=True),
            Interesado(nombre="Sin Permiso", telefono="923456789", sector="agricola", consentimiento=False),
        ])
        db.commit()
        con, sin = [i.id for i in db.scalars(select(Interesado).order_by(Interesado.id))]
    entrar(client, ASESOR)
    r = client.post(f"/interesados/{con}/prospecto", follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        p = db.scalar(select(Prospecto).where(Prospecto.interesado_id == con))
        assert p.segmento == "transportista" and p.origen == "chatbot" and p.estado == "interesado"
    # Repetir no duplica
    client.post(f"/interesados/{con}/prospecto")
    assert client.post(f"/interesados/{sin}/prospecto").status_code == 409
    with SessionLocal() as db:
        assert len(db.scalars(select(Prospecto)).all()) == 1


def test_mensaje_comercial_no_envia_datos_personales(client, monkeypatch):
    enviados = []

    def falso(prompt, json=False, validar=None, timeout=25):
        enviados.append(prompt)
        return validar("Hola, ¿cómo está? Tenemos una opción para su negocio. ¿Coordinamos una visita?"), "modelo-prueba"

    monkeypatch.setattr(ia, "llamar_gemini", falso)
    entrar(client, ASESOR)
    datos = PROSPECTO | {"dni": "45678912", "necesidad": "Rosa necesita capital, llamar al 987654321"}
    r = client.post("/prospectos/nuevo", data=datos, follow_redirects=False)
    pid = int(r.headers["location"].rsplit("/", 1)[1])
    client.post(f"/prospectos/{pid}/mensaje", follow_redirects=False)
    r = client.get(f"/prospectos/{pid}")
    assert "Tenemos una opción para su negocio" in r.text
    prompt = enviados[0]
    for dato in ("Rosa", "Quispe", "987654321", "45678912"):
        assert dato not in prompt


def test_mensaje_comercial_con_tasa_usa_plantilla(monkeypatch):
    def con_tasa(prompt, json=False, validar=None, timeout=25):
        return validar("Hola, ¿cómo está? Le damos una tasa de 2% mensual. ¿Le interesa?"), "m"

    monkeypatch.setattr(ia, "llamar_gemini", con_tasa)
    p = Prospecto(nombre="X", telefono="900000000", segmento="comerciante", actividad="Venta", necesidad="capital",
                  region="lima", contacto_preferido="whatsapp", consentimiento=True)
    r = comercial.mensaje_comercial(p)
    assert r["fuente"] == "plantilla" and "%" not in r["texto"]


def _campana_borrador(autor_id: int) -> int:
    from app.config import cargar_tipos_campana
    from app.schemas import CampanaEntrada
    from app.services import campanas as servicio

    entrada = CampanaEntrada(
        tipo_campana=next(iter(cargar_tipos_campana())),
        temporada="lluvias", publico_objetivo="Comerciantes de mercado", necesidad="Capital para la temporada",
        plazo_meses=6, zona="Trujillo", tipo_cliente="ambos", periodo_gracia_meses=0, fecha_inicio=date.today(),
        duracion_semanas=4, presupuesto_difusion=Decimal("100"), meta_creditos=10, segmento="comerciante", region="la_libertad",
    )
    with SessionLocal() as db:
        c = Campana(nombre="Campaña prueba", contenido=servicio.contenido_plantilla(entrada), generado_con="plantilla",
                    creado_por=autor_id)
        servicio.aplicar_entrada(c, entrada)
        db.add(c)
        db.commit()
        return c.id


def test_flujo_campana_borrador_pendiente_publicada(client):
    cid = _campana_borrador(uid(ASESOR["email"]))
    entrar(client, ASESOR2)
    assert client.post(f"/campanas/{cid}/enviar").status_code == 403  # no es el autor
    client.get("/logout")
    entrar(client, ASESOR)
    assert client.post(f"/campanas/{cid}/publicar").status_code == 403  # el asesor no publica
    assert client.post(f"/campanas/{cid}/enviar", follow_redirects=False).status_code == 303
    with SessionLocal() as db:
        assert db.get(Campana, cid).estado == "pendiente"
    r = client.get(f"/campanas/{cid}")
    assert "Pendiente de aprobación" in r.text and "Comerciante" in r.text
    client.get("/logout")
    entrar(client, GERENTE)
    assert "Campaña prueba" in client.get("/campanas?estado=pendiente").text
    client.post(f"/campanas/{cid}/publicar")
    with SessionLocal() as db:
        assert db.get(Campana, cid).estado == "publicada"


def test_campana_rechaza_segmento_invalido():
    from pydantic import ValidationError

    from app.schemas import CampanaEntrada

    with pytest.raises(ValidationError):
        CampanaEntrada(tipo_campana="x", temporada="lluvias", publico_objetivo="abcde", necesidad="abcde", plazo_meses=6,
                       zona="zz", tipo_cliente="ambos", periodo_gracia_meses=0, fecha_inicio=date.today(),
                       duracion_semanas=4, presupuesto_difusion=0, meta_creditos=1, segmento="inventado")


# =====================================================================
# Fase 10 · Negocios: simulador, expediente y solicitud
# =====================================================================

def test_simulador_metodo_frances():
    # TEA 12.6825 % ≈ 1 % mensual; 10 000 a 12 meses → cuota 888.49 (valor de tabla conocido)
    r = simular(10000, 12.682503, 12, "mensual", date(2026, 1, 15))
    assert r["cuota"] == Decimal("888.49")
    assert r["cronograma"][-1]["saldo"] == Decimal("0.00")
    assert sum(c["capital"] for c in r["cronograma"]) == Decimal("10000.00")
    assert r["cronograma"][0]["fecha"] == date(2026, 2, 15)
    assert r["total_pagar"] == sum(c["cuota"] for c in r["cronograma"])


def test_simulador_tasa_cero_y_frecuencias():
    r = simular(1200, 0, 12, "mensual")
    assert r["cuota"] == Decimal("100.00") and r["total_intereses"] == Decimal("0.00")
    assert numero_cuotas(6, "quincenal") == 12 and numero_cuotas(12, "semanal") == 52
    assert abs(tasa_periodica(12.682503, "mensual") - 0.01) < 1e-6
    with pytest.raises(ValueError):
        simular(-5, 10, 12, "mensual")


def test_simulador_web_y_api(client):
    entrar(client, ASESOR)
    r = client.get("/simulador?monto=5000&plazo_meses=12&frecuencia=mensual&producto=capital_trabajo")
    assert r.status_code == 200 and "Cronograma" in r.text and "45.0" in r.text and "demostración" in r.text
    r = client.get("/api/simulador?monto=1200&tea=0&plazo_meses=12")
    assert r.status_code == 200 and r.json()["cuota"] == "100.00" and len(r.json()["cronograma"]) == 12
    assert client.get("/api/simulador?monto=-1&tea=0&plazo_meses=12").status_code == 422


def test_expediente_dni_unico_y_restringido(client):
    entrar(client, ASESOR)
    cid = crear_cliente(client)
    r = client.post("/clientes/nuevo", data=CLIENTE | {"telefono": "911111111"})
    assert r.status_code == 422 and "Ya existe un expediente" in r.text
    r = client.post("/clientes/nuevo", data=CLIENTE | {"dni": "123"})
    assert r.status_code == 422 and "8 dígitos" in r.text
    client.get("/logout")
    entrar(client, ASESOR2)
    assert client.get(f"/clientes/{cid}").status_code == 403
    assert "Rosa Quispe" not in client.get("/clientes").text
    client.get("/logout")
    entrar(client, ANALISTA)  # sin solicitudes enviadas, el analista no lo ve
    assert client.get(f"/clientes/{cid}").status_code == 403


def test_solicitud_formulario_dinamico_y_condiciones(client):
    entrar(client, ASESOR)
    cid = crear_cliente(client)
    r = client.get(f"/clientes/{cid}/solicitud/nueva")
    assert "Ventas mensuales" in r.text and "Sueldo neto" not in r.text  # formulario de comerciante
    datos = SOLICITUD | {"perfil_ventas_mensuales": "", "monto": "999999"}
    r = client.post(f"/clientes/{cid}/solicitud/nueva", data=datos)
    assert r.status_code == 422
    assert "Este campo es obligatorio" in r.text and "El monto debe estar entre" in r.text
    r = client.post(f"/clientes/{cid}/solicitud/nueva", data=SOLICITUD | {"producto": "personal"})
    assert r.status_code == 422 and "no está disponible para el tipo de cliente" in r.text
    sid = crear_solicitud(client, cid)
    with SessionLocal() as db:
        s = db.get(Solicitud, sid)
        assert s.estado == "borrador" and s.datos_perfil["ventas_mensuales"] == 9000
        assert {d.tipo for d in s.documentos} == {"dni", "recibo_servicio", "sustento_ventas"}


def test_flujo_completo_de_solicitud_con_permisos(client):
    entrar(client, ASESOR)
    r = client.post("/prospectos/nuevo", data=PROSPECTO, follow_redirects=False)
    pid = int(r.headers["location"].rsplit("/", 1)[1])
    cid = crear_cliente(client, CLIENTE | {"prospecto_id": str(pid)})
    sid = crear_solicitud(client, cid)
    with SessionLocal() as db:
        assert db.get(Prospecto, pid).estado == "solicitud"
    validar_documentos(client, sid)
    assert client.post(f"/solicitudes/{sid}/accion", data={"accion": "aprobar", "comentario": "x"}).status_code == 403
    client.post(f"/solicitudes/{sid}/accion", data={"accion": "enviar"})
    with SessionLocal() as db:
        s = db.get(Solicitud, sid)
        assert s.estado == "enviada" and len(s.evaluaciones) == 1  # foto de la evaluación al enviar
        assert db.get(Prospecto, pid).estado == "evaluacion"
    client.get("/logout")

    entrar(client, ANALISTA)
    assert client.get(f"/clientes/{cid}").status_code == 200  # ahora sí: tiene una solicitud enviada
    client.post(f"/solicitudes/{sid}/accion", data={"accion": "tomar"})
    # "evaluar" exige comentario
    client.post(f"/solicitudes/{sid}/accion", data={"accion": "evaluar", "comentario": ""})
    with SessionLocal() as db:
        assert db.get(Solicitud, sid).estado == "en_evaluacion"
    client.post(f"/solicitudes/{sid}/accion", data={"accion": "evaluar", "comentario": "Capacidad suficiente, documentos completos"})
    assert client.post(f"/solicitudes/{sid}/accion", data={"accion": "aprobar", "comentario": "ok"}).status_code == 403
    client.get("/logout")

    entrar(client, GERENTE)
    client.post(f"/solicitudes/{sid}/accion", data={"accion": "aprobar", "comentario": "Aprobada en comité"})
    with SessionLocal() as db:
        s = db.get(Solicitud, sid)
        assert s.estado == "aprobada"
        assert [m.estado_nuevo for m in reversed(s.movimientos)] == ["borrador", "enviada", "en_evaluacion", "evaluada", "aprobada"]
        assert s.evaluaciones[0].opinion == "Capacidad suficiente, documentos completos"
        assert db.get(Prospecto, pid).estado == "convertido"


def test_analista_no_ve_borradores(client):
    entrar(client, ASESOR)
    cid = crear_cliente(client)
    sid = crear_solicitud(client, cid)
    client.get("/logout")
    entrar(client, ANALISTA)
    assert client.get(f"/solicitudes/{sid}").status_code == 403
    assert f"#{sid}" not in client.get("/solicitudes").text


def test_observada_vuelve_al_asesor(client):
    entrar(client, ASESOR)
    cid = crear_cliente(client)
    sid = crear_solicitud(client, cid)
    client.post(f"/solicitudes/{sid}/accion", data={"accion": "enviar"})
    client.get("/logout")
    entrar(client, ANALISTA)
    client.post(f"/solicitudes/{sid}/accion", data={"accion": "observar", "comentario": "Falta sustento de ventas"})
    client.get("/logout")
    entrar(client, ASESOR)
    assert client.get(f"/solicitudes/{sid}/editar").status_code == 200
    r = client.post(f"/solicitudes/{sid}/editar", data=SOLICITUD | {"monto": "4000"}, follow_redirects=False)
    assert r.status_code == 303
    client.post(f"/solicitudes/{sid}/accion", data={"accion": "enviar"})
    with SessionLocal() as db:
        s = db.get(Solicitud, sid)
        assert s.estado == "enviada" and s.monto == Decimal("4000.00")


def test_productos_marcados_como_demostracion(client):
    entrar(client, GESTOR)
    r = client.get("/productos")
    assert r.status_code == 200 and "No es una oferta ni una cotización de Caja Trujillo" in r.text
    assert "Ahorro" not in r.text.split("El ahorro")[0]  # no se ofrece ahorro


# =====================================================================
# Fase 11 · Riesgos
# =====================================================================

def _evaluar(client, cliente=None, solicitud=None, validar=True) -> dict:
    entrar(client, ASESOR)
    cid = crear_cliente(client, cliente)
    sid = crear_solicitud(client, cid, solicitud)
    if validar:
        validar_documentos(client, sid)
    client.post(f"/solicitudes/{sid}/evaluar")
    with SessionLocal() as db:
        s = db.get(Solicitud, sid)
        return {"sid": sid, "estado": s.estado, "ev": s.evaluaciones[0].semaforo,
                "codigos": [a["codigo"] for a in s.evaluaciones[0].alertas], "ind": s.evaluaciones[0].indicadores}


def test_semaforo_verde_no_decide(client):
    r = _evaluar(client)
    assert r["ev"] == "verde", r["codigos"]
    assert r["estado"] == "borrador"  # evaluar nunca cambia el estado ni aprueba
    assert r["ind"]["ingreso_neto"] == 2500 and r["ind"]["capacidad_disponible"] == 2200
    assert r["ind"]["completitud"] == 100


def test_semaforo_amarillo_por_documentos(client):
    r = _evaluar(client, validar=False)
    assert r["ev"] == "amarillo" and "completitud" in r["codigos"]


def test_semaforo_rojo_sin_capacidad(client):
    r = _evaluar(client, CLIENTE | {"gastos_mensuales": "3800", "cuotas_otras_deudas": "500"})
    assert r["ev"] == "rojo" and "sin_capacidad" in r["codigos"]


def test_inconsistencias_ingresos_y_duplicados(client):
    entrar(client, ASESOR)
    crear_cliente(client, CLIENTE | {"dni": "11111111"})  # mismo teléfono que el siguiente
    client.get("/logout")
    r = _evaluar(client, solicitud=SOLICITUD | {"perfil_ventas_mensuales": "2000", "perfil_costo_ventas": "1500"})
    assert "ingresos_perfil" in r["codigos"] and "duplicado_telefono" in r["codigos"]


def test_bandeja_de_riesgos_y_seguridad(client):
    iniciar_sesion(client, {"email": ASESOR["email"], "password": "mala"})
    entrar(client, ASESOR)
    cid = crear_cliente(client)
    sid = crear_solicitud(client, cid)
    client.post(f"/solicitudes/{sid}/accion", data={"accion": "enviar"})
    client.get("/logout")
    entrar(client, ANALISTA)
    r = client.get("/riesgos")
    assert r.status_code == 200 and f"#{sid}" in r.text and "2026-11-v1" in r.text
    r = client.get("/riesgos/seguridad")
    assert "Intento fallido" in r.text and ASESOR["email"] in r.text


# =====================================================================
# Fase 12 · Recuperaciones
# =====================================================================

def _credito(gestor_email=GESTOR["email"], desembolso=None, consentimiento=True) -> int:
    # Los id se leen antes: en las pruebas todas las sesiones comparten una sola conexión SQLite
    asesor, gestor, gerente = uid(ASESOR["email"]), uid(gestor_email), uid(GERENTE["email"])
    with SessionLocal() as db:
        c = Cliente(dni="22223333", nombres="Luis Torres", telefono="955555555", segmento="transportista", ocupacion="Mototaxi",
                    region="piura", ingresos_mensuales=2500, gastos_mensuales=1000, antiguedad_meses=24,
                    cuotas_otras_deudas=0, saldo_otras_deudas=0, consentimiento=consentimiento,
                    asesor_id=asesor, creado_por=asesor)
        db.add(c)
        db.flush()
        cr = Credito(cliente_id=c.id, producto="independientes", monto=Decimal("1200"), tea=Decimal("0"), plazo_meses=6,
                     frecuencia="mensual", fecha_desembolso=desembolso or date.today() - timedelta(days=75),
                     gestor_id=gestor, registrado_por=gerente)
        rec.generar_cuotas(cr)
        db.add(cr)
        db.commit()
        return cr.id


def test_cronograma_pagos_y_atraso():
    cid = _credito()
    hoy = date.today()
    with SessionLocal() as db:
        cr = db.get(Credito, cid)
        assert len(cr.cuotas) == 6 and all(c.monto == Decimal("200.00") for c in cr.cuotas)
        assert rec.dias_atraso(cr, hoy) > 0  # dos cuotas ya vencieron sin pago
        rec.aplicar_pago(cr, Decimal("300"), hoy)
        assert cr.cuotas[0].pagado == Decimal("200.00") and cr.cuotas[0].fecha_pago == hoy
        assert cr.cuotas[1].pagado == Decimal("100.00") and rec.estado_cuota(cr.cuotas[1], hoy) == "vencida"
        with pytest.raises(ValueError):
            rec.aplicar_pago(cr, Decimal("5000"), hoy)
        rec.aplicar_pago(cr, rec.saldo_pendiente(cr), hoy)
        assert cr.estado == "cancelado" and rec.dias_atraso(cr, hoy) == 0


def test_alertas_y_compromisos():
    cid = _credito(desembolso=date.today() - timedelta(days=28))
    with SessionLocal() as db:
        cr = db.get(Credito, cid)
        gestor = db.get(Usuario, uid(GESTOR["email"]))
        tipos = [a["tipo"] for a in rec.alertas(db, gestor)]
        assert "proximo_vencimiento" in tipos  # la primera cuota vence en ~3 días
        db.add(CompromisoPago(credito_id=cid, fecha=date.today() - timedelta(days=1), monto=Decimal("200"),
                              creado_por=gestor.id))
        db.add(Reprogramacion(credito_id=cid, tipo="reprogramacion", motivo="Vehículo en taller", solicitada_por=gestor.id))
        db.commit()
        assert rec.actualizar_compromisos(db) == 1
        tipos = [a["tipo"] for a in rec.alertas(db, gestor)]
        assert "compromiso_incumplido" in tipos and "reprogramacion_pendiente" in tipos
        # Otro gestor no ve alertas de créditos ajenos
        assert rec.alertas(db, db.get(Usuario, uid(GESTOR2["email"]))) == []
        texto = rec.mensaje_sugerido("proximo", cr, date.today(), Decimal("200"))
        assert texto.startswith("Hola Luis") and "Torres" not in texto
        assert rec.enlace_whatsapp(cr, texto).startswith("https://wa.me/51955555555")


def test_sin_consentimiento_no_hay_whatsapp():
    cid = _credito(consentimiento=False)
    with SessionLocal() as db:
        assert rec.enlace_whatsapp(db.get(Credito, cid), "hola") is None


def test_gestion_web_y_permisos(client):
    cid = _credito()
    entrar(client, GESTOR2)
    assert client.get(f"/recuperaciones/creditos/{cid}").status_code == 403
    client.get("/logout")
    entrar(client, GESTOR)
    r = client.get("/recuperaciones")
    assert r.status_code == 200 and "Luis Torres" in r.text
    assert client.get("/recuperaciones/creditos/nuevo").status_code == 403  # solo el gerente registra créditos
    hoy = date.today().isoformat()
    assert client.post(f"/recuperaciones/creditos/{cid}/pago", data={"monto": "200", "fecha": hoy},
                       follow_redirects=False).status_code == 303
    client.post(f"/recuperaciones/creditos/{cid}/gestion", data={"canal": "llamada", "resultado": "compromiso", "observacion": "Paga el viernes"})
    client.post(f"/recuperaciones/creditos/{cid}/compromiso", data={"fecha": hoy, "monto": "200"})
    client.post(f"/recuperaciones/creditos/{cid}/reprogramacion", data={"tipo": "reprogramacion", "motivo": "Enfermedad en la familia"})
    assert client.get("/recuperaciones/alertas").status_code == 200
    with SessionLocal() as db:
        cr = db.get(Credito, cid)
        assert len(cr.pagos) == 1 and len(cr.gestiones) == 1 and len(cr.compromisos) == 1
        rp_id = cr.reprogramaciones[0].id
    assert client.post(f"/recuperaciones/reprogramaciones/{rp_id}/revisar", data={"decision": "aprobada", "comentario": "ok ok"}).status_code == 403
    client.get("/logout")
    entrar(client, GERENTE)
    client.post(f"/recuperaciones/reprogramaciones/{rp_id}/revisar", data={"decision": "aprobada", "comentario": "Se aprueba un mes de gracia"})
    with SessionLocal() as db:
        assert db.get(Reprogramacion, rp_id).estado == "aprobada"


def test_gerente_registra_credito_desde_solicitud_aprobada(client):
    entrar(client, ASESOR)
    cid = crear_cliente(client)
    sid = crear_solicitud(client, cid)
    client.get("/logout")
    with SessionLocal() as db:
        db.get(Solicitud, sid).estado = "aprobada"
        db.commit()
    entrar(client, GERENTE)
    r = client.get(f"/recuperaciones/creditos/nuevo?solicitud_id={sid}")
    assert r.status_code == 200 and 'value="5000.00"' in r.text
    datos = {"cliente_id": str(cid), "solicitud_id": str(sid), "producto": "capital_trabajo", "monto": "5000", "tea": "45",
             "plazo_meses": "12", "frecuencia": "mensual", "fecha_desembolso": date.today().isoformat(),
             "gestor_id": str(uid(GESTOR["email"]))}
    r = client.post("/recuperaciones/creditos/nuevo", data=datos | {"fecha_desembolso": "2999-01-01"})
    assert r.status_code == 422 and "no puede ser futura" in r.text
    assert client.post("/recuperaciones/creditos/nuevo", data=datos, follow_redirects=False).status_code == 303
    r = client.post("/recuperaciones/creditos/nuevo", data=datos)
    assert r.status_code == 422 and "ya tiene un crédito" in r.text
    with SessionLocal() as db:
        cr = db.scalar(select(Credito))
        assert len(cr.cuotas) == 12 and cr.gestor_id == uid(GESTOR["email"])


# =====================================================================
# Panel por rol
# =====================================================================

@pytest.mark.parametrize("cred,texto", [(ASESOR, "Comercial"), (GERENTE, "Recuperaciones"), (ANALISTA, "Riesgos"),
                                        (GESTOR, "Recuperaciones")])
def test_panel_por_rol(client, cred, texto):
    _credito()
    entrar(client, cred)
    r = client.get("/panel")
    assert r.status_code == 200 and texto in r.text


# =====================================================================
# Fase 13 · Datos de demostración y respaldo
# =====================================================================

def test_datos_demo_se_crean_y_se_borran(client, capsys):
    from scripts import seed_360

    with SessionLocal() as db:
        seed_360.crear(db)
        seed_360.crear(db)  # no duplica
    with SessionLocal() as db:
        assert len(db.scalars(select(Cliente)).all()) == 6
        assert len(db.scalars(select(Credito)).all()) == 4
        estados = {s.estado for s in db.scalars(select(Solicitud))}
        assert {"borrador", "enviada", "en_evaluacion", "observada", "evaluada", "aprobada"} <= estados
    # Todas las páginas principales se ven con datos, para cada rol
    for cred in (GERENTE, {"email": "analista@activa.pe", "password": "Analista2026!"},
                 {"email": "gestor@activa.pe", "password": "Gestor2026!"}):
        entrar(client, cred)
        for ruta in ("/panel", "/simulador", "/productos"):
            assert client.get(ruta).status_code == 200, (cred, ruta)
        client.get("/logout")
    entrar(client, GERENTE)
    for ruta in ("/prospectos", "/clientes", "/solicitudes", "/riesgos", "/riesgos/seguridad", "/recuperaciones",
                 "/recuperaciones/alertas", "/usuarios", "/auditoria", "/campanas", "/interesados"):
        assert client.get(ruta).status_code == 200, ruta
    with SessionLocal() as db:
        ids = [s.id for s in db.scalars(select(Solicitud))]
        creditos = [c.id for c in db.scalars(select(Credito))]
    for i in ids:
        assert client.get(f"/solicitudes/{i}").status_code == 200
    for i in creditos:
        assert client.get(f"/recuperaciones/creditos/{i}").status_code == 200
    with SessionLocal() as db:
        seed_360.borrar(db)
        assert db.scalars(select(Cliente)).all() == [] and db.scalars(select(Prospecto)).all() == []


def test_respaldo_exporta_todas_las_tablas(tmp_path):
    import json

    from scripts.respaldo import respaldar

    _credito()
    archivo = respaldar(tmp_path)
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    assert {"usuarios", "clientes", "creditos", "cuotas", "auditoria"} <= set(datos["tablas"])
    assert len(datos["tablas"]["cuotas"]) == 6


def test_roles_caben_en_columna_rol():
    # SQLite no controla el largo de VARCHAR, pero PostgreSQL (Supabase) sí
    from app.models import ROLES, Usuario
    largo = Usuario.__table__.c.rol.type.length
    assert all(len(r) <= largo for r in ROLES)
