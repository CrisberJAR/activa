import pytest

from app.db import SessionLocal
from app.security import autenticar
from scripts.cambiar_password import cambiar
from tests.conftest import ASESOR


def test_cambia_la_password_y_la_anterior_deja_de_servir(client):
    with SessionLocal() as db:
        cambiar(db, ASESOR["email"], "nueva-clave-segura")
        assert autenticar(db, ASESOR["email"], "nueva-clave-segura") is not None
        assert autenticar(db, ASESOR["email"], ASESOR["password"]) is None


@pytest.mark.parametrize("email, password", [
    ("nadie@test.pe", "nueva-clave-segura"),
    (ASESOR["email"], "corta"),
])
def test_rechaza_usuario_inexistente_o_password_corta(client, email, password):
    with SessionLocal() as db:
        with pytest.raises(ValueError):
            cambiar(db, email, password)
        assert autenticar(db, ASESOR["email"], ASESOR["password"]) is not None
