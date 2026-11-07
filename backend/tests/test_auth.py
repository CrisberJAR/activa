from app.config import cargar_umbrales, settings
from tests.conftest import ASESOR, GERENTE, iniciar_sesion


def test_asesor_inicia_sesion_y_ve_su_panel(client):
    r = iniciar_sesion(client, ASESOR)
    assert r.status_code == 303
    assert r.headers["location"] == "/panel"
    r = client.get("/panel")
    assert r.status_code == 200
    assert "Panel de asesor de negocios" in r.text
    assert 'href="/usuarios"' not in r.text  # Administración solo para el gerente
    assert 'href="/recuperaciones"' not in r.text
    # Ruta antigua: redirige al panel
    assert client.get("/asesor", follow_redirects=False).headers["location"] == "/panel"


def test_gerente_inicia_sesion_y_ve_su_panel(client):
    r = iniciar_sesion(client, GERENTE)
    assert r.headers["location"] == "/panel"
    r = client.get("/panel")
    assert r.status_code == 200
    for modulo in ("Comercial", "Negocios", "Riesgos", "Recuperaciones", "Administración"):
        assert modulo in r.text


def test_contrasena_incorrecta(client):
    r = iniciar_sesion(client, {"email": ASESOR["email"], "password": "otra"})
    assert r.status_code == 401
    assert "incorrectos" in r.text


def test_asesor_no_puede_entrar_al_menu_del_gerente(client):
    iniciar_sesion(client, ASESOR)
    r = client.get("/gerente")
    assert r.status_code == 403


def test_sin_sesion_redirige_al_login(client):
    r = client.get("/asesor", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_logout_cierra_la_sesion(client):
    iniciar_sesion(client, ASESOR)
    client.get("/logout")
    r = client.get("/asesor", follow_redirects=False)
    assert r.status_code == 303


def test_token_para_app_movil(client):
    r = client.post("/api/auth/token", data={"username": GERENTE["email"], "password": GERENTE["password"]})
    assert r.status_code == 200
    token = r.json()["access_token"]
    r = client.get("/api/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert r.json()["rol"] == "gerente"


def test_token_invalido(client):
    r = client.get("/api/auth/yo", headers={"Authorization": "Bearer basura"})
    assert r.status_code == 401


def test_salud(client):
    assert client.get("/api/salud").json()["base_de_datos"] == "conectada"


def test_salud_no_muestra_detalles_de_conexion(client):
    from app.db import get_db
    from app.main import app

    class SinConexion:
        def execute(self, *_):
            raise RuntimeError("postgresql://usuario:secreto@servidor")

    app.dependency_overrides[get_db] = lambda: SinConexion()
    try:
        r = client.get("/api/salud")
    finally:
        app.dependency_overrides.pop(get_db)
    assert r.status_code == 503
    assert "secreto" not in r.text


def test_umbrales_vienen_del_archivo_de_configuracion():
    u = cargar_umbrales()
    assert u["estacion"]["lluvias_humedad_min"] == 75
    assert u["cambios"]["temperatura_grados"] == 2.5


def test_url_de_supabase_se_normaliza():
    v = settings.normalizar_url("postgresql://u:p@aws-0-x.pooler.supabase.com:5432/postgres")
    assert v.startswith("postgresql+psycopg://")
    assert v.endswith("sslmode=require")
