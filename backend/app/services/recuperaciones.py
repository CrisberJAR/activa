"""Recuperaciones: cronograma, pagos registrados, atrasos, alertas preventivas y mensajes respetuosos.

La plataforma no mueve dinero: los pagos los informa la entidad y aquí solo se registran.
"""
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import cargar_yaml, hoy_peru
from app.models import CompromisoPago, Credito, Cuota, Reprogramacion
from app.services.simulador import simular

CERO = Decimal("0.00")


def config() -> dict:
    return cargar_yaml("recuperaciones")


def generar_cuotas(credito: Credito) -> None:
    """Crea el cronograma del crédito con el método francés (mismo cálculo del simulador)."""
    r = simular(credito.monto, float(credito.tea), credito.plazo_meses, credito.frecuencia, credito.fecha_desembolso)
    credito.cuotas = [
        Cuota(numero=c["numero"], fecha_vencimiento=c["fecha"], capital=c["capital"], interes=c["interes"],
              monto=c["cuota"], pagado=CERO)
        for c in r["cronograma"]
    ]


def pendiente(c: Cuota) -> Decimal:
    return Decimal(c.monto) - Decimal(c.pagado or 0)


def estado_cuota(c: Cuota, hoy: date) -> str:
    if pendiente(c) <= 0:
        return "pagada"
    if c.fecha_vencimiento < hoy:
        return "vencida"
    return "parcial" if (c.pagado or 0) > 0 else "pendiente"


def saldo_pendiente(credito: Credito) -> Decimal:
    return sum((pendiente(c) for c in credito.cuotas), CERO)


def aplicar_pago(credito: Credito, monto: Decimal, fecha: date) -> None:
    """Reparte el pago entre las cuotas más antiguas. Lanza ValueError si supera el saldo."""
    monto = Decimal(monto)
    if monto <= 0:
        raise ValueError("El monto debe ser mayor que cero")
    if monto > saldo_pendiente(credito):
        raise ValueError(f"El pago supera el saldo pendiente (S/ {saldo_pendiente(credito):,.2f})")
    for c in credito.cuotas:
        if monto <= 0:
            break
        falta = pendiente(c)
        if falta <= 0:
            continue
        abono = min(falta, monto)
        c.pagado = Decimal(c.pagado or 0) + abono
        monto -= abono
        if pendiente(c) <= 0:
            c.fecha_pago = fecha
    if saldo_pendiente(credito) <= 0:
        credito.estado = "cancelado"


def dias_atraso(credito: Credito, hoy: date) -> int:
    vencidas = [c.fecha_vencimiento for c in credito.cuotas if pendiente(c) > 0 and c.fecha_vencimiento < hoy]
    return (hoy - min(vencidas)).days if vencidas else 0


def monto_vencido(credito: Credito, hoy: date) -> Decimal:
    return sum((pendiente(c) for c in credito.cuotas if c.fecha_vencimiento < hoy and pendiente(c) > 0), CERO)


def tramo(dias: int) -> dict:
    for t in config()["tramos"]:
        if t["hasta"] is None or dias <= t["hasta"]:
            return t
    return config()["tramos"][-1]


def proxima_cuota(credito: Credito) -> Cuota | None:
    return next((c for c in credito.cuotas if pendiente(c) > 0), None)


def resumen(credito: Credito, hoy: date | None = None) -> dict:
    hoy = hoy or hoy_peru()
    dias = dias_atraso(credito, hoy)
    return {
        "dias_atraso": dias,
        "tramo": tramo(dias),
        "saldo": saldo_pendiente(credito),
        "vencido": monto_vencido(credito, hoy),
        "pagadas": sum(1 for c in credito.cuotas if pendiente(c) <= 0),
        "vencidas": sum(1 for c in credito.cuotas if estado_cuota(c, hoy) == "vencida"),
        "pendientes": sum(1 for c in credito.cuotas if pendiente(c) > 0),
        "proxima": proxima_cuota(credito),
    }


def actualizar_compromisos(db: Session, hoy: date | None = None) -> int:
    """Marca como incumplidos los compromisos vencidos sin pago. Devuelve cuántos cambió."""
    hoy = hoy or hoy_peru()
    vencidos = db.scalars(select(CompromisoPago).where(CompromisoPago.estado == "pendiente", CompromisoPago.fecha < hoy)).all()
    for c in vencidos:
        c.estado = "incumplido"
    if vencidos:
        db.commit()
    return len(vencidos)


def creditos_de(db: Session, usuario, solo_vigentes: bool = True) -> list[Credito]:
    """Cartera visible: el gestor ve sus créditos asignados; el gerente, todos."""
    consulta = select(Credito).options(selectinload(Credito.cuotas), selectinload(Credito.cliente)).order_by(Credito.id)
    if solo_vigentes:
        consulta = consulta.where(Credito.estado == "vigente")
    if usuario.rol == "gestor_recuperaciones":
        consulta = consulta.where(Credito.gestor_id == usuario.id)
    return db.scalars(consulta).all()


def alertas(db: Session, usuario, hoy: date | None = None) -> list[dict]:
    """Alertas internas: próximos vencimientos, cuotas vencidas, compromisos y reprogramaciones pendientes."""
    hoy = hoy or hoy_peru()
    cfg = config()
    salida = []
    creditos = creditos_de(db, usuario)
    ids = [c.id for c in creditos]
    limite = hoy + timedelta(days=cfg["dias_aviso_vencimiento"])
    for cr in creditos:
        for c in cr.cuotas:
            if pendiente(c) <= 0:
                continue
            if c.fecha_vencimiento < hoy:
                salida.append({"tipo": "cuota_vencida", "nivel": "danger", "credito": cr, "cuota": c, "fecha": c.fecha_vencimiento, "monto": pendiente(c),
                               "texto": f"Cuota {c.numero} vencida hace {(hoy - c.fecha_vencimiento).days} días · S/ {pendiente(c):,.2f}"})
                break  # una alerta por crédito: la cuota más antigua
            if c.fecha_vencimiento <= limite:
                dias = (c.fecha_vencimiento - hoy).days
                cuando = "hoy" if dias == 0 else f"en {dias} día(s)"
                salida.append({"tipo": "proximo_vencimiento", "nivel": "warning", "credito": cr, "cuota": c, "fecha": c.fecha_vencimiento, "monto": pendiente(c),
                               "texto": f"Cuota {c.numero} vence {cuando} · S/ {pendiente(c):,.2f}"})
            break
    if ids:
        limite_comp = hoy + timedelta(days=cfg["dias_aviso_compromiso"])
        for cp in db.scalars(select(CompromisoPago).where(CompromisoPago.credito_id.in_(ids))).all():
            if cp.estado == "pendiente" and hoy <= cp.fecha <= limite_comp:
                salida.append({"tipo": "compromiso_proximo", "nivel": "info", "credito": cp.credito, "fecha": cp.fecha, "monto": cp.monto,
                               "texto": f"Compromiso de pago para el {cp.fecha:%d/%m/%Y} · S/ {cp.monto:,.2f}"})
            elif cp.estado == "incumplido" or (cp.estado == "pendiente" and cp.fecha < hoy):
                salida.append({"tipo": "compromiso_incumplido", "nivel": "danger", "credito": cp.credito, "fecha": cp.fecha,
                               "texto": f"Compromiso del {cp.fecha:%d/%m/%Y} incumplido · S/ {cp.monto:,.2f}"})
        for rp in db.scalars(select(Reprogramacion).where(Reprogramacion.credito_id.in_(ids), Reprogramacion.estado == "pendiente")).all():
            salida.append({"tipo": "reprogramacion_pendiente", "nivel": "secondary", "credito": rp.credito, "fecha": rp.creado_en.date(),
                           "texto": f"Solicitud de {rp.tipo} pendiente de revisión"})
    orden = {"cuota_vencida": 0, "compromiso_incumplido": 1, "proximo_vencimiento": 2, "compromiso_proximo": 3, "reprogramacion_pendiente": 4}
    return sorted(salida, key=lambda a: (orden[a["tipo"]], a["fecha"]))


TIPOS_ALERTA = {
    "cuota_vencida": "Cuota vencida",
    "compromiso_incumplido": "Compromiso incumplido",
    "proximo_vencimiento": "Próximo vencimiento",
    "compromiso_proximo": "Compromiso próximo",
    "reprogramacion_pendiente": "Reprogramación pendiente",
}


def mensaje_sugerido(tipo: str, credito: Credito, fecha: date, monto: Decimal) -> str:
    plantilla = config()["mensajes"][tipo]
    nombre = credito.cliente.nombres.split()[0]
    return plantilla.format(nombre=nombre, fecha=f"{fecha:%d/%m/%Y}", monto=f"S/ {monto:,.2f}").strip()


def enlace_whatsapp(credito: Credito, texto: str) -> str | None:
    """Solo si el cliente dio su consentimiento y tiene un celular peruano válido."""
    tel = credito.cliente.telefono
    if not credito.cliente.consentimiento or not (len(tel) == 9 and tel.startswith("9")):
        return None
    return f"https://wa.me/51{tel}?text={quote(texto)}"
