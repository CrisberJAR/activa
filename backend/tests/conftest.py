import os

# Las pruebas usan SQLite en memoria: no tocan Supabase
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "clave-solo-para-pruebas-automaticas-1234"
os.environ["SCHEDULER_ACTIVO"] = "false"
os.environ["FIREBASE_DB_URL"] = "https://firebase-de-prueba.invalid"  # nunca se llama: se simula en las pruebas
os.environ["GEMINI_API_KEY"] = ""  # sin clave: las pruebas nunca llaman a Gemini (se simula cuando hace falta)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Usuario  # noqa: E402
from app.security import cifrar_password  # noqa: E402

ASESOR = {"email": "asesor@test.pe", "password": "clave-asesor"}
GERENTE = {"email": "gerente@test.pe", "password": "clave-gerente"}
ASESOR2 = {"email": "asesor2@test.pe", "password": "clave-asesor2"}


@pytest.fixture(autouse=True)
def base_limpia():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add_all([
            Usuario(nombre="Asesor", email=ASESOR["email"], password_hash=cifrar_password(ASESOR["password"]), rol="asesor"),
            Usuario(nombre="Gerente", email=GERENTE["email"], password_hash=cifrar_password(GERENTE["password"]), rol="gerente"),
            Usuario(nombre="Asesor 2", email=ASESOR2["email"], password_hash=cifrar_password(ASESOR2["password"]), rol="asesor"),
        ])
        db.commit()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    return TestClient(app)


def iniciar_sesion(client, credenciales):
    return client.post("/login", data=credenciales, follow_redirects=False)
