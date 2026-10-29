"""IA generativa con Google Gemini (solo desde el backend, por REST).

Reglas: nunca se envían nombres ni teléfonos (se anonimiza antes) y la IA no inventa tasas
ni promete aprobación. Si no hay clave o Gemini falla, se usa un texto automático de respaldo.
"""
import re

import httpx

from app.catalogos import RIESGOS, SECTORES, TEMPORADAS
from app.config import settings

URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"


class ErrorIA(Exception):
    def __init__(self, mensaje: str, reintentable: bool = False):
        super().__init__(mensaje)
        self.reintentable = reintentable  # True: conviene probar con otro modelo


# ---------- Anonimización ----------

_TELEFONO = re.compile(r"\+?\d[\d\s-]{5,}\d")
_CORREO = re.compile(r"\S+@\S+")


def anonimizar(texto: str, nombres: list[str] = ()) -> str:
    """Quita teléfonos, correos y las palabras de los nombres de los clientes."""
    texto = _CORREO.sub("[correo]", texto)
    texto = _TELEFONO.sub("[teléfono]", texto)
    palabras = {p for n in nombres for p in n.split() if len(p) >= 3}
    for p in sorted(palabras, key=len, reverse=True):
        texto = re.sub(rf"\b{re.escape(p)}\b", "[cliente]", texto, flags=re.IGNORECASE)
    return texto


# ---------- Llamada a Gemini ----------

def llamar_modelo(prompt: str, modelo: str) -> str:
    """Una consulta a un modelo concreto de Gemini."""
    try:
        r = httpx.post(
            URL_GEMINI.format(modelo=modelo),
            headers={"x-goog-api-key": settings.gemini_api_key},
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.4}},
            timeout=25,
        )
    except httpx.TimeoutException as e:
        raise ErrorIA(f"{modelo} tardó demasiado en responder", reintentable=True) from e
    except httpx.HTTPError as e:
        raise ErrorIA(f"No se pudo conectar con Gemini: {e}") from e
    if r.status_code == 429:
        raise ErrorIA(f"Se agotó la cuota gratuita de {modelo} por ahora", reintentable=True)
    if r.status_code in (500, 503):
        raise ErrorIA(f"{modelo} está saturado en este momento", reintentable=True)
    if r.status_code == 404:
        raise ErrorIA(f"El modelo '{modelo}' no existe: revisa GEMINI_MODELO", reintentable=True)
    if r.status_code in (400, 401, 403):
        raise ErrorIA(f"Gemini rechazó la clave o la consulta ({r.status_code}): revisa GEMINI_API_KEY")
    if r.status_code != 200:
        raise ErrorIA(f"Gemini respondió {r.status_code}: {r.text[:200]}")
    try:
        partes = r.json()["candidates"][0]["content"]["parts"]
        texto = "".join(p.get("text", "") for p in partes).strip()
    except (KeyError, IndexError, ValueError) as e:
        raise ErrorIA(f"{modelo} no devolvió texto (respuesta bloqueada o vacía)", reintentable=True) from e
    if not texto:
        raise ErrorIA(f"{modelo} devolvió un texto vacío", reintentable=True)
    return texto


def llamar_gemini(prompt: str) -> tuple[str, str]:
    """Prueba el modelo principal y, si está saturado o sin cuota, los de respaldo.

    Devuelve (texto, modelo que respondió).
    """
    if not settings.gemini_api_key:
        raise ErrorIA("Falta GEMINI_API_KEY en backend/.env")
    errores = []
    for modelo in settings.gemini_modelos:
        try:
            return llamar_modelo(prompt, modelo), modelo
        except ErrorIA as e:
            if not e.reintentable:
                raise
            errores.append(str(e))
    raise ErrorIA("Ningún modelo de Gemini respondió: " + "; ".join(errores))


# ---------- Texto del patrón del bloque ----------

def _resumen(indicadores: dict, ranking: list[dict], estacion: dict | None, campana: dict | None = None) -> list[str]:
    """Datos agregados (sin datos personales) que se le dan a la IA y a la plantilla."""
    lineas = [
        f"Encuestas del bloque: {indicadores['total']}",
        "Sectores: " + ", ".join(f"{SECTORES.get(k, k)} {v}" for k, v in indicadores["por_sector"].items()),
        "Zonas: " + ", ".join(f"{k} {v}" for k, v in indicadores["por_zona"].items()),
        f"Ingreso mensual promedio: S/ {indicadores['ingreso_promedio']:.0f}",
        f"Monto solicitado promedio: S/ {indicadores['monto_promedio']:.0f}; plazo promedio: {indicadores['plazo_promedio']} meses",
        f"Con crédito vigente: {indicadores['pct_credito_vigente']} %; interesados en campaña: {indicadores['pct_interes']} %; sin garantía: {indicadores['pct_sin_garantia']} %",
        "Temporada de mayor necesidad: " + ", ".join(f"{TEMPORADAS.get(k, k)} {v}" for k, v in indicadores["por_temporada"].items()),
        "Riesgo principal: " + ", ".join(f"{RIESGOS.get(k, k)} {v}" for k, v in indicadores["por_riesgo"].items()),
        "Ranking de necesidades: " + "; ".join(f"{r['nombre']} {r['cantidad']} ({r['porcentaje']} %)" for r in ranking),
    ]
    if estacion and estacion.get("estacion_actual"):
        lineas.append(f"Estación actual según los sensores IoT: {estacion['estacion_nombre']}. "
                      f"Temporada que se acerca: {estacion['temporada_nombre']}.")
    if campana:
        lineas.append("Tipo de campaña sugerido por el modelo Random Forest (clientes por tipo): "
                      + "; ".join(f"{r['nombre']} {r['cantidad']} ({r['porcentaje']} %)" for r in campana["reparto"][:4]))
    return lineas


def crear_prompt(
    indicadores: dict, ranking: list[dict], textos: list[str], estacion: dict | None, campana: dict | None = None
) -> str:
    datos = "\n".join("- " + l for l in _resumen(indicadores, ranking, estacion, campana))
    necesidades = "\n".join("- " + t for t in textos[:40])
    paso2 = ("2) por qué conviene la campaña sugerida por el modelo y cuándo lanzarla (puedes mencionar la segunda opción)."
             if campana else "2) qué tipo de campaña crediticia convendría preparar y cuándo.")
    return f"""Eres analista de una microfinanciera de Huánuco (Perú) que atiende agricultores, comerciantes de mercado, ambulantes y taxistas.
Con estos datos de UN bloque de encuestas, escribe en español sencillo un análisis de 2 párrafos cortos (máximo 150 palabras en total):
1) qué necesitan principalmente estos clientes y por qué, relacionándolo con la temporada y el riesgo;
{paso2}
Reglas: usa solo los datos dados; no inventes cifras, nombres, tasas de interés ni promesas de aprobación; no uses títulos ni viñetas.

Datos agregados:
{datos}

Necesidades escritas por los clientes (anonimizadas):
{necesidades}"""


def texto_plantilla(indicadores: dict, ranking: list[dict], estacion: dict | None, campana: dict | None = None) -> str:
    """Texto automático, sin IA, para cuando Gemini no está disponible."""
    principal = ranking[0]
    sector = SECTORES.get(indicadores["sector_principal"], indicadores["sector_principal"])
    temporada = TEMPORADAS.get(indicadores["temporada_frecuente"], indicadores["temporada_frecuente"])
    riesgo = RIESGOS.get(indicadores["riesgo_frecuente"], indicadores["riesgo_frecuente"])
    texto = (
        f"En este bloque se analizaron {indicadores['total']} encuestas, principalmente del sector {sector}. "
        f"La necesidad más frecuente es «{principal['nombre']}» ({principal['porcentaje']} % de los clientes), "
        f"con un monto promedio de S/ {principal['monto_promedio']:.0f}. "
        f"La temporada de mayor necesidad es {temporada} y el riesgo más mencionado es {riesgo}. "
        f"El {indicadores['pct_interes']} % muestra interés en una campaña."
    )
    if estacion and estacion.get("estacion_actual"):
        texto += f" Los sensores indican estación de {estacion['estacion_nombre']}"
        if estacion["temporada_proxima"] != estacion["estacion_actual"]:
            texto += f" y se acerca {estacion['temporada_nombre']}."
        else:
            texto += ", sin cambios relevantes a la vista."
    if campana:
        principal = campana["reparto"][0]
        texto += (f" El modelo sugiere preparar la campaña «{principal['nombre']}», "
                  f"adecuada para el {principal['porcentaje']} % de los clientes del bloque.")
    return texto


def texto_patron(
    indicadores: dict, ranking: list[dict], textos: list[str], estacion: dict | None, campana: dict | None = None
) -> dict:
    """Devuelve {texto, fuente ('gemini' o 'plantilla'), modelo, error}."""
    try:
        texto, modelo = llamar_gemini(crear_prompt(indicadores, ranking, textos, estacion, campana))
        return {"texto": texto, "fuente": "gemini", "modelo": modelo, "error": None}
    except ErrorIA as e:
        texto = texto_plantilla(indicadores, ranking, estacion, campana)
        return {"texto": texto, "fuente": "plantilla", "modelo": None, "error": str(e)}
