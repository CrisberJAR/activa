"""Cambia la contraseña de un usuario sin mostrarla ni guardarla en el historial.

Uso (desde backend/, con el entorno activado):
    python -m scripts.cambiar_password asesor@activa.pe
"""
import argparse
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Usuario
from app.security import cifrar_password

MINIMO = 10


def cambiar(db: Session, email: str, password: str) -> None:
    if len(password) < MINIMO:
        raise ValueError(f"La contraseña debe tener al menos {MINIMO} caracteres")
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is None:
        raise ValueError(f"No existe el usuario {email}")
    usuario.password_hash = cifrar_password(password)
    db.commit()


def main():
    parser = argparse.ArgumentParser(description="Cambia la contraseña de un usuario")
    parser.add_argument("email")
    args = parser.parse_args()

    password = getpass("Nueva contraseña: ")
    if password != getpass("Repítela: "):
        raise SystemExit("Las contraseñas no coinciden; no se cambió nada")
    try:
        with SessionLocal() as db:
            cambiar(db, args.email, password)
    except ValueError as e:
        raise SystemExit(str(e))
    print(f"Contraseña actualizada: {args.email}")


if __name__ == "__main__":
    main()
