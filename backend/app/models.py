"""Tablas de la base de datos (SQLAlchemy 2).

Cualquier cambio aquí requiere una nueva migración:
    alembic revision --autogenerate -m "descripcion"
    alembic upgrade head
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

ROLES = ("asesor", "gerente")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    rol: Mapped[str] = mapped_column(String(20))  # asesor | gerente
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Bloque(Base):
    """Agrupa encuestas tomadas en un mismo periodo o campaña de campo."""

    __tablename__ = "bloques"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    descripcion: Mapped[str | None] = mapped_column(Text)
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date | None] = mapped_column(Date)
    # Abierto para registrar encuestas; puede haber varios abiertos a la vez
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    encuestas: Mapped[list["Encuesta"]] = relationship(back_populates="bloque")


class Encuesta(Base):
    __tablename__ = "encuestas"

    id: Mapped[int] = mapped_column(primary_key=True)
    bloque_id: Mapped[int] = mapped_column(ForeignKey("bloques.id"), index=True)
    asesor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    nombre: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str] = mapped_column(String(20))
    zona: Mapped[str] = mapped_column(String(80))
    sector: Mapped[str] = mapped_column(String(40))  # agricola | comerciante | ambulante | taxista
    ingreso_mensual: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    anios_negocio: Mapped[int] = mapped_column(Integer)
    trabajadores: Mapped[int] = mapped_column(Integer)
    frecuencia_ingresos: Mapped[str] = mapped_column(String(20))
    credito_vigente: Mapped[bool] = mapped_column(Boolean)
    garantia: Mapped[str] = mapped_column(String(80))
    necesidad: Mapped[str] = mapped_column(Text)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    plazo_meses: Mapped[int] = mapped_column(Integer)
    temporada_necesidad: Mapped[str] = mapped_column(String(20))
    riesgo_principal: Mapped[str] = mapped_column(String(80))
    interes_campana: Mapped[bool] = mapped_column(Boolean)
    contacto_preferido: Mapped[str] = mapped_column(String(20))
    consentimiento: Mapped[bool] = mapped_column(Boolean)  # Ley 29733, obligatorio
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    bloque: Mapped[Bloque] = relationship(back_populates="encuestas")
    asesor: Mapped[Usuario] = relationship()


class Sensor(Base):
    __tablename__ = "sensores"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)  # identificador usado en Firebase
    sector: Mapped[str] = mapped_column(String(40))
    ubicacion: Mapped[str | None] = mapped_column(String(120))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class RegistroDiario(Base):
    """Promedio diario de las lecturas de un sensor."""

    __tablename__ = "registros_diarios"
    __table_args__ = (UniqueConstraint("sensor_id", "fecha"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensores.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    temp_promedio: Mapped[float] = mapped_column(Float)
    temp_min: Mapped[float] = mapped_column(Float)
    temp_max: Mapped[float] = mapped_column(Float)
    humedad_promedio: Mapped[float] = mapped_column(Float)
    humedad_min: Mapped[float] = mapped_column(Float)
    humedad_max: Mapped[float] = mapped_column(Float)
    n_lecturas: Mapped[int] = mapped_column(Integer)


class Diagnostico(Base):
    """Resultado del análisis estacional en una fecha."""

    __tablename__ = "diagnosticos"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    periodo_dias: Mapped[int] = mapped_column(Integer)  # 7 o 28
    estacion_actual: Mapped[str] = mapped_column(String(20))
    temporada_proxima: Mapped[str | None] = mapped_column(String(20))
    cambio_humedad: Mapped[float | None] = mapped_column(Float)
    cambio_temperatura: Mapped[float | None] = mapped_column(Float)
    alerta: Mapped[bool] = mapped_column(Boolean, default=False)
    mensaje: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Campana(Base):
    __tablename__ = "campanas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    temporada: Mapped[str] = mapped_column(String(20))
    tipo_campana: Mapped[str | None] = mapped_column(String(40))  # clave de config/tipos_campana.yaml
    bloque_id: Mapped[int | None] = mapped_column(ForeignKey("bloques.id"))  # bloque que la originó
    entradas: Mapped[dict] = mapped_column(JSON)    # datos ingresados por el asesor
    contenido: Mapped[dict] = mapped_column(JSON)   # las cinco secciones generadas por la IA
    generado_con: Mapped[str | None] = mapped_column(String(60))  # modelo de Gemini o "plantilla"
    estado: Mapped[str] = mapped_column(String(20), default="borrador")  # borrador | publicada | retirada
    vigente_desde: Mapped[date | None] = mapped_column(Date)
    vigente_hasta: Mapped[date | None] = mapped_column(Date)
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    publicado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    publicado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bloque: Mapped[Bloque | None] = relationship()
    autor: Mapped[Usuario] = relationship(foreign_keys=[creado_por])


class Interesado(Base):
    """Cliente captado por el chatbot."""

    __tablename__ = "interesados"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str] = mapped_column(String(20))
    sector: Mapped[str | None] = mapped_column(String(40))
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"))
    conversacion_id: Mapped[str | None] = mapped_column(String(64))
    atendido: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalisisBloque(Base):
    __tablename__ = "analisis_bloque"

    id: Mapped[int] = mapped_column(primary_key=True)
    bloque_id: Mapped[int] = mapped_column(ForeignKey("bloques.id"), index=True)
    indicadores: Mapped[dict] = mapped_column(JSON)
    ranking_necesidades: Mapped[list] = mapped_column(JSON)
    texto_patron: Mapped[str | None] = mapped_column(Text)
    tipo_campana_sugerida: Mapped[str | None] = mapped_column(String(60))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
