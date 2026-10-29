from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

if settings.database_url.startswith("sqlite"):
    # Solo para pruebas automáticas (base en memoria)
    engine = create_engine(
        settings.database_url, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
else:
    # Supabase: pool_pre_ping reconecta si Supabase cerró la conexión
    engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Entrega una sesión de base de datos por petición y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
