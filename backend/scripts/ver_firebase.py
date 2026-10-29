"""Muestra las últimas lecturas que llegaron a Firebase desde los sensores.

Uso (desde backend/, con el entorno activado):
    python -m scripts.ver_firebase
"""
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

HORA_PERU = timezone(timedelta(hours=-5))


def leer(ruta: str, **params) -> dict | None:
    if settings.firebase_db_secret:
        params["auth"] = settings.firebase_db_secret
    r = httpx.get(f"{settings.firebase_db_url}/{ruta}.json", params=params, timeout=15)
    if r.status_code == 401:
        raise SystemExit("Firebase rechazó la lectura: falta FIREBASE_DB_SECRET en .env (las reglas ya están cerradas)")
    r.raise_for_status()
    return r.json()


def hora(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=HORA_PERU).strftime("%d/%m/%Y %H:%M:%S")


def main():
    if not settings.firebase_db_url:
        raise SystemExit("Falta FIREBASE_DB_URL en backend/.env")
    ultimas = leer("ultima") or {}
    if not ultimas:
        print("Todavía no hay lecturas en Firebase. Inicia la simulación en Wokwi.")
        return
    for sensor, ultima in ultimas.items():
        print(f"\n== {sensor} ({ultima['sector']}) ==")
        lecturas = leer(f"lecturas/{sensor}", orderBy='"$key"', limitToLast=5) or {}
        for lec in sorted(lecturas.values(), key=lambda x: x["ts"]):
            print(f"  {hora(lec['ts'])}   {lec['temperatura']:5.1f} °C   {lec['humedad']:5.1f} %")
        total = leer(f"lecturas/{sensor}", shallow="true") or {}
        print(f"  Total de lecturas guardadas: {len(total)}")


if __name__ == "__main__":
    main()
