"""Verifica la clave de Gemini: lista los modelos Flash disponibles y hace una consulta corta.

Uso (desde backend/, con el entorno activado):
    python -m scripts.probar_gemini
"""
import time

import httpx

from app.config import settings
from app.services import ia


def main():
    if not settings.gemini_api_key:
        print("Falta GEMINI_API_KEY en backend/.env (sácala gratis en https://aistudio.google.com)")
        return
    r = httpx.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        headers={"x-goog-api-key": settings.gemini_api_key}, params={"pageSize": 200}, timeout=30,
    )
    if r.status_code != 200:
        print(f"Gemini respondió {r.status_code}: {r.text[:300]}")
        return
    flash = [
        m["name"].removeprefix("models/") for m in r.json().get("models", [])
        if "flash" in m["name"] and "generateContent" in m.get("supportedGenerationMethods", [])
    ]
    print("Modelos Flash disponibles con tu clave:")
    for nombre in flash:
        print("  -", nombre, "  <- configurado" if nombre in settings.gemini_modelos else "")
    print("\nProbando los modelos configurados (principal y respaldo):")
    for modelo in settings.gemini_modelos:
        inicio = time.time()
        try:
            respuesta = ia.llamar_modelo("Responde solo: 'Conexión con Gemini correcta'.", modelo)
            print(f"  {modelo}: OK en {time.time() - inicio:.1f} s -> {respuesta}")
        except ia.ErrorIA as e:
            print(f"  {modelo}: ERROR -> {e}")


if __name__ == "__main__":
    main()
