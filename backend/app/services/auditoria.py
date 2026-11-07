"""Auditoría: guarda quién hizo qué y cuándo, y controla los intentos de inicio de sesión."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import cargar_yaml
from app.models import Auditoria, Usuario

# Acción guardada → texto que ve el gerente
ACCIONES = {
    "login_ok": "Inicio de sesión",
    "login_fallido": "Intento fallido de inicio de sesión",
    "login_bloqueado": "Ingreso bloqueado por intentos",
    "bloque_creado": "Bloque creado",
    "bloque_abierto": "Bloque abierto",
    "bloque_cerrado": "Bloque cerrado",
    "encuesta_creada": "Encuesta registrada",
    "encuesta_editada": "Encuesta editada",
    "campana_generada": "Campaña generada",
    "campana_editada": "Campaña editada",
    "campana_regenerada": "Campaña regenerada",
    "campana_publicada": "Campaña publicada",
    "campana_retirada": "Campaña retirada",
    "campana_eliminada": "Borrador eliminado",
    "interesado_atendido": "Interesado atendido",
    "interesado_reabierto": "Interesado reabierto",
    "acceso_denegado": "Acceso denegado",
    "usuario_creado": "Usuario creado",
    "usuario_activado": "Usuario activado",
    "usuario_desactivado": "Usuario desactivado",
    # Comercial
    "prospecto_creado": "Prospecto registrado",
    "prospecto_editado": "Prospecto editado",
    "prospecto_contacto": "Contacto con prospecto",
    "prospecto_asignado": "Prospecto asignado",
    "campana_enviada": "Campaña enviada a aprobación",
    "campana_devuelta": "Campaña devuelta a borrador",
    # Negocios
    "cliente_creado": "Expediente creado",
    "cliente_editado": "Expediente editado",
    "solicitud_creada": "Solicitud creada",
    "solicitud_editada": "Solicitud editada",
    "solicitud_estado": "Cambio de estado de solicitud",
    "documento_estado": "Documento revisado",
    # Riesgos
    "riesgo_evaluado": "Evaluación preliminar de riesgos",
    "riesgo_opinion": "Opinión del analista",
    # Recuperaciones
    "credito_registrado": "Crédito registrado para seguimiento",
    "pago_registrado": "Pago registrado",
    "gestion_registrada": "Gestión de cobranza",
    "compromiso_registrado": "Compromiso de pago",
    "compromiso_estado": "Compromiso actualizado",
    "reprogramacion_solicitada": "Reprogramación solicitada",
    "reprogramacion_revisada": "Reprogramación revisada",
    "credito_asignado": "Crédito asignado a gestor",
}


def config() -> dict:
    return cargar_yaml("seguridad")


def registrar(
    db: Session, accion: str, usuario: Usuario | None = None, detalle: str | None = None, email: str | None = None
) -> None:
    """Agrega un registro a la sesión; se guarda con el commit de la operación que se audita."""
    db.add(Auditoria(
        accion=accion,
        usuario_id=usuario.id if usuario else None,
        email=(email or (usuario.email if usuario else None) or "").strip().lower()[:160] or None,
        detalle=detalle,
    ))


def _ventana(cfg: dict) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=cfg["login"]["bloqueo_minutos"])


def intentos_fallidos(db: Session, email: str) -> int:
    """Intentos fallidos con este correo en la ventana de bloqueo, desde el último ingreso correcto."""
    cfg = config()
    email = email.strip().lower()
    desde = _ventana(cfg)
    ultimo_ok = db.scalar(
        select(func.max(Auditoria.creado_en)).where(Auditoria.email == email, Auditoria.accion == "login_ok")
    )
    consulta = select(func.count(Auditoria.id)).where(
        Auditoria.email == email, Auditoria.accion == "login_fallido", Auditoria.creado_en >= desde
    )
    if ultimo_ok is not None:
        consulta = consulta.where(Auditoria.creado_en > ultimo_ok)
    return db.scalar(consulta) or 0


def esta_bloqueado(db: Session, email: str) -> bool:
    return intentos_fallidos(db, email) >= config()["login"]["max_intentos"]


def mensaje_bloqueo() -> str:
    return f"Demasiados intentos fallidos. Espera {config()['login']['bloqueo_minutos']} minutos e inténtalo de nuevo."
