"""Comercial: embudo de prospectos, indicadores y mensajes comerciales asistidos por IA."""
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.catalogos import SEGMENTOS
from app.config import hoy_peru
from app.models import Campana, Prospecto, Usuario
from app.services import ia
from app.services.campanas import infracciones

ESTADOS_TEXTO = {
    "nuevo": "Nuevo",
    "contactado": "Contactado",
    "interesado": "Interesado",
    "solicitud": "Solicitud iniciada",
    "evaluacion": "En evaluación",
    "convertido": "Convertido",
    "no_convertido": "No convertido",
}
ESTADOS_COLOR = {
    "nuevo": "secondary", "contactado": "info", "interesado": "primary", "solicitud": "warning",
    "evaluacion": "dark", "convertido": "success", "no_convertido": "danger",
}
FINALES = ("convertido", "no_convertido")


def visibles(usuario: Usuario):
    """Consulta de prospectos visibles: el asesor ve los suyos y los sin asignar; el gerente, todos."""
    consulta = select(Prospecto)
    if usuario.rol == "asesor":
        consulta = consulta.where((Prospecto.asesor_id == usuario.id) | (Prospecto.asesor_id.is_(None)))
    return consulta


def puede_ver(usuario: Usuario, p: Prospecto) -> bool:
    return usuario.rol == "gerente" or (usuario.rol == "asesor" and p.asesor_id in (None, usuario.id))


def embudo(db: Session, usuario: Usuario) -> dict:
    sub = visibles(usuario).subquery()
    conteo = dict(db.execute(select(sub.c.estado, func.count()).group_by(sub.c.estado)).all())
    filas = [{"estado": e, "nombre": ESTADOS_TEXTO[e], "cantidad": conteo.get(e, 0)} for e in ESTADOS_TEXTO]
    total = sum(f["cantidad"] for f in filas)
    cerrados = conteo.get("convertido", 0) + conteo.get("no_convertido", 0)
    return {
        "filas": filas,
        "total": total,
        "maximo": max([f["cantidad"] for f in filas] + [1]),
        # Tasa de conversión: convertidos sobre prospectos cerrados (convertidos + no convertidos)
        "tasa_conversion": round(100 * conteo.get("convertido", 0) / cerrados, 1) if cerrados else None,
        "conteo": conteo,
    }


def pendientes(db: Session, usuario: Usuario, hoy: date | None = None) -> list[Prospecto]:
    """Actividades vencidas o de hoy (próxima acción) de prospectos abiertos."""
    hoy = hoy or hoy_peru()
    consulta = visibles(usuario).where(
        Prospecto.proxima_accion.is_not(None), Prospecto.proxima_accion <= hoy, Prospecto.estado.not_in(FINALES)
    ).order_by(Prospecto.proxima_accion)
    if usuario.rol == "asesor":
        consulta = consulta.where(Prospecto.asesor_id == usuario.id)
    return db.scalars(consulta).all()


def desempeno_campanas(db: Session, limite: int = 5) -> list[dict]:
    """Campañas con más prospectos convertidos (y su tasa)."""
    filas = db.execute(
        select(
            Campana.id, Campana.nombre, func.count(Prospecto.id),
            func.sum(case((Prospecto.estado == "convertido", 1), else_=0)),
        )
        .join(Prospecto, Prospecto.campana_id == Campana.id)
        .group_by(Campana.id, Campana.nombre)
    ).all()
    salida = [
        {"id": i, "nombre": n, "prospectos": t, "convertidos": int(c or 0),
         "tasa": round(100 * int(c or 0) / t, 1) if t else 0}
        for i, n, t, c in filas
    ]
    return sorted(salida, key=lambda x: (-x["convertidos"], -x["prospectos"]))[:limite]


def resultados_campana(db: Session, campana_id: int) -> dict:
    conteo = dict(db.execute(
        select(Prospecto.estado, func.count()).where(Prospecto.campana_id == campana_id).group_by(Prospecto.estado)
    ).all())
    total = sum(conteo.values())
    return {"total": total, "convertidos": conteo.get("convertido", 0), "conteo": conteo,
            "tasa": round(100 * conteo.get("convertido", 0) / total, 1) if total else None}


# ---------- Mensaje comercial con IA ----------

def _datos_anonimos(p: Prospecto) -> list[str]:
    """Lo único que se envía a Gemini: sin nombre, teléfono, DNI ni montos personales."""
    lineas = [
        f"Tipo de cliente: {SEGMENTOS.get(p.segmento, p.segmento)}",
        f"Actividad: {ia.anonimizar(p.actividad, [p.nombre])}",
        f"Necesidad: {ia.anonimizar(p.necesidad, [p.nombre])}",
    ]
    if p.campana:
        lineas.append(f"Campaña vigente: {p.campana.nombre}. {p.campana.contenido.get('propuesta_valor', '')}")
    return lineas


def prompt_mensaje(p: Prospecto) -> str:
    datos = "\n".join("- " + l for l in _datos_anonimos(p))
    return f"""Eres asesor comercial de una entidad microfinanciera peruana. Escribe UN mensaje de WhatsApp
(máximo 60 palabras, tono cercano y respetuoso, español sencillo, 1 emoji como máximo) para retomar
el contacto con este cliente potencial. Termina con UNA sola pregunta.
Reglas: no menciones tasas de interés ni porcentajes, no prometas aprobación, no inventes requisitos
ni condiciones, no uses nombres (empieza con "Hola, ¿cómo está?").

Datos del cliente (anonimizados):
{datos}"""


def mensaje_plantilla(p: Prospecto) -> str:
    oferta = f" Tenemos la campaña «{p.campana.nombre}» que podría ayudarle." if p.campana else ""
    return (f"Hola, ¿cómo está? Le saluda su asesor. Conversamos sobre su necesidad para su actividad de "
            f"{p.actividad.lower()}.{oferta} ¿Le parece si coordinamos una visita o llamada esta semana?")


def _validar_mensaje(texto: str) -> str:
    texto = texto.strip().strip('"')
    if infracciones({"t": texto}) or len(texto) > 600:
        raise ia.ErrorIA("El mensaje no cumple las reglas", reintentable=True)
    return texto


def mensaje_comercial(p: Prospecto) -> dict:
    """{texto, fuente, error}: Gemini si responde y cumple las reglas; si no, plantilla."""
    try:
        texto, modelo = ia.llamar_gemini(prompt_mensaje(p), validar=_validar_mensaje, timeout=20)
        return {"texto": texto, "fuente": modelo, "error": None}
    except ia.ErrorIA as e:
        return {"texto": mensaje_plantilla(p), "fuente": "plantilla", "error": str(e)}
