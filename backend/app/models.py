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
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

ROLES = ("asesor", "gerente", "analista_riesgos", "gestor_recuperaciones")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    rol: Mapped[str] = mapped_column(String(30))  # asesor | gerente | analista_riesgos | gestor_recuperaciones
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


class Conversacion(Base):
    """Chat de un visitante con el asesor virtual (sus mensajes y en qué paso va)."""

    __tablename__ = "conversaciones"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # código aleatorio (uuid4 hex)
    estado: Mapped[str] = mapped_column(String(20), default="oficio")
    sector: Mapped[str | None] = mapped_column(String(40))
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"))
    datos: Mapped[dict] = mapped_column(JSON, default=dict)      # nombre mientras se capturan los datos
    mensajes: Mapped[list] = mapped_column(JSON, default=list)   # [{rol: bot|cliente, texto, hora}]
    n_mensajes: Mapped[int] = mapped_column(Integer, default=0)  # mensajes del cliente (para el límite)
    ip_hash: Mapped[str] = mapped_column(String(64), index=True)  # IP cifrada (no se guarda la IP real)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    campana: Mapped["Campana | None"] = relationship()


class Interesado(Base):
    """Cliente captado por el chatbot."""

    __tablename__ = "interesados"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str] = mapped_column(String(20))
    sector: Mapped[str | None] = mapped_column(String(40))
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"))
    conversacion_id: Mapped[str | None] = mapped_column(String(64))
    consentimiento: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())  # Ley 29733
    atendido: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campana: Mapped["Campana | None"] = relationship()


class AnalisisBloque(Base):
    __tablename__ = "analisis_bloque"

    id: Mapped[int] = mapped_column(primary_key=True)
    bloque_id: Mapped[int] = mapped_column(ForeignKey("bloques.id"), index=True)
    indicadores: Mapped[dict] = mapped_column(JSON)
    ranking_necesidades: Mapped[list] = mapped_column(JSON)
    texto_patron: Mapped[str | None] = mapped_column(Text)
    tipo_campana_sugerida: Mapped[str | None] = mapped_column(String(60))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Auditoria(Base):
    """Registro de acciones importantes: quién hizo qué y cuándo (sin datos personales de clientes)."""

    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    email: Mapped[str | None] = mapped_column(String(160), index=True)  # correo usado al iniciar sesión
    accion: Mapped[str] = mapped_column(String(40), index=True)  # login_ok, campana_publicada…
    detalle: Mapped[str | None] = mapped_column(Text)  # solo identificadores, nunca nombres ni teléfonos
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    usuario: Mapped["Usuario | None"] = relationship()


# =====================================================================
# ACTIVA 360° · Módulo COMERCIAL (Fase 9)
# =====================================================================

ESTADOS_PROSPECTO = ("nuevo", "contactado", "interesado", "solicitud", "evaluacion", "convertido", "no_convertido")


class Prospecto(Base):
    """Cliente potencial y su avance en el embudo comercial."""

    __tablename__ = "prospectos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str] = mapped_column(String(20))
    dni: Mapped[str | None] = mapped_column(String(8), index=True)
    segmento: Mapped[str] = mapped_column(String(30))  # clave de catalogos.SEGMENTOS
    actividad: Mapped[str] = mapped_column(String(120))  # actividad económica u ocupación
    necesidad: Mapped[str] = mapped_column(Text)
    region: Mapped[str] = mapped_column(String(30))  # clave de catalogos.REGIONES
    ubicacion: Mapped[str | None] = mapped_column(String(120))  # provincia o distrito (ubicación general)
    monto_solicitado: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    contacto_preferido: Mapped[str] = mapped_column(String(20))
    consentimiento: Mapped[bool] = mapped_column(Boolean)  # Ley 29733, obligatorio
    estado: Mapped[str] = mapped_column(String(20), default="nuevo", index=True)
    origen: Mapped[str] = mapped_column(String(20), default="manual")  # manual | chatbot
    asesor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)  # asesor asignado
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"), index=True)
    interesado_id: Mapped[int | None] = mapped_column(ForeignKey("interesados.id"))
    proxima_accion: Mapped[date | None] = mapped_column(Date)  # fecha de la siguiente actividad
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    asesor: Mapped["Usuario | None"] = relationship(foreign_keys=[asesor_id])
    campana: Mapped["Campana | None"] = relationship()
    contactos: Mapped[list["ContactoProspecto"]] = relationship(
        back_populates="prospecto", order_by="ContactoProspecto.id.desc()", cascade="all, delete-orphan"
    )


class ContactoProspecto(Base):
    """Cada contacto con un prospecto: fecha, canal y resultado."""

    __tablename__ = "contactos_prospecto"

    id: Mapped[int] = mapped_column(primary_key=True)
    prospecto_id: Mapped[int] = mapped_column(ForeignKey("prospectos.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    canal: Mapped[str] = mapped_column(String(20))
    resultado: Mapped[str] = mapped_column(Text)
    estado_nuevo: Mapped[str] = mapped_column(String(20))
    proxima_accion: Mapped[date | None] = mapped_column(Date)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    prospecto: Mapped[Prospecto] = relationship(back_populates="contactos")
    usuario: Mapped[Usuario] = relationship()


# =====================================================================
# ACTIVA 360° · Módulo de NEGOCIOS (Fase 10)
# =====================================================================

ESTADOS_SOLICITUD = ("borrador", "enviada", "en_evaluacion", "observada", "evaluada", "aprobada", "denegada", "desistida")


class Cliente(Base):
    """Expediente financiero del cliente (datos declarados, con consentimiento)."""

    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    dni: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    nombres: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str] = mapped_column(String(20), index=True)
    email: Mapped[str | None] = mapped_column(String(160))
    segmento: Mapped[str] = mapped_column(String(30))
    ocupacion: Mapped[str] = mapped_column(String(120))
    region: Mapped[str] = mapped_column(String(30))
    ubicacion: Mapped[str | None] = mapped_column(String(120))
    ingresos_mensuales: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    gastos_mensuales: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    antiguedad_meses: Mapped[int] = mapped_column(Integer)  # antigüedad en la actividad o empleo
    cuotas_otras_deudas: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)  # pago mensual declarado
    saldo_otras_deudas: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    necesidades: Mapped[str | None] = mapped_column(Text)
    consentimiento: Mapped[bool] = mapped_column(Boolean)  # Ley 29733
    prospecto_id: Mapped[int | None] = mapped_column(ForeignKey("prospectos.id"))
    asesor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)  # responsable del expediente
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    asesor: Mapped[Usuario] = relationship(foreign_keys=[asesor_id])
    solicitudes: Mapped[list["Solicitud"]] = relationship(back_populates="cliente", order_by="Solicitud.id.desc()")


class Solicitud(Base):
    """Solicitud de crédito digital (no hay desembolsos ni movimientos de dinero)."""

    __tablename__ = "solicitudes"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    asesor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    producto: Mapped[str] = mapped_column(String(40))  # clave de config/productos.yaml
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    plazo_meses: Mapped[int] = mapped_column(Integer)
    frecuencia: Mapped[str] = mapped_column(String(20))  # mensual | quincenal | semanal
    destino: Mapped[str] = mapped_column(Text)
    datos_perfil: Mapped[dict] = mapped_column(JSON, default=dict)  # campos según el tipo de cliente
    estado: Mapped[str] = mapped_column(String(20), default="borrador", index=True)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    cliente: Mapped[Cliente] = relationship(back_populates="solicitudes")
    asesor: Mapped[Usuario] = relationship()
    campana: Mapped["Campana | None"] = relationship()
    documentos: Mapped[list["DocumentoSolicitud"]] = relationship(
        back_populates="solicitud", order_by="DocumentoSolicitud.id", cascade="all, delete-orphan"
    )
    movimientos: Mapped[list["MovimientoSolicitud"]] = relationship(
        back_populates="solicitud", order_by="MovimientoSolicitud.id.desc()", cascade="all, delete-orphan"
    )
    evaluaciones: Mapped[list["EvaluacionRiesgo"]] = relationship(
        back_populates="solicitud", order_by="EvaluacionRiesgo.id.desc()", cascade="all, delete-orphan"
    )


class DocumentoSolicitud(Base):
    """Lista de control de documentos (no se suben archivos: se registra su revisión)."""

    __tablename__ = "documentos_solicitud"

    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(40))
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")  # pendiente | recibido | validado | observado
    observacion: Mapped[str | None] = mapped_column(Text)
    revisado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    revisado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    solicitud: Mapped[Solicitud] = relationship(back_populates="documentos")
    revisor: Mapped["Usuario | None"] = relationship()


class MovimientoSolicitud(Base):
    """Historial de estados y observaciones de una solicitud."""

    __tablename__ = "movimientos_solicitud"

    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    estado_anterior: Mapped[str | None] = mapped_column(String(20))
    estado_nuevo: Mapped[str] = mapped_column(String(20))
    comentario: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    solicitud: Mapped[Solicitud] = relationship(back_populates="movimientos")
    usuario: Mapped[Usuario] = relationship()


# =====================================================================
# ACTIVA 360° · Módulo de RIESGOS (Fase 11)
# =====================================================================

class EvaluacionRiesgo(Base):
    """Evaluación preliminar y explicable. NO aprueba ni rechaza: solo alerta para revisión humana."""

    __tablename__ = "evaluaciones_riesgo"

    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), index=True)
    version_umbrales: Mapped[str] = mapped_column(String(30))
    semaforo: Mapped[str] = mapped_column(String(10), index=True)  # verde | amarillo | rojo
    indicadores: Mapped[dict] = mapped_column(JSON)
    alertas: Mapped[list] = mapped_column(JSON)  # [{nivel, codigo, mensaje}]
    opinion: Mapped[str | None] = mapped_column(Text)  # comentario del analista
    opinion_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    solicitud: Mapped[Solicitud] = relationship(back_populates="evaluaciones")
    autor: Mapped[Usuario] = relationship(foreign_keys=[creado_por])
    analista: Mapped["Usuario | None"] = relationship(foreign_keys=[opinion_por])


# =====================================================================
# ACTIVA 360° · Módulo de RECUPERACIONES (Fase 12)
# =====================================================================

class Credito(Base):
    """Crédito ya desembolsado por la entidad, registrado SOLO para su seguimiento."""

    __tablename__ = "creditos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    solicitud_id: Mapped[int | None] = mapped_column(ForeignKey("solicitudes.id"))
    producto: Mapped[str] = mapped_column(String(40))
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tea: Mapped[Decimal] = mapped_column(Numeric(7, 3))  # tasa efectiva anual registrada (%)
    plazo_meses: Mapped[int] = mapped_column(Integer)
    frecuencia: Mapped[str] = mapped_column(String(20))
    fecha_desembolso: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(20), default="vigente", index=True)  # vigente | cancelado
    gestor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    registrado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cliente: Mapped[Cliente] = relationship()
    gestor: Mapped["Usuario | None"] = relationship(foreign_keys=[gestor_id])
    cuotas: Mapped[list["Cuota"]] = relationship(back_populates="credito", order_by="Cuota.numero", cascade="all, delete-orphan")
    pagos: Mapped[list["Pago"]] = relationship(back_populates="credito", order_by="Pago.id.desc()", cascade="all, delete-orphan")
    gestiones: Mapped[list["GestionCobranza"]] = relationship(
        back_populates="credito", order_by="GestionCobranza.id.desc()", cascade="all, delete-orphan")
    compromisos: Mapped[list["CompromisoPago"]] = relationship(
        back_populates="credito", order_by="CompromisoPago.id.desc()", cascade="all, delete-orphan")
    reprogramaciones: Mapped[list["Reprogramacion"]] = relationship(
        back_populates="credito", order_by="Reprogramacion.id.desc()", cascade="all, delete-orphan")


class Cuota(Base):
    __tablename__ = "cuotas"
    __table_args__ = (UniqueConstraint("credito_id", "numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    credito_id: Mapped[int] = mapped_column(ForeignKey("creditos.id"), index=True)
    numero: Mapped[int] = mapped_column(Integer)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, index=True)
    capital: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    interes: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    pagado: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    fecha_pago: Mapped[date | None] = mapped_column(Date)  # cuando quedó pagada por completo

    credito: Mapped[Credito] = relationship(back_populates="cuotas")


class Pago(Base):
    """Pago informado por la entidad (registro manual; la plataforma no mueve dinero)."""

    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(primary_key=True)
    credito_id: Mapped[int] = mapped_column(ForeignKey("creditos.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    observacion: Mapped[str | None] = mapped_column(Text)
    registrado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    credito: Mapped[Credito] = relationship(back_populates="pagos")


class GestionCobranza(Base):
    __tablename__ = "gestiones_cobranza"

    id: Mapped[int] = mapped_column(primary_key=True)
    credito_id: Mapped[int] = mapped_column(ForeignKey("creditos.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    canal: Mapped[str] = mapped_column(String(20))
    resultado: Mapped[str] = mapped_column(String(30))  # clave de config/recuperaciones.yaml
    observacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    credito: Mapped[Credito] = relationship(back_populates="gestiones")
    usuario: Mapped[Usuario] = relationship()


class CompromisoPago(Base):
    __tablename__ = "compromisos_pago"

    id: Mapped[int] = mapped_column(primary_key=True)
    credito_id: Mapped[int] = mapped_column(ForeignKey("creditos.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")  # pendiente | cumplido | incumplido
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    credito: Mapped[Credito] = relationship(back_populates="compromisos")


class Reprogramacion(Base):
    """Pedido de reprogramación o refinanciamiento: siempre lo revisa una persona (gerente)."""

    __tablename__ = "reprogramaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    credito_id: Mapped[int] = mapped_column(ForeignKey("creditos.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))  # reprogramacion | refinanciamiento
    motivo: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")  # pendiente | aprobada | rechazada
    solicitada_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    revisada_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    comentario_revision: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revisado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    credito: Mapped[Credito] = relationship(back_populates="reprogramaciones")
