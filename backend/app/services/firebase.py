"""Lectura de Firebase Realtime Database por REST (solo desde el backend, con la clave secreta)."""
import httpx

from app.config import settings


class ErrorFirebase(Exception):
    pass


def _leer(ruta: str, **params) -> httpx.Response:
    if not settings.firebase_db_url:
        raise ErrorFirebase("Falta FIREBASE_DB_URL en backend/.env")
    if settings.firebase_db_secret:
        params["auth"] = settings.firebase_db_secret
    try:
        r = httpx.get(f"{settings.firebase_db_url}/{ruta}.json", params=params, timeout=20)
    except httpx.HTTPError as e:
        raise ErrorFirebase(f"No se pudo conectar con Firebase: {e}") from e
    if r.status_code == 401:
        raise ErrorFirebase("Firebase rechazó la lectura: revisa FIREBASE_DB_SECRET en .env")
    return r


def _json(r: httpx.Response) -> dict:
    if r.status_code != 200:
        raise ErrorFirebase(f"Firebase respondió {r.status_code}: {r.text[:200]}")
    return r.json() or {}


def leer_ultimas() -> dict[str, dict]:
    """Última lectura de cada sensor: {sensor_id: {temperatura, humedad, sector, ts}}."""
    return _json(_leer("ultima"))


def leer_lecturas(sensor_id: str, desde_ms: int) -> list[dict]:
    """Lecturas de un sensor desde una hora dada (milisegundos desde 1970)."""
    r = _leer(f"lecturas/{sensor_id}", orderBy='"ts"', startAt=desde_ms)
    if r.status_code == 400:
        # Falta ".indexOn" en las reglas: se lee todo y se filtra aquí
        datos = _json(_leer(f"lecturas/{sensor_id}"))
        return [lec for lec in datos.values() if lec.get("ts", 0) >= desde_ms]
    return list(_json(r).values())
