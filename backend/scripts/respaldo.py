"""Copia de seguridad de la base de datos (Supabase) en un archivo JSON, sin instalar pg_dump.

Exporta TODAS las tablas que existen en la base (aunque el código sea más nuevo o más antiguo).
Ejecutar SIEMPRE antes de `alembic upgrade head`.

Uso (desde backend/, con el entorno activado):
    python -m scripts.respaldo                 # crea respaldos/respaldo_AAAAMMDD_HHMMSS.json
    python -m scripts.respaldo --carpeta D:\\copias

El archivo contiene datos personales: queda en backend/respaldos/ (ignorada por git). No lo compartas.
"""
import argparse
import base64
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import MetaData, select

from app.config import BASE_DIR
from app.db import engine


def _a_json(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, bytes):
        return base64.b64encode(valor).decode()
    return valor


def respaldar(carpeta: Path) -> Path:
    meta = MetaData()
    meta.reflect(bind=engine)
    datos = {"creado_en": datetime.now().isoformat(timespec="seconds"), "tablas": {}}
    with engine.connect() as con:
        for nombre, tabla in meta.tables.items():
            filas = [{k: _a_json(v) for k, v in fila._mapping.items()} for fila in con.execute(select(tabla))]
            datos["tablas"][nombre] = filas
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / f"respaldo_{datetime.now():%Y%m%d_%H%M%S}.json"
    archivo.write_text(json.dumps(datos, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return archivo


def main():
    parser = argparse.ArgumentParser(description="Respaldo de la base de datos en JSON")
    parser.add_argument("--carpeta", default=str(BASE_DIR / "respaldos"))
    args = parser.parse_args()
    archivo = respaldar(Path(args.carpeta))
    resumen = json.loads(archivo.read_text(encoding="utf-8"))["tablas"]
    print(f"Respaldo creado: {archivo}")
    for tabla, filas in sorted(resumen.items()):
        print(f"  {tabla:<24} {len(filas):>6} filas")


if __name__ == "__main__":
    main()
