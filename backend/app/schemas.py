"""Validaciones del servidor (Pydantic). Los mensajes de error se muestran en español."""
import re
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, field_validator

from app.catalogos import CATALOGOS

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


def errores_es(exc: ValidationError) -> dict[str, str]:
    """Convierte los errores de Pydantic en {campo: mensaje en español}."""
    errores = {}
    for err in exc.errors():
        campo = str(err["loc"][0]) if err["loc"] else "__all__"
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
