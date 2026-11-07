"""Validaciones del servidor (Pydantic). Los mensajes de error se muestran en español."""
import re
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, field_validator

from app.catalogos import CATALOGOS, TIPOS_CLIENTE

MENSAJES = {
    "missing": "Este campo es obligatorio",
    "string_too_short": "Debe tener al menos {min_length} caracteres",
    "string_too_long": "Debe tener como máximo {max_length} caracteres",
    "greater_than": "Debe ser mayor que {gt}",
    "greater_than_equal": "Debe ser mayor o igual a {ge}",
    "less_than_equal": "Debe ser menor o igual a {le}",
    "int_parsing": "Debe ser un número entero",
    "decimal_parsing": "Debe ser un número",
    "decimal_max_places": "Máximo {decimal_places} decimales",
    "date_from_datetime_parsing": "Fecha inválida",
    "date_parsing": "Fecha inválida",
    "bool_parsing": "Elige una opción",
}


def errores_es(exc: ValidationError, anidado: bool = False) -> dict[str, str]:
    """Convierte los errores de Pydantic en {campo: mensaje en español}.

    Con anidado=True usa el campo interno (p. ej. marketing.gancho → "gancho").
    """
    errores = {}
    for err in exc.errors():
        loc = [str(x) for x in err["loc"] if not isinstance(x, int)]  # sin posiciones de listas
        if not loc:
            campo = "__all__"
        elif anidado and len(loc) >= 2:
            campo = loc[1]  # capacitacion.objeciones.respuesta → "objeciones"
        else:
            campo = loc[0]
        if err["type"] == "value_error":
            mensaje = str(err["ctx"]["error"])
        else:
            mensaje = MENSAJES.get(err["type"], "Valor inválido").format(**err.get("ctx", {}))
        errores.setdefault(campo, mensaje)
    return errores


def _vacio_a_none(v):
    return None if v == "" else v


class BloqueEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=3, max_length=120)
    descripcion: str | None = Field(default=None, max_length=1000)
    fecha_inicio: date
    fecha_fin: date | None = None

    _vacios = field_validator("descripcion", "fecha_fin", mode="before")(_vacio_a_none)

    @field_validator("fecha_fin")
    @classmethod
    def fin_despues_de_inicio(cls, v: date | None, info: ValidationInfo):
        inicio = info.data.get("fecha_inicio")
        if v and inicio and v < inicio:
            raise ValueError("La fecha de fin no puede ser anterior a la de inicio")
        return v


class EncuestaEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    bloque_id: int
    nombre: str = Field(min_length=3, max_length=120)
    telefono: str
    zona: str = Field(min_length=2, max_length=80)
    sector: str
    ingreso_mensual: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)
    anios_negocio: int = Field(ge=0, le=80)
    trabajadores: int = Field(ge=0, le=500)
    frecuencia_ingresos: str
    credito_vigente: bool
    garantia: str
    necesidad: str = Field(min_length=5, max_length=1000)
    monto: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)
    plazo_meses: int = Field(ge=1, le=60)
    temporada_necesidad: str
    riesgo_principal: str
    interes_campana: bool
    contacto_preferido: str
    consentimiento: bool

    @field_validator("telefono")
    @classmethod
    def telefono_peruano(cls, v: str) -> str:
        v = re.sub(r"\s", "", v)
        if not re.fullmatch(r"9\d{8}", v):
            raise ValueError("Debe tener 9 dígitos y empezar con 9")
        return v

    @field_validator(*CATALOGOS)
    @classmethod
    def en_catalogo(cls, v: str, info: ValidationInfo) -> str:
        if v not in CATALOGOS[info.field_name]:
            raise ValueError("Elige una opción de la lista")
        return v

    @field_validator("consentimiento")
    @classmethod
    def consentimiento_obligatorio(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Sin el consentimiento del cliente (Ley 29733) la encuesta no se puede guardar")
        return v


CAMPOS_ENCUESTA = list(EncuestaEntrada.model_fields)


# ---------- Campañas (Fase 5c) ----------

class CampanaEntrada(BaseModel):
    """Datos que el asesor ingresa para generar una campaña."""

    model_config = ConfigDict(str_strip_whitespace=True)

    bloque_id: int | None = None
    tipo_campana: str
    temporada: str
    publico_objetivo: str = Field(min_length=5, max_length=300)
    necesidad: str = Field(min_length=5, max_length=500)  # riesgo o necesidad que atiende
    monto_maximo: Decimal | None = Field(default=None, gt=0, le=200_000, decimal_places=2)
    plazo_meses: int = Field(ge=1, le=60)
    zona: str = Field(min_length=2, max_length=200)
    tipo_cliente: str
    periodo_gracia_meses: int = Field(ge=0, le=6)
    fecha_inicio: date
    duracion_semanas: int = Field(ge=1, le=26)
    presupuesto_difusion: Decimal = Field(ge=0, le=100_000, decimal_places=2)
    meta_creditos: int = Field(ge=1, le=10_000)
    # ACTIVA 360°: segmentación opcional de la campaña
    segmento: str | None = None
    region: str | None = None
    producto: str | None = None

    _vacios = field_validator("bloque_id", "monto_maximo", "segmento", "region", "producto", mode="before")(_vacio_a_none)

    @field_validator("segmento")
    @classmethod
    def segmento_valido(cls, v):
        from app.catalogos import SEGMENTOS
        if v is not None and v not in SEGMENTOS:
            raise ValueError("Elige un segmento de la lista")
        return v

    @field_validator("region")
    @classmethod
    def region_valida(cls, v):
        from app.catalogos import REGIONES
        if v is not None and v not in REGIONES:
            raise ValueError("Elige una región de la lista")
        return v

    @field_validator("producto")
    @classmethod
    def producto_valido(cls, v):
        from app.services.negocios import productos
        if v is not None and v not in productos():
            raise ValueError("Elige un producto del catálogo")
        return v

    @field_validator("tipo_campana")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        from app.config import cargar_tipos_campana

        if v not in cargar_tipos_campana():
            raise ValueError("Elige un tipo de campaña de la lista")
        return v

    @field_validator("temporada")
    @classmethod
    def temporada_valida(cls, v: str) -> str:
        if v not in CATALOGOS["temporada_necesidad"]:
            raise ValueError("Elige una temporada de la lista")
        return v

    @field_validator("tipo_cliente")
    @classmethod
    def tipo_cliente_valido(cls, v: str) -> str:
        if v not in TIPOS_CLIENTE:
            raise ValueError("Elige una opción de la lista")
        return v


class Objecion(BaseModel):
    objecion: str = Field(min_length=3, max_length=300)
    respuesta: str = Field(min_length=3, max_length=800)


class Capacitacion(BaseModel):
    speech: str = Field(min_length=30, max_length=2000)
    objeciones: list[Objecion] = Field(min_length=1, max_length=8)


class Marketing(BaseModel):
    canales: list[str] = Field(min_length=1, max_length=8)
    gancho: str = Field(min_length=5, max_length=300)
    mensaje_whatsapp: str = Field(min_length=20, max_length=1000)


class CampanaContenido(BaseModel):
    """Las cinco secciones de una campaña (lo que genera la IA y edita el gerente)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=5, max_length=120)
    propuesta_valor: str = Field(min_length=20, max_length=1000)
    decisiones_gerencia: list[str] = Field(min_length=1, max_length=10)
    capacitacion: Capacitacion
    marketing: Marketing

    @field_validator("decisiones_gerencia")
    @classmethod
    def sin_vacios(cls, v: list[str]) -> list[str]:
        v = [x.strip() for x in v if x and x.strip()]
        if not v:
            raise ValueError("Escribe al menos una decisión")
        return v


# =====================================================================
# ACTIVA 360°
# =====================================================================

def _en_catalogo(catalogo: dict, mensaje: str = "Elige una opción de la lista"):
    def validar(cls, v):
        if v not in catalogo:
            raise ValueError(mensaje)
        return v
    return validar


def _telefono_peru(v: str) -> str:
    v = re.sub(r"[\s-]", "", v or "")
    if not re.fullmatch(r"9\d{8}", v):
        raise ValueError("Celular peruano de 9 dígitos que empieza con 9")
    return v


def _dni(v: str | None) -> str | None:
    if v in (None, ""):
        return None
    v = v.strip()
    if not re.fullmatch(r"\d{8}", v):
        raise ValueError("El DNI tiene 8 dígitos")
    return v


def _vacio_a_cero(v):
    return "0" if v in (None, "") else v


def _consentimiento(v) -> bool:
    if v not in (True, "on", "true", "1", 1):
        raise ValueError("Sin consentimiento no se pueden registrar los datos (Ley 29733)")
    return True


class ProspectoEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=3, max_length=120)
    telefono: str
    dni: str | None = None
    segmento: str
    actividad: str = Field(min_length=3, max_length=120)
    necesidad: str = Field(min_length=5, max_length=1000)
    region: str
    ubicacion: str | None = Field(default=None, max_length=120)
    monto_solicitado: Decimal | None = Field(default=None, gt=0, le=500_000, decimal_places=2)
    contacto_preferido: str
    campana_id: int | None = None
    asesor_id: int | None = None
    proxima_accion: date | None = None
    consentimiento: bool

    _vacios = field_validator("ubicacion", "monto_solicitado", "campana_id", "asesor_id", "proxima_accion", mode="before")(_vacio_a_none)
    _tel = field_validator("telefono")(_telefono_peru)
    _doc = field_validator("dni", mode="before")(_dni)
    _cons = field_validator("consentimiento", mode="before")(_consentimiento)

    @field_validator("segmento")
    @classmethod
    def segmento_valido(cls, v):
        from app.catalogos import SEGMENTOS
        return _en_catalogo(SEGMENTOS)(cls, v)

    @field_validator("region")
    @classmethod
    def region_valida(cls, v):
        from app.catalogos import REGIONES
        return _en_catalogo(REGIONES)(cls, v)

    @field_validator("contacto_preferido")
    @classmethod
    def contacto_valido(cls, v):
        from app.catalogos import CANALES
        return _en_catalogo(CANALES)(cls, v)


class ContactoEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    canal: str
    resultado: str = Field(min_length=3, max_length=1000)
    estado_nuevo: str
    proxima_accion: date | None = None

    _vacios = field_validator("proxima_accion", mode="before")(_vacio_a_none)

    @field_validator("canal")
    @classmethod
    def canal_valido(cls, v):
        from app.catalogos import CANALES
        return _en_catalogo(CANALES)(cls, v)

    @field_validator("estado_nuevo")
    @classmethod
    def estado_valido(cls, v):
        from app.models import ESTADOS_PROSPECTO
        if v not in ESTADOS_PROSPECTO:
            raise ValueError("Elige un estado del embudo")
        return v


class ClienteEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    dni: str
    nombres: str = Field(min_length=3, max_length=120)
    telefono: str
    email: str | None = Field(default=None, max_length=160)
    segmento: str
    ocupacion: str = Field(min_length=3, max_length=120)
    region: str
    ubicacion: str | None = Field(default=None, max_length=120)
    ingresos_mensuales: Decimal = Field(ge=0, le=1_000_000, decimal_places=2)
    gastos_mensuales: Decimal = Field(ge=0, le=1_000_000, decimal_places=2)
    antiguedad_meses: int = Field(ge=0, le=720)
    cuotas_otras_deudas: Decimal = Field(default=Decimal("0"), ge=0, le=1_000_000, decimal_places=2)
    saldo_otras_deudas: Decimal = Field(default=Decimal("0"), ge=0, le=10_000_000, decimal_places=2)
    necesidades: str | None = Field(default=None, max_length=1000)
    consentimiento: bool

    _vacios = field_validator("email", "ubicacion", "necesidades", mode="before")(_vacio_a_none)
    _ceros = field_validator("cuotas_otras_deudas", "saldo_otras_deudas", mode="before")(_vacio_a_cero)
    _tel = field_validator("telefono")(_telefono_peru)
    _cons = field_validator("consentimiento", mode="before")(_consentimiento)

    @field_validator("dni", mode="before")
    @classmethod
    def dni_obligatorio(cls, v):
        if v in (None, ""):
            raise ValueError("Este campo es obligatorio")
        return _dni(v)

    @field_validator("email")
    @classmethod
    def email_valido(cls, v):
        if v and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("Correo inválido")
        return v

    @field_validator("segmento")
    @classmethod
    def segmento_valido(cls, v):
        from app.catalogos import SEGMENTOS
        return _en_catalogo(SEGMENTOS)(cls, v)

    @field_validator("region")
    @classmethod
    def region_valida(cls, v):
        from app.catalogos import REGIONES
        return _en_catalogo(REGIONES)(cls, v)


class SolicitudEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    producto: str
    monto: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)
    plazo_meses: int = Field(ge=1, le=120)
    frecuencia: str
    destino: str = Field(min_length=5, max_length=1000)
    campana_id: int | None = None

    _vacios = field_validator("campana_id", mode="before")(_vacio_a_none)

    @field_validator("frecuencia")
    @classmethod
    def frecuencia_valida(cls, v):
        from app.services.simulador import FRECUENCIAS
        return _en_catalogo(FRECUENCIAS)(cls, v)


class SimulacionEntrada(BaseModel):
    monto: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)
    tea: float = Field(ge=0, le=300)
    plazo_meses: int = Field(ge=1, le=120)
    frecuencia: str
    fecha_inicio: date | None = None

    _vacios = field_validator("fecha_inicio", mode="before")(_vacio_a_none)

    @field_validator("frecuencia")
    @classmethod
    def frecuencia_valida(cls, v):
        from app.services.simulador import FRECUENCIAS
        return _en_catalogo(FRECUENCIAS)(cls, v)


class CreditoEntrada(BaseModel):
    """Registro de un crédito ya desembolsado por la entidad (solo para seguimiento)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    cliente_id: int
    solicitud_id: int | None = None
    producto: str
    monto: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)
    tea: Decimal = Field(ge=0, le=300, decimal_places=3)
    plazo_meses: int = Field(ge=1, le=120)
    frecuencia: str
    fecha_desembolso: date
    gestor_id: int | None = None

    _vacios = field_validator("solicitud_id", "gestor_id", mode="before")(_vacio_a_none)

    @field_validator("frecuencia")
    @classmethod
    def frecuencia_valida(cls, v):
        from app.services.simulador import FRECUENCIAS
        return _en_catalogo(FRECUENCIAS)(cls, v)

    @field_validator("fecha_desembolso")
    @classmethod
    def no_futura(cls, v):
        from app.config import hoy_peru
        if v > hoy_peru():
            raise ValueError("La fecha de desembolso no puede ser futura")
        return v
