"""Crea un usuario asesor y un usuario gerente de prueba.

Uso (desde la carpeta backend/, con el entorno activado):
    python -m scripts.seed_usuarios
"""
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Usuario
from app.security import cifrar_password

USUARIOS = [
    {"nombre": "Ana Asesora", "email": "asesor@activa.pe", "password": "Asesor2026!", "rol": "asesor"},
    {"nombre": "Gustavo Gerente", "email": "gerente@activa.pe", "password": "Gerente2026!", "rol": "gerente"},
]


def main():
    with SessionLocal() as db:
        for datos in USUARIOS:
            if db.scalar(select(Usuario).where(Usuario.email == datos["email"])):
                print(f"Ya existe: {datos['email']}")
                continue
            db.add(Usuario(
                nombre=datos["nombre"],
                email=datos["email"],
                password_hash=cifrar_password(datos["password"]),
                rol=datos["rol"],
            ))
            print(f"Creado: {datos['email']} / {datos['password']} ({datos['rol']})")
        db.commit()


if __name__ == "__main__":
    main()
