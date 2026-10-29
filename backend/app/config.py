from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Carpeta backend/
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configuración leída del archivo backend/.env (o de variables de entorno)."""

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    secret_key: str
    jwt_minutos: int = 60 * 24 * 7  # duración del token de la app móvil

    # Firebase Realtime Database (lecturas de los sensores IoT)
    firebase_db_url: str | None = None
    firebase_db_secret: str | None = None  # solo para leer cuando las reglas están cerradas

    scheduler_activo: bool = True  # tarea automática de consolidación (se apaga en las pruebas)

    # Google Gemini (IA generativa). Sin clave, el sistema usa textos automáticos de respaldo
    gemini_api_key: str | None = None
    gemini_modelo: str = "gemini-3.1-flash-lite"
    # Se prueban en orden si el principal está saturado (503), sin cuota (429) o tarda demasiado
    gemini_modelos_respaldo: str = "gemini-3.5-flash-lite,gemini-3.5-flash"

    @property
    def gemini_modelos(self) -> list[str]:
        respaldo = [m.strip() for m in self.gemini_modelos_respaldo.split(",") if m.strip()]
        return [self.gemini_modelo] + [m for m in respaldo if m != self.gemini_modelo]

    @field_validator("database_url")
    @classmethod
    def normalizar_url(cls, v: str) -> str:
        # Supabase entrega "postgresql://..."; SQLAlchemy necesita saber que el driver es psycopg
        for prefijo in ("postgres://", "postgresql://"):
            if v.startswith(prefijo):
                v = "postgresql+psycopg://" + v[len(prefijo):]
        # Supabase exige conexión cifrada
        if "supabase" in v and "sslmode" not in v:
            v += ("&" if "?" in v else "?") + "sslmode=require"
        return v


settings = Settings()

HORA_PERU = timezone(timedelta(hours=-5))  # Perú no tiene horario de verano


def hoy_peru() -> date:
    return datetime.now(HORA_PERU).date()


def cargar_umbrales() -> dict:
    """Lee los umbrales del análisis estacional desde config/umbrales.yaml."""
    with open(BASE_DIR / "config" / "umbrales.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cargar_necesidades() -> dict:
    """Lee las categorías de necesidades desde config/necesidades.yaml."""
    with open(BASE_DIR / "config" / "necesidades.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)
