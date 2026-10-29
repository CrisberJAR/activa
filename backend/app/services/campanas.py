"""Generación de campañas crediticias con IA (Fase 5c).

Gemini devuelve un JSON con las 5 secciones; se valida con Pydantic y se revisa que no
invente tasas ni prometa aprobación. Si Gemini falla, se arma una campaña de plantilla.
Solo el gerente edita y publica; una campaña es vigente si está publicada y dentro de sus fechas.
"""
import json
import re
from datetime import date, datetime, timedelta, timezone

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalogos import SECTORES, TEMPORADAS, TIPOS_CLIENTE
from app.config import cargar_tipos_campana, hoy_peru
from app.models import Bloque, Campana
from app.schemas import CampanaContenido, CampanaEntrada
from app.services import ia
from app.services.analisis import normalizar, ultimo_analisis

# ---------- Reglas: ni tasas inventadas ni promesas de aprobación ----------

_NUMERO_PCT = r"\d+(?:[.,]\d+)?\s*%"
PROHIBIDO = [
    (re.compile(rf"\b(tasa|tea|tcea|tem|interes|intereses)\b[^.\n]{{0,40}}{_NUMERO_PCT}"), "menciona una tasa de interés"),
    (re.compile(rf"{_NUMERO_PCT}[^.\n]{{0,25}}\b(tasa|tea|tcea|interes|anual|mensual)"), "menciona una tasa de interés"),
    (re.compile(r"\b(tea|tcea)\s*(de\s*)?\d"), "menciona una tasa de interés"),
    (re.compile(r"aprobacion (garantizada|segura|asegurada|inmediata|al instante)"), "promete aprobación"),
    (re.compile(r"\b(credito|prestamo) (garantizado|asegurado|seguro|aprobado)"), "promete aprobación"),
    (re.compile(r"(100\s*% aprobado|aprobado seguro|te aprobamos|garantizamos (tu|el|su) (credito|prestamo))"),
     "promete aprobación"),
    (re.compile(r"\bsin (evaluacion|requisitos|revisar)"), "promete crédito sin evaluación"),
]


def _textos(contenido: dict) -> list[str]:
    """Todos los textos de la campaña, para revisarlos."""
    textos = []

    def recorrer(valor):
        if isinstance(valor, str):
            textos.append(valor)
        elif isinstance(valor, dict):
            for v in valor.values():
                recorrer(v)
        elif isinstance(valor, list):
            for v in valor:
                recorrer(v)

    recorrer(contenido)
    return textos


def infracciones(contenido: dict) -> list[str]:
    """Reglas que incumple el texto (lista vacía si está bien)."""
    encontradas = []
    for texto in _textos(contenido):
        limpio = normalizar(texto)
        for patron, motivo in PROHIBIDO:
            if patron.search(limpio) and motivo not in encontradas:
                encontradas.append(motivo)
    return encontradas


# ---------- Prompt y validación de la respuesta de Gemini ----------

FORMATO_JSON = """{
  "nombre": "nombre corto y atractivo de la campaña (máx. 8 palabras)",
  "propuesta_valor": "2 o 3 frases: qué problema de la temporada resuelve y por qué conviene al cliente",
  "decisiones_gerencia": ["3 a 5 decisiones concretas que debe tomar el gerente (presupuesto, asesores, condiciones, metas)"],
  "capacitacion": {
    "speech": "guion de 4 a 6 frases que el asesor dice al cliente, en tono cercano",
    "objeciones": [{"objecion": "lo que diría el cliente", "respuesta": "cómo responde el asesor"}]
  },
  "marketing": {
    "canales": ["3 a 5 canales concretos: WhatsApp, visitas, perifoneo en el mercado, Facebook, radio local, etc."],
    "gancho": "frase gancho de 1 línea",
    "mensaje_whatsapp": "mensaje listo para enviar, máx. 60 palabras, con 1 o 2 emojis y una pregunta final"
  }
}"""


def crear_prompt(entrada: CampanaEntrada, contexto: list[str]) -> str:
    tipo = cargar_tipos_campana()[entrada.tipo_campana]
    monto = f"S/ {entrada.monto_maximo:.0f}" if entrada.monto_maximo else "según evaluación"
    datos = [
        f"Tipo de campaña: {tipo['nombre']} ({tipo['descripcion']})",
        f"Temporada: {TEMPORADAS[entrada.temporada]}",
        f"Público objetivo: {entrada.publico_objetivo}",
        f"Necesidad o riesgo que atiende: {entrada.necesidad}",
        f"Monto máximo: {monto}; plazo: {entrada.plazo_meses} meses; periodo de gracia: {entrada.periodo_gracia_meses} meses",
        f"Zona: {entrada.zona}; tipo de cliente: {TIPOS_CLIENTE[entrada.tipo_cliente]}",
        f"Duración: {entrada.duracion_semanas} semanas desde {entrada.fecha_inicio:%d/%m/%Y}",
        f"Presupuesto de difusión: S/ {entrada.presupuesto_difusion:.0f}; meta: {entrada.meta_creditos} créditos",
    ]
    lineas = "\n".join("- " + d for d in datos + contexto)
    return f"""Eres especialista en marketing de una microfinanciera de Huánuco (Perú) que atiende agricultores, comerciantes de mercado, ambulantes y taxistas.
Diseña una campaña crediticia con estos datos:
{lineas}

Responde SOLO con un JSON válido con exactamente esta estructura (textos en español sencillo, tono cercano):
{FORMATO_JSON}

Reglas obligatorias:
- NO menciones tasas de interés, TEA, TCEA ni porcentajes de interés: las define la gerencia.
- NO prometas aprobación: todo crédito está sujeto a evaluación; puedes decir "sujeto a evaluación".
- No inventes datos de clientes ni cifras que no estén arriba.
- Incluye 3 objeciones típicas del cliente con su respuesta."""


def validar_contenido(texto: str) -> dict:
    """JSON de Gemini → contenido validado. Lanza ErrorIA reintentable si no sirve."""
    try:
        datos = json.loads(texto)
        contenido = CampanaContenido(**datos).model_dump()
    except (ValueError, TypeError, ValidationError) as e:
        raise ia.ErrorIA(f"respuesta con formato inválido ({type(e).__name__})", reintentable=True) from e
    problemas = infracciones(contenido)
    if problemas:
        raise ia.ErrorIA("la respuesta " + " y ".join(problemas), reintentable=True)
    return contenido


# ---------- Plantilla de respaldo (sin IA) ----------

def contenido_plantilla(entrada: CampanaEntrada) -> dict:
    tipo = cargar_tipos_campana()[entrada.tipo_campana]
    temporada = TEMPORADAS[entrada.temporada].lower()
    monto = f"hasta S/ {entrada.monto_maximo:.0f}" if entrada.monto_maximo else "según tu capacidad de pago"
    gracia = (f" y {entrada.periodo_gracia_meses} mes(es) de gracia" if entrada.periodo_gracia_meses else "")
    contenido = {
        "nombre": f"{tipo['nombre']} {entrada.fecha_inicio.year}"[:120],
        "propuesta_valor": (
            f"Crédito {monto}, a {entrada.plazo_meses} meses{gracia}, pensado para {entrada.publico_objetivo.lower()}. "
            f"Atiende esta necesidad: {entrada.necesidad.rstrip('.')}. Sujeto a evaluación."
        ),
        "decisiones_gerencia": [
            f"Aprobar el presupuesto de difusión de S/ {entrada.presupuesto_difusion:.0f}.",
            "Definir la tasa y las condiciones según la política de créditos vigente.",
            f"Asignar asesores en {entrada.zona} para lograr la meta de {entrada.meta_creditos} créditos.",
            f"Confirmar el periodo de gracia de {entrada.periodo_gracia_meses} mes(es) y el plazo de {entrada.plazo_meses} meses.",
        ],
        "capacitacion": {
            "speech": (
                f"Buenos días, soy asesor de Grupo Activa. Sabemos que en temporada de {temporada} "
                f"aparecen gastos como: {entrada.necesidad.rstrip('.').lower()}. Tenemos la campaña "
                f"{tipo['nombre']}, con un crédito a {entrada.plazo_meses} meses{gracia}. "
                "Si le interesa, revisamos juntos su caso; todo crédito está sujeto a evaluación."
            ),
            "objeciones": [
                {"objecion": "No quiero endeudarme.",
                 "respuesta": "Lo entiendo. Calculamos juntos una cuota que pueda pagar con lo que genera su negocio."},
                {"objecion": "No tengo garantía.",
                 "respuesta": "Evaluamos su negocio y su historial; en algunos casos basta con un aval."},
                {"objecion": "Ya tengo un crédito en otra entidad.",
                 "respuesta": "Podemos revisar su capacidad de pago para ver qué opción le conviene más."},
            ],
        },
        "marketing": {
            "canales": ["WhatsApp", "Visitas del asesor", "Perifoneo en mercados y paraderos", "Facebook"],
            "gancho": f"¡Prepárate para la temporada de {temporada} con Grupo Activa!",
            "mensaje_whatsapp": (
                f"Hola 👋 En Grupo Activa tenemos la campaña {tipo['nombre']}: crédito a "
                f"{entrada.plazo_meses} meses{gracia}, sujeto a evaluación. ¿Te gustaría que un asesor te visite?"
            ),
        },
    }
    return CampanaContenido(**contenido).model_dump()


# ---------- Generación y estado ----------

def vigencia(entrada: CampanaEntrada) -> tuple[date, date]:
    return entrada.fecha_inicio, entrada.fecha_inicio + timedelta(weeks=entrada.duracion_semanas) - timedelta(days=1)


def generar_contenido(entrada: CampanaEntrada, contexto: list[str]) -> tuple[dict, str, str | None]:
    """Devuelve (contenido, generado_con, error). generado_con = modelo de Gemini o 'plantilla'."""
    try:
        contenido, modelo = ia.llamar_gemini(
            crear_prompt(entrada, contexto), json=True, validar=validar_contenido, timeout=45
        )
        return contenido, modelo, None
    except ia.ErrorIA as e:
        return contenido_plantilla(entrada), "plantilla", str(e)


def aplicar_entrada(campana: Campana, entrada: CampanaEntrada) -> None:
    campana.entradas = entrada.model_dump(mode="json")
    campana.tipo_campana = entrada.tipo_campana
    campana.temporada = entrada.temporada
    campana.bloque_id = entrada.bloque_id
    campana.vigente_desde, campana.vigente_hasta = vigencia(entrada)


def estado_visible(c: Campana, hoy: date | None = None) -> str:
    """borrador | programada | vigente | finalizada | retirada."""
    hoy = hoy or hoy_peru()
    if c.estado != "publicada":
        return c.estado
    if c.vigente_desde and hoy < c.vigente_desde:
        return "programada"
    if c.vigente_hasta and hoy > c.vigente_hasta:
        return "finalizada"
    return "vigente"


def publicar(c: Campana, gerente_id: int) -> str | None:
    """Publica la campaña. Devuelve un mensaje de error si no se puede."""
    if c.estado != "borrador":
        return "Solo se publican campañas en borrador"
    if c.vigente_hasta and c.vigente_hasta < hoy_peru():
        return "La fecha de fin ya pasó: edita la fecha de inicio o la duración antes de publicar"
    c.estado = "publicada"
    c.publicado_por = gerente_id
    c.publicado_en = datetime.now(timezone.utc)
    return None


def vigentes(db: Session, hoy: date | None = None) -> list[Campana]:
    """Campañas publicadas dentro de sus fechas (las que puede ofrecer el chatbot)."""
    hoy = hoy or hoy_peru()
    return db.scalars(
        select(Campana).where(
            Campana.estado == "publicada", Campana.vigente_desde <= hoy, Campana.vigente_hasta >= hoy
        ).order_by(Campana.vigente_hasta)
    ).all()


def campana_a_dict(c: Campana) -> dict:
    return {
        "id": c.id,
        "nombre": c.nombre,
        "tipo_campana": c.tipo_campana,
        "temporada": c.temporada,
        "estado": estado_visible(c),
        "vigente_desde": c.vigente_desde.isoformat() if c.vigente_desde else None,
        "vigente_hasta": c.vigente_hasta.isoformat() if c.vigente_hasta else None,
        "entradas": c.entradas,
        "contenido": c.contenido,
    }


# ---------- Datos del bloque: contexto para la IA y valores sugeridos del formulario ----------

def contexto_bloque(db: Session, bloque_id: int | None, estacion: dict | None) -> list[str]:
    """Resumen agregado del último análisis del bloque (sin datos personales) y la estación IoT."""
    lineas = []
    analisis = ultimo_analisis(db, bloque_id) if bloque_id else None
    if analisis:
        ind = analisis.indicadores
        lineas = ["Datos del bloque de encuestas que origina la campaña:"] + ia.resumen_bloque(
            ind, analisis.ranking_necesidades, None, ind.get("campana_modelo")
        )
    if estacion and estacion.get("estacion_actual"):
        lineas.append(f"Estación actual según los sensores IoT: {estacion['estacion_nombre']}; "
                      f"temporada que se acerca: {estacion['temporada_nombre']}. {estacion.get('mensaje') or ''}")
    return lineas


def valores_sugeridos(db: Session, bloque_id: int | None, estacion: dict | None) -> dict:
    """Prellena el formulario con el último análisis del bloque y la estación del IoT."""
    hoy = hoy_peru()
    v = {"tipo_cliente": "ambos", "periodo_gracia_meses": "0", "fecha_inicio": hoy.isoformat(),
         "duracion_semanas": "8", "presupuesto_difusion": "500", "meta_creditos": "20", "plazo_meses": "6"}
    if estacion and estacion.get("temporada_proxima"):
        v["temporada"] = estacion["temporada_proxima"]
    if bloque_id:
        v["bloque_id"] = str(bloque_id)
    analisis = ultimo_analisis(db, bloque_id) if bloque_id else None
    if analisis:
        ind = analisis.indicadores
        if analisis.tipo_campana_sugerida:
            v["tipo_campana"] = analisis.tipo_campana_sugerida
        v.setdefault("temporada", ind.get("temporada_frecuente"))
        sectores = ", ".join(SECTORES.get(s, s).lower() for s in list(ind["por_sector"])[:2])
        v["publico_objetivo"] = f"Clientes del sector {sectores} del bloque «{db.get(Bloque, bloque_id).nombre}»"
        principal = analisis.ranking_necesidades[0]
        v["necesidad"] = principal["nombre"]
        v["zona"] = ", ".join(list(ind["por_zona"])[:3])
        v["plazo_meses"] = str(round(ind["plazo_promedio"]) or 6)
        v["meta_creditos"] = str(max(5, round(ind["total"] * ind["pct_interes"] / 100)))
    return v
