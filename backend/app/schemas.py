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

    _vacios = field_validator("bloque_id", "monto_maximo", mode="before")(_vacio_a_none)

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
