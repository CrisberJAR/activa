"""Negocios: productos de demostración, formularios por tipo de cliente, documentos y estados de solicitudes."""
from decimal import Decimal

from app.config import cargar_yaml
from app.models import Cliente, Solicitud, Usuario

# ---------- Productos (config/productos.yaml) ----------


def catalogo() -> dict:
    return cargar_yaml("productos")


def productos() -> dict:
    return catalogo()["productos"]


def productos_para(segmento: str) -> dict:
    return {k: p for k, p in productos().items() if segmento in p["segmentos"]}


def documentos_requeridos(segmento: str) -> list[str]:
    cat = catalogo()
    return list(cat["documentos_base"]) + list(cat["documentos_por_segmento"].get(segmento, []))


# ---------- Formulario dinámico según el tipo de cliente ----------
# tipo: "numero" (monto en soles o cantidad) o "texto"

CAMPOS_PERFIL = {
    "comerciante": [
        {"campo": "giro", "etiqueta": "Giro del negocio (qué vende)", "tipo": "texto", "requerido": True},
        {"campo": "ventas_mensuales", "etiqueta": "Ventas mensuales (S/)", "tipo": "numero", "requerido": True},
        {"campo": "costo_ventas", "etiqueta": "Costo de la mercadería al mes (S/)", "tipo": "numero", "requerido": True},
    ],
    "emprendedor": [
        {"campo": "etapa", "etiqueta": "Etapa del emprendimiento (idea, inicio, crecimiento)", "tipo": "texto", "requerido": True},
        {"campo": "ventas_mensuales", "etiqueta": "Ventas mensuales actuales (S/)", "tipo": "numero", "requerido": True},
        {"campo": "costo_ventas", "etiqueta": "Costos mensuales del negocio (S/)", "tipo": "numero", "requerido": True},
    ],
    "independiente": [
        {"campo": "servicio", "etiqueta": "Servicio u oficio que ofrece", "tipo": "texto", "requerido": True},
        {"campo": "ingreso_mes_bajo", "etiqueta": "Ingreso en un mes bajo (S/)", "tipo": "numero", "requerido": True},
        {"campo": "ingreso_mes_alto", "etiqueta": "Ingreso en un mes alto (S/)", "tipo": "numero", "requerido": True},
    ],
    "dependiente": [
        {"campo": "empleador", "etiqueta": "Empleador", "tipo": "texto", "requerido": True},
        {"campo": "sueldo_neto", "etiqueta": "Sueldo neto mensual (S/)", "tipo": "numero", "requerido": True},
        {"campo": "descuentos_planilla", "etiqueta": "Descuentos por planilla al mes (S/)", "tipo": "numero", "requerido": False},
    ],
    "agricultor": [
        {"campo": "cultivo", "etiqueta": "Cultivo o crianza principal", "tipo": "texto", "requerido": True},
        {"campo": "ingreso_por_campana", "etiqueta": "Ingreso neto por campaña (S/)", "tipo": "numero", "requerido": True},
        {"campo": "campanas_por_anio", "etiqueta": "Campañas por año", "tipo": "numero", "requerido": True},
    ],
    "transportista": [
        {"campo": "tipo_vehiculo", "etiqueta": "Tipo de vehículo (mototaxi, taxi, carga…)", "tipo": "texto", "requerido": True},
        {"campo": "ingreso_diario", "etiqueta": "Ingreso neto por día (S/)", "tipo": "numero", "requerido": True},
        {"campo": "dias_trabajo_mes", "etiqueta": "Días de trabajo al mes", "tipo": "numero", "requerido": True},
    ],
    "persona_natural": [
        {"campo": "fuente_ingresos", "etiqueta": "Fuente de sus ingresos", "tipo": "texto", "requerido": True},
        {"campo": "capacidad_pago_declarada", "etiqueta": "Cuánto podría pagar al mes (S/)", "tipo": "numero", "requerido": True},
    ],
}


def validar_perfil(segmento: str, form: dict) -> tuple[dict, dict]:
    """Lee los campos del perfil del formulario. Devuelve (datos, errores)."""
    datos, errores = {}, {}
    for c in CAMPOS_PERFIL.get(segmento, []):
        valor = str(form.get(f"perfil_{c['campo']}", "")).strip()
        if not valor:
            if c["requerido"]:
                errores[f"perfil_{c['campo']}"] = "Este campo es obligatorio"
            continue
        if c["tipo"] == "numero":
            try:
                numero = float(valor.replace(",", "."))
            except ValueError:
                errores[f"perfil_{c['campo']}"] = "Debe ser un número"
                continue
            if numero < 0 or numero > 10_000_000:
                errores[f"perfil_{c['campo']}"] = "Valor fuera de rango"
                continue
            datos[c["campo"]] = numero
        else:
            datos[c["campo"]] = valor[:200]
    return datos, errores


def ingreso_segun_perfil(segmento: str, perfil: dict) -> float | None:
    """Ingreso mensual que sustenta el perfil (para detectar montos inconsistentes)."""
    p = perfil or {}
    try:
        if segmento in ("comerciante", "emprendedor"):
            return p["ventas_mensuales"] - p["costo_ventas"]
        if segmento == "independiente":
            return (p["ingreso_mes_bajo"] + p["ingreso_mes_alto"]) / 2
        if segmento == "dependiente":
            return p["sueldo_neto"] - p.get("descuentos_planilla", 0)
        if segmento == "agricultor":
            return p["ingreso_por_campana"] * p["campanas_por_anio"] / 12
        if segmento == "transportista":
            return p["ingreso_diario"] * p["dias_trabajo_mes"]
    except (KeyError, TypeError):
        return None
    return None


def validar_condiciones(producto: str, segmento: str, monto: Decimal, plazo: int, frecuencia: str) -> dict:
    """Reglas del producto de demostración. Devuelve {campo: error}."""
    errores = {}
    p = productos().get(producto)
    if not p:
        return {"producto": "Elige un producto del catálogo"}
    if segmento not in p["segmentos"]:
        errores["producto"] = "Este producto no está disponible para el tipo de cliente"
    if not p["monto_min"] <= float(monto) <= p["monto_max"]:
        errores["monto"] = f"El monto debe estar entre S/ {p['monto_min']:,} y S/ {p['monto_max']:,}"
    if not p["plazo_min"] <= plazo <= p["plazo_max"]:
        errores["plazo_meses"] = f"El plazo debe estar entre {p['plazo_min']} y {p['plazo_max']} meses"
    if frecuencia not in p["frecuencias"]:
        errores["frecuencia"] = "Frecuencia no disponible para este producto"
    return errores


# ---------- Permisos sobre expedientes ----------

def puede_ver_cliente(usuario: Usuario, cliente: Cliente) -> bool:
    """Asesor: solo sus expedientes. Gerente: todos. Analista: los que tienen solicitudes enviadas a evaluación."""
    if usuario.rol == "gerente":
        return True
    if usuario.rol == "asesor":
        return cliente.asesor_id == usuario.id
    if usuario.rol == "analista_riesgos":
        return any(s.estado != "borrador" for s in cliente.solicitudes)
    return False


def puede_editar_cliente(usuario: Usuario, cliente: Cliente) -> bool:
    return usuario.rol == "gerente" or (usuario.rol == "asesor" and cliente.asesor_id == usuario.id)


# ---------- Estados de la solicitud ----------

ESTADOS_TEXTO = {
    "borrador": "Borrador",
    "enviada": "Enviada a evaluación",
    "en_evaluacion": "En evaluación",
    "observada": "Observada",
    "evaluada": "Evaluada (espera decisión)",
    "aprobada": "Aprobada",
    "denegada": "Denegada",
    "desistida": "Desistida",
}
ESTADOS_COLOR = {
    "borrador": "secondary", "enviada": "info", "en_evaluacion": "primary", "observada": "warning",
    "evaluada": "dark", "aprobada": "success", "denegada": "danger", "desistida": "secondary",
}

# acción → (estados desde los que se puede, estado nuevo, roles, ¿solo el asesor dueño?, ¿comentario obligatorio?)
ACCIONES = {
    "enviar": (("borrador", "observada"), "enviada", ("asesor", "gerente"), True, False),
    "tomar": (("enviada",), "en_evaluacion", ("analista_riesgos", "gerente"), False, False),
    "observar": (("enviada", "en_evaluacion", "evaluada"), "observada", ("analista_riesgos", "gerente"), False, True),
    "evaluar": (("en_evaluacion",), "evaluada", ("analista_riesgos", "gerente"), False, True),
    "aprobar": (("evaluada",), "aprobada", ("gerente",), False, True),
    "denegar": (("evaluada",), "denegada", ("gerente",), False, True),
    "desistir": (("borrador", "enviada", "observada"), "desistida", ("asesor", "gerente"), True, True),
}
ACCIONES_TEXTO = {
    "enviar": "Enviar a evaluación de riesgos",
    "tomar": "Tomar para evaluación",
    "observar": "Observar (pedir información)",
    "evaluar": "Cerrar evaluación",
    "aprobar": "Aprobar (decisión humana)",
    "denegar": "Denegar (decisión humana)",
    "desistir": "Registrar desistimiento",
}


def acciones_permitidas(usuario: Usuario, s: Solicitud) -> list[str]:
    salida = []
    for accion, (desde, _, roles, solo_duenio, _) in ACCIONES.items():
        if s.estado not in desde or usuario.rol not in roles:
            continue
        if solo_duenio and usuario.rol == "asesor" and s.asesor_id != usuario.id:
            continue
        salida.append(accion)
    return salida


def editable(usuario: Usuario, s: Solicitud) -> bool:
    if s.estado not in ("borrador", "observada"):
        return False
    return usuario.rol == "gerente" or (usuario.rol == "asesor" and s.asesor_id == usuario.id)


def puede_ver_solicitud(usuario: Usuario, s: Solicitud) -> bool:
    if usuario.rol == "gerente":
        return True
    if usuario.rol == "asesor":
        return s.asesor_id == usuario.id
    if usuario.rol == "analista_riesgos":
        return s.estado != "borrador"
    return False
