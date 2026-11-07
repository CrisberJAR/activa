"""Evaluación PRELIMINAR de riesgos: indicadores explicables y semáforo de alertas.

No aprueba ni rechaza créditos: marca qué requiere revisión humana y explica por qué.
Los umbrales están en config/riesgos.yaml (versionados y justificados).
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import cargar_yaml
from app.models import Auditoria, Cliente, EvaluacionRiesgo, Solicitud
from app.services import negocios
from app.services.simulador import cuota_estimada

NIVELES = {"verde": 0, "amarillo": 1, "rojo": 2}
ESTADOS_ACTIVOS = ("enviada", "en_evaluacion", "observada", "evaluada")

CAMPOS_CLIENTE = ("dni", "nombres", "telefono", "segmento", "ocupacion", "region", "ingresos_mensuales",
                  "gastos_mensuales", "antiguedad_meses")


def config() -> dict:
    return cargar_yaml("riesgos")


def _alerta(nivel: str, codigo: str, mensaje: str) -> dict:
    return {"nivel": nivel, "codigo": codigo, "mensaje": mensaje}


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.0f} %"


def completitud(cliente: Cliente, solicitud: Solicitud) -> dict:
    """Porcentaje de campos y documentos completos (los documentos cuentan solo si están validados)."""
    campos = [getattr(cliente, c) not in (None, "") for c in CAMPOS_CLIENTE]
    requeridos = [c["campo"] for c in negocios.CAMPOS_PERFIL.get(cliente.segmento, []) if c["requerido"]]
    campos += [solicitud.datos_perfil.get(c) not in (None, "") for c in requeridos]
    docs = solicitud.documentos
    docs_ok = [d.estado == "validado" for d in docs]
    total = len(campos) + len(docs_ok)
    hechos = sum(campos) + sum(docs_ok)
    return {
        "porcentaje": round(100 * hechos / total) if total else 100,
        "campos_faltantes": len(campos) - sum(campos),
        "documentos_pendientes": [d.tipo for d in docs if d.estado != "validado"],
    }


def evaluar(db: Session, solicitud: Solicitud) -> dict:
    """Calcula indicadores y alertas. No guarda nada (ver `guardar_evaluacion`)."""
    cfg = config()
    u = cfg["umbrales"]
    cliente = solicitud.cliente
    producto = negocios.productos().get(solicitud.producto, {})
    tea = float(producto.get("tea_demo", 0))

    ingresos = float(cliente.ingresos_mensuales or 0)
    gastos = float(cliente.gastos_mensuales or 0)
    otras = float(cliente.cuotas_otras_deudas or 0)
    ingreso_neto = ingresos - gastos
    capacidad = ingreso_neto - otras
    cuota = float(cuota_estimada(solicitud.monto, tea, solicitud.plazo_meses, solicitud.frecuencia))

    cuota_ingreso = cuota / ingresos if ingresos > 0 else None
    deuda_ingreso = (otras + cuota) / ingresos if ingresos > 0 else None
    cuota_capacidad = cuota / capacidad if capacidad > 0 else None
    comp = completitud(cliente, solicitud)

    alertas = []

    # --- Capacidad de pago ---
    if ingresos <= 0:
        alertas.append(_alerta("rojo", "sin_ingresos", "No hay ingresos declarados: no se puede estimar la capacidad de pago."))
    if capacidad <= 0:
        alertas.append(_alerta("rojo", "sin_capacidad",
                               f"Los gastos y cuotas declarados (S/ {gastos + otras:,.2f}) igualan o superan los ingresos (S/ {ingresos:,.2f})."))
    elif cuota_capacidad is not None:
        if cuota_capacidad >= u["cuota_capacidad"]["rojo"]:
            alertas.append(_alerta("rojo", "cuota_capacidad",
                                   f"La cuota estimada usa el {_pct(cuota_capacidad)} de la capacidad disponible (límite rojo {_pct(u['cuota_capacidad']['rojo'])})."))
        elif cuota_capacidad >= u["cuota_capacidad"]["amarillo"]:
            alertas.append(_alerta("amarillo", "cuota_capacidad",
                                   f"La cuota estimada usa el {_pct(cuota_capacidad)} de la capacidad disponible (revisar desde {_pct(u['cuota_capacidad']['amarillo'])})."))
    for clave, valor, texto in (("cuota_ingreso", cuota_ingreso, "Cuota / ingresos"),
                                ("deuda_ingreso", deuda_ingreso, "Deudas totales / ingresos")):
        if valor is None:
            continue
        if valor >= u[clave]["rojo"]:
            alertas.append(_alerta("rojo", clave, f"{texto}: {_pct(valor)} (límite rojo {_pct(u[clave]['rojo'])})."))
        elif valor >= u[clave]["amarillo"]:
            alertas.append(_alerta("amarillo", clave, f"{texto}: {_pct(valor)} (revisar desde {_pct(u[clave]['amarillo'])})."))

    # --- Completitud del expediente ---
    if comp["porcentaje"] < u["completitud"]["rojo"]:
        alertas.append(_alerta("rojo", "completitud", f"Expediente completo al {comp['porcentaje']} %: falta información importante."))
    elif comp["porcentaje"] < u["completitud"]["amarillo"]:
        detalle = []
        if comp["campos_faltantes"]:
            detalle.append(f"{comp['campos_faltantes']} campo(s) sin completar")
        if comp["documentos_pendientes"]:
            detalle.append(f"{len(comp['documentos_pendientes'])} documento(s) sin validar")
        alertas.append(_alerta("amarillo", "completitud", f"Expediente completo al {comp['porcentaje']} %: " + ", ".join(detalle) + "."))

    # --- Inconsistencias ---
    alertas += inconsistencias(db, solicitud, producto, ingreso_neto, cfg)

    semaforo = "verde"
    for a in alertas:
        if NIVELES[a["nivel"]] > NIVELES[semaforo]:
            semaforo = a["nivel"]

    return {
        "version": cfg["version"],
        "semaforo": semaforo,
        "explicacion": cfg["textos"][semaforo],
        "alertas": sorted(alertas, key=lambda a: -NIVELES[a["nivel"]]),
        "indicadores": {
            "ingresos": round(ingresos, 2),
            "gastos": round(gastos, 2),
            "cuotas_otras_deudas": round(otras, 2),
            "ingreso_neto": round(ingreso_neto, 2),
            "capacidad_disponible": round(capacidad, 2),
            "cuota_estimada_mensual": round(cuota, 2),
            "tea_demo": tea,
            "cuota_ingreso": None if cuota_ingreso is None else round(cuota_ingreso, 4),
            "deuda_ingreso": None if deuda_ingreso is None else round(deuda_ingreso, 4),
            "cuota_capacidad": None if cuota_capacidad is None else round(cuota_capacidad, 4),
            "completitud": comp["porcentaje"],
            "documentos_pendientes": comp["documentos_pendientes"],
        },
    }


def inconsistencias(db: Session, solicitud: Solicitud, producto: dict, ingreso_neto: float, cfg: dict) -> list[dict]:
    """Montos incoherentes, posibles duplicados y cambios inusuales. No afirma fraude: pide revisión."""
    u = cfg["umbrales"]
    cliente = solicitud.cliente
    alertas = []

    if producto:
        errores = negocios.validar_condiciones(solicitud.producto, cliente.segmento, solicitud.monto,
                                               solicitud.plazo_meses, solicitud.frecuencia)
        for msg in errores.values():
            alertas.append(_alerta("amarillo", "condiciones_producto", f"Condiciones del producto: {msg}."))
    else:
        alertas.append(_alerta("amarillo", "producto", "El producto ya no existe en el catálogo."))

    if ingreso_neto > 0 and float(solicitud.monto) > u["monto_ingreso_neto_veces"] * ingreso_neto:
        alertas.append(_alerta("amarillo", "monto_alto",
                               f"El monto supera {u['monto_ingreso_neto_veces']} veces el ingreso neto mensual declarado."))

    sustento = negocios.ingreso_segun_perfil(cliente.segmento, solicitud.datos_perfil)
    if sustento is not None and float(cliente.ingresos_mensuales) > 1.5 * max(sustento, 0) + 1:
        alertas.append(_alerta("amarillo", "ingresos_perfil",
                               f"Los ingresos declarados (S/ {float(cliente.ingresos_mensuales):,.2f}) superan lo que sustenta el "
                               f"formulario del negocio (≈ S/ {sustento:,.2f} al mes)."))

    if cliente.antiguedad_meses is not None and cliente.antiguedad_meses < u["antiguedad_minima_meses"]:
        alertas.append(_alerta("amarillo", "antiguedad",
                               f"Antigüedad en la actividad de {cliente.antiguedad_meses} meses (menos de {u['antiguedad_minima_meses']})."))

    # Posibles duplicados
    otras_activas = db.scalar(select(func.count(Solicitud.id)).where(
        Solicitud.cliente_id == cliente.id, Solicitud.id != solicitud.id, Solicitud.estado.in_(ESTADOS_ACTIVOS)))
    if otras_activas:
        alertas.append(_alerta("amarillo", "duplicado_solicitud",
                               f"El cliente tiene {otras_activas} otra(s) solicitud(es) en curso: posible registro duplicado."))
    mismo_telefono = db.scalar(select(func.count(Cliente.id)).where(
        Cliente.telefono == cliente.telefono, Cliente.id != cliente.id))
    if mismo_telefono:
        alertas.append(_alerta("amarillo", "duplicado_telefono",
                               "Otro expediente usa el mismo teléfono: verificar que no sea un registro duplicado."))

    # Cambio inusual frente a la evaluación anterior
    anterior = db.scalar(select(EvaluacionRiesgo).where(EvaluacionRiesgo.solicitud_id == solicitud.id)
                         .order_by(EvaluacionRiesgo.id.desc()).limit(1))
    if anterior and anterior.indicadores.get("ingresos"):
        previo = anterior.indicadores["ingresos"]
        actual = float(cliente.ingresos_mensuales)
        if previo > 0 and abs(actual - previo) / previo > u["cambio_ingresos"]:
            alertas.append(_alerta("amarillo", "cambio_ingresos",
                                   f"Los ingresos declarados cambiaron de S/ {previo:,.2f} a S/ {actual:,.2f} desde la evaluación anterior."))
    return alertas


def guardar_evaluacion(db: Session, solicitud: Solicitud, usuario_id: int) -> EvaluacionRiesgo:
    r = evaluar(db, solicitud)
    ev = EvaluacionRiesgo(
        solicitud_id=solicitud.id, version_umbrales=r["version"], semaforo=r["semaforo"],
        indicadores=r["indicadores"], alertas=r["alertas"], creado_por=usuario_id,
    )
    db.add(ev)
    return ev


def ultima_evaluacion(solicitud: Solicitud) -> EvaluacionRiesgo | None:
    return solicitud.evaluaciones[0] if solicitud.evaluaciones else None


# ---------- Alertas de seguridad (accesos) ----------

def alertas_seguridad(db: Session, dias: int = 7) -> dict:
    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    filas = db.execute(
        select(Auditoria.accion, Auditoria.email, func.count(Auditoria.id), func.max(Auditoria.creado_en))
        .where(Auditoria.accion.in_(("login_fallido", "login_bloqueado", "acceso_denegado")), Auditoria.creado_en >= desde)
        .group_by(Auditoria.accion, Auditoria.email)
        .order_by(func.count(Auditoria.id).desc())
    ).all()
    return {"dias": dias, "filas": [{"accion": a, "email": e, "cantidad": n, "ultimo": u} for a, e, n, u in filas]}
