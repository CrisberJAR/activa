"""Análisis de necesidades de un bloque: indicadores y ranking (Fase 5a).

La parte de cálculo es pura (recibe listas de diccionarios) para probarla sin base de datos.
Se usan SOLO las encuestas del bloque elegido.
"""
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import HORA_PERU, cargar_necesidades, hoy_peru
from app.models import AnalisisBloque, Bloque, Encuesta
from app.services import ia, ml

# Campos que entran al análisis. Nombre y teléfono NO: no se necesitan y así nunca llegan a la IA
CAMPOS = (
    "zona", "sector", "ingreso_mensual", "anios_negocio", "trabajadores", "frecuencia_ingresos",
    "credito_vigente", "garantia", "necesidad", "monto", "plazo_meses", "temporada_necesidad",
    "riesgo_principal", "interes_campana", "contacto_preferido",
)


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes: 'Mercadería' → 'mercaderia'."""
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")


def clasificar(necesidad: str, config: dict) -> str:
    """Devuelve la clave de la primera categoría cuya palabra aparece en el texto."""
    texto = normalizar(necesidad)
    for clave, cat in config["categorias"].items():
        for palabra in cat["palabras"]:
            if re.search(r"\b" + re.escape(normalizar(palabra)), texto):
                return clave
    return "otros"


def _pct(parte: int, total: int) -> float:
    return round(100 * parte / total, 1) if total else 0.0


def _promedio(valores: list[float]) -> float:
    return round(sum(valores) / len(valores), 1) if valores else 0.0


def _mas_frecuente(conteo: Counter) -> str | None:
    return conteo.most_common(1)[0][0] if conteo else None


def calcular_indicadores(encuestas: list[dict]) -> dict:
    total = len(encuestas)
    por = {campo: Counter(e[campo] for e in encuestas)
           for campo in ("sector", "zona", "temporada_necesidad", "riesgo_principal", "contacto_preferido", "garantia")}
    return {
        "total": total,
        "por_sector": dict(por["sector"].most_common()),
        "por_zona": dict(por["zona"].most_common()),
        "por_temporada": dict(por["temporada_necesidad"].most_common()),
        "por_riesgo": dict(por["riesgo_principal"].most_common()),
        "sector_principal": _mas_frecuente(por["sector"]),
        "temporada_frecuente": _mas_frecuente(por["temporada_necesidad"]),
        "riesgo_frecuente": _mas_frecuente(por["riesgo_principal"]),
        "contacto_frecuente": _mas_frecuente(por["contacto_preferido"]),
        "ingreso_promedio": _promedio([float(e["ingreso_mensual"]) for e in encuestas]),
        "monto_promedio": _promedio([float(e["monto"]) for e in encuestas]),
        "monto_total": round(sum(float(e["monto"]) for e in encuestas), 2),
        "plazo_promedio": _promedio([e["plazo_meses"] for e in encuestas]),
        "pct_credito_vigente": _pct(sum(e["credito_vigente"] for e in encuestas), total),
        "pct_interes": _pct(sum(e["interes_campana"] for e in encuestas), total),
        "pct_sin_garantia": _pct(por["garantia"]["ninguna"], total),
    }


def ranking_necesidades(encuestas: list[dict], config: dict) -> list[dict]:
    """Agrupa las necesidades por categoría, de la más pedida a la menos pedida."""
    grupos: dict[str, list[dict]] = {}
    for e in encuestas:
        grupos.setdefault(clasificar(e["necesidad"], config), []).append(e)
    nombres = {k: v["nombre"] for k, v in config["categorias"].items()} | {"otros": config["otros"]["nombre"]}
    orden = list(nombres)  # en empate, el orden del YAML
    ranking = [
        {
            "categoria": clave,
            "nombre": nombres[clave],
            "cantidad": len(grupo),
            "porcentaje": _pct(len(grupo), len(encuestas)),
            "monto_promedio": _promedio([float(e["monto"]) for e in grupo]),
            "temporada_frecuente": _mas_frecuente(Counter(e["temporada_necesidad"] for e in grupo)),
            "sectores": dict(Counter(e["sector"] for e in grupo).most_common()),
        }
        for clave, grupo in grupos.items()
    ]
    return sorted(ranking, key=lambda r: (-r["cantidad"], orden.index(r["categoria"])))


# ---------- Unión con la base de datos ----------

def _mes_peru(momento: datetime | None) -> int:
    """Mes (hora de Perú) en que se registró la encuesta; el modelo lo usa para las campañas festivas."""
    if momento is None:
        return hoy_peru().month
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(HORA_PERU).month


def encuestas_del_bloque(db: Session, bloque_id: int) -> tuple[list[dict], list[str]]:
    """Encuestas del bloque (sin datos personales) y, aparte, los nombres para anonimizar textos."""
    filas = db.scalars(select(Encuesta).where(Encuesta.bloque_id == bloque_id)).all()
    encuestas = [{c: getattr(e, c) for c in CAMPOS} | {"mes": _mes_peru(e.creado_en)} for e in filas]
    return encuestas, [e.nombre for e in filas]


def sugerencia_modelo(encuestas: list[dict], config: dict) -> dict | None:
    """Tipo de campaña sugerido por el Random Forest (None si el modelo no está entrenado)."""
    filas = [ml.caracteristicas(e, clasificar(e["necesidad"], config), e["mes"]) for e in encuestas]
    sugerencia = ml.sugerir(filas)
    if sugerencia:
        sugerencia.pop("por_cliente")  # no se guarda el detalle por cliente
    return sugerencia


def ultimo_analisis(db: Session, bloque_id: int) -> AnalisisBloque | None:
    return db.scalar(
        select(AnalisisBloque).where(AnalisisBloque.bloque_id == bloque_id)
        .order_by(AnalisisBloque.creado_en.desc(), AnalisisBloque.id.desc())
    )


def analizar_bloque(db: Session, bloque: Bloque, estacion: dict | None) -> AnalisisBloque | None:
    """Calcula y guarda un análisis nuevo. Devuelve None si el bloque no tiene encuestas."""
    encuestas, nombres = encuestas_del_bloque(db, bloque.id)
    if not encuestas:
        return None
    config = cargar_necesidades()
    indicadores = calcular_indicadores(encuestas)
    ranking = ranking_necesidades(encuestas, config)
    campana = sugerencia_modelo(encuestas, config)
    textos = [ia.anonimizar(e["necesidad"], nombres) for e in encuestas]
    patron = ia.texto_patron(indicadores, ranking, textos, estacion, campana)
    # Datos del contexto guardados junto a los indicadores (sin migración nueva)
    indicadores["estacion_actual"] = estacion.get("estacion_actual") if estacion else None
    indicadores["fuente_texto"] = patron["fuente"]
    indicadores["modelo_ia"] = patron["modelo"]
    indicadores["error_ia"] = patron["error"]
    indicadores["campana_modelo"] = campana
    analisis = AnalisisBloque(
        bloque_id=bloque.id, indicadores=indicadores, ranking_necesidades=ranking, texto_patron=patron["texto"],
        tipo_campana_sugerida=campana["sugerida"] if campana else None,
    )
    db.add(analisis)
    db.commit()
    return analisis


def analisis_a_dict(a: AnalisisBloque) -> dict:
    return {
        "id": a.id,
        "bloque_id": a.bloque_id,
        "creado_en": a.creado_en.isoformat() if a.creado_en else None,
        "indicadores": a.indicadores,
        "ranking_necesidades": a.ranking_necesidades,
        "texto_patron": a.texto_patron,
        "tipo_campana_sugerida": a.tipo_campana_sugerida,
    }
