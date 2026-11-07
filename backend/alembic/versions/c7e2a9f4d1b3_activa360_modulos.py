"""activa360: modulos comercial, negocios, riesgos y recuperaciones

Revision ID: c7e2a9f4d1b3
Revises: b5d8e1f2a4c6
Create Date: 2026-11-06 17:05:43.264964

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e2a9f4d1b3'
down_revision: Union[str, Sequence[str], None] = 'b5d8e1f2a4c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    op.create_table('prospectos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('telefono', sa.String(length=20), nullable=False),
    sa.Column('dni', sa.String(length=8), nullable=True),
    sa.Column('segmento', sa.String(length=30), nullable=False),
    sa.Column('actividad', sa.String(length=120), nullable=False),
    sa.Column('necesidad', sa.Text(), nullable=False),
    sa.Column('region', sa.String(length=30), nullable=False),
    sa.Column('ubicacion', sa.String(length=120), nullable=True),
    sa.Column('monto_solicitado', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('contacto_preferido', sa.String(length=20), nullable=False),
    sa.Column('consentimiento', sa.Boolean(), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('origen', sa.String(length=20), nullable=False),
    sa.Column('asesor_id', sa.Integer(), nullable=True),
    sa.Column('campana_id', sa.Integer(), nullable=True),
    sa.Column('interesado_id', sa.Integer(), nullable=True),
    sa.Column('proxima_accion', sa.Date(), nullable=True),
    sa.Column('creado_por', sa.Integer(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['asesor_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['campana_id'], ['campanas.id'], ),
    sa.ForeignKeyConstraint(['creado_por'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['interesado_id'], ['interesados.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prospectos_asesor_id'), 'prospectos', ['asesor_id'], unique=False)
    op.create_index(op.f('ix_prospectos_campana_id'), 'prospectos', ['campana_id'], unique=False)
    op.create_index(op.f('ix_prospectos_dni'), 'prospectos', ['dni'], unique=False)
    op.create_index(op.f('ix_prospectos_estado'), 'prospectos', ['estado'], unique=False)
    op.create_table('clientes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('dni', sa.String(length=8), nullable=False),
    sa.Column('nombres', sa.String(length=120), nullable=False),
    sa.Column('telefono', sa.String(length=20), nullable=False),
    sa.Column('email', sa.String(length=160), nullable=True),
    sa.Column('segmento', sa.String(length=30), nullable=False),
    sa.Column('ocupacion', sa.String(length=120), nullable=False),
    sa.Column('region', sa.String(length=30), nullable=False),
    sa.Column('ubicacion', sa.String(length=120), nullable=True),
    sa.Column('ingresos_mensuales', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('gastos_mensuales', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('antiguedad_meses', sa.Integer(), nullable=False),
    sa.Column('cuotas_otras_deudas', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('saldo_otras_deudas', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('necesidades', sa.Text(), nullable=True),
    sa.Column('consentimiento', sa.Boolean(), nullable=False),
    sa.Column('prospecto_id', sa.Integer(), nullable=True),
    sa.Column('asesor_id', sa.Integer(), nullable=False),
    sa.Column('creado_por', sa.Integer(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['asesor_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['creado_por'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['prospecto_id'], ['prospectos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clientes_asesor_id'), 'clientes', ['asesor_id'], unique=False)
    op.create_index(op.f('ix_clientes_dni'), 'clientes', ['dni'], unique=True)
    op.create_index(op.f('ix_clientes_telefono'), 'clientes', ['telefono'], unique=False)
    op.create_table('contactos_prospecto',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('prospecto_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('canal', sa.String(length=20), nullable=False),
    sa.Column('resultado', sa.Text(), nullable=False),
    sa.Column('estado_nuevo', sa.String(length=20), nullable=False),
    sa.Column('proxima_accion', sa.Date(), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['prospecto_id'], ['prospectos.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contactos_prospecto_prospecto_id'), 'contactos_prospecto', ['prospecto_id'], unique=False)
    op.create_table('solicitudes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cliente_id', sa.Integer(), nullable=False),
    sa.Column('asesor_id', sa.Integer(), nullable=False),
    sa.Column('producto', sa.String(length=40), nullable=False),
    sa.Column('monto', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('plazo_meses', sa.Integer(), nullable=False),
    sa.Column('frecuencia', sa.String(length=20), nullable=False),
    sa.Column('destino', sa.Text(), nullable=False),
    sa.Column('datos_perfil', sa.JSON(), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('campana_id', sa.Integer(), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['asesor_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['campana_id'], ['campanas.id'], ),
    sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_solicitudes_asesor_id'), 'solicitudes', ['asesor_id'], unique=False)
    op.create_index(op.f('ix_solicitudes_cliente_id'), 'solicitudes', ['cliente_id'], unique=False)
    op.create_index(op.f('ix_solicitudes_estado'), 'solicitudes', ['estado'], unique=False)
    op.create_table('creditos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cliente_id', sa.Integer(), nullable=False),
    sa.Column('solicitud_id', sa.Integer(), nullable=True),
    sa.Column('producto', sa.String(length=40), nullable=False),
    sa.Column('monto', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('tea', sa.Numeric(precision=7, scale=3), nullable=False),
    sa.Column('plazo_meses', sa.Integer(), nullable=False),
    sa.Column('frecuencia', sa.String(length=20), nullable=False),
    sa.Column('fecha_desembolso', sa.Date(), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('gestor_id', sa.Integer(), nullable=True),
    sa.Column('registrado_por', sa.Integer(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ),
    sa.ForeignKeyConstraint(['gestor_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['registrado_por'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['solicitud_id'], ['solicitudes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_creditos_cliente_id'), 'creditos', ['cliente_id'], unique=False)
    op.create_index(op.f('ix_creditos_estado'), 'creditos', ['estado'], unique=False)
    op.create_index(op.f('ix_creditos_gestor_id'), 'creditos', ['gestor_id'], unique=False)
    op.create_table('documentos_solicitud',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('solicitud_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=40), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('observacion', sa.Text(), nullable=True),
    sa.Column('revisado_por', sa.Integer(), nullable=True),
    sa.Column('revisado_en', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['revisado_por'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['solicitud_id'], ['solicitudes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documentos_solicitud_solicitud_id'), 'documentos_solicitud', ['solicitud_id'], unique=False)
    op.create_table('evaluaciones_riesgo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('solicitud_id', sa.Integer(), nullable=False),
    sa.Column('version_umbrales', sa.String(length=30), nullable=False),
    sa.Column('semaforo', sa.String(length=10), nullable=False),
    sa.Column('indicadores', sa.JSON(), nullable=False),
    sa.Column('alertas', sa.JSON(), nullable=False),
    sa.Column('opinion', sa.Text(), nullable=True),
    sa.Column('opinion_por', sa.Integer(), nullable=True),
    sa.Column('creado_por', sa.Integer(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['creado_por'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['opinion_por'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['solicitud_id'], ['solicitudes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluaciones_riesgo_semaforo'), 'evaluaciones_riesgo', ['semaforo'], unique=False)
    op.create_index(op.f('ix_evaluaciones_riesgo_solicitud_id'), 'evaluaciones_riesgo', ['solicitud_id'], unique=False)
    op.create_table('movimientos_solicitud',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('solicitud_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('estado_anterior', sa.String(length=20), nullable=True),
    sa.Column('estado_nuevo', sa.String(length=20), nullable=False),
    sa.Column('comentario', sa.Text(), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['solicitud_id'], ['solicitudes.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_movimientos_solicitud_solicitud_id'), 'movimientos_solicitud', ['solicitud_id'], unique=False)
    op.create_table('compromisos_pago',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('credito_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.Date(), nullable=False),
    sa.Column('monto', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('creado_por', sa.Integer(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['creado_por'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['credito_id'], ['creditos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compromisos_pago_credito_id'), 'compromisos_pago', ['credito_id'], unique=False)
    op.create_index(op.f('ix_compromisos_pago_fecha'), 'compromisos_pago', ['fecha'], unique=False)
    op.create_table('cuotas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('credito_id', sa.Integer(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('fecha_vencimiento', sa.Date(), nullable=False),
    sa.Column('capital', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('interes', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('monto', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('pagado', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('fecha_pago', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['credito_id'], ['creditos.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('credito_id', 'numero')
    )
    op.create_index(op.f('ix_cuotas_credito_id'), 'cuotas', ['credito_id'], unique=False)
    op.create_index(op.f('ix_cuotas_fecha_vencimiento'), 'cuotas', ['fecha_vencimiento'], unique=False)
    op.create_table('gestiones_cobranza',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('credito_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('canal', sa.String(length=20), nullable=False),
    sa.Column('resultado', sa.String(length=30), nullable=False),
    sa.Column('observacion', sa.Text(), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['credito_id'], ['creditos.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gestiones_cobranza_credito_id'), 'gestiones_cobranza', ['credito_id'], unique=False)
    op.create_table('pagos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('credito_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.Date(), nullable=False),
    sa.Column('monto', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('observacion', sa.Text(), nullable=True),
    sa.Column('registrado_por', sa.Integer(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['credito_id'], ['creditos.id'], ),
    sa.ForeignKeyConstraint(['registrado_por'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pagos_credito_id'), 'pagos', ['credito_id'], unique=False)
    op.create_table('reprogramaciones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('credito_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('motivo', sa.Text(), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('solicitada_por', sa.Integer(), nullable=False),
    sa.Column('revisada_por', sa.Integer(), nullable=True),
    sa.Column('comentario_revision', sa.Text(), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('revisado_en', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['credito_id'], ['creditos.id'], ),
    sa.ForeignKeyConstraint(['revisada_por'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['solicitada_por'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reprogramaciones_credito_id'), 'reprogramaciones', ['credito_id'], unique=False)
    


def downgrade() -> None:
    """Downgrade schema."""
    
    op.drop_index(op.f('ix_reprogramaciones_credito_id'), table_name='reprogramaciones')
    op.drop_table('reprogramaciones')
    op.drop_index(op.f('ix_pagos_credito_id'), table_name='pagos')
    op.drop_table('pagos')
    op.drop_index(op.f('ix_gestiones_cobranza_credito_id'), table_name='gestiones_cobranza')
    op.drop_table('gestiones_cobranza')
    op.drop_index(op.f('ix_cuotas_fecha_vencimiento'), table_name='cuotas')
    op.drop_index(op.f('ix_cuotas_credito_id'), table_name='cuotas')
    op.drop_table('cuotas')
    op.drop_index(op.f('ix_compromisos_pago_fecha'), table_name='compromisos_pago')
    op.drop_index(op.f('ix_compromisos_pago_credito_id'), table_name='compromisos_pago')
    op.drop_table('compromisos_pago')
    op.drop_index(op.f('ix_movimientos_solicitud_solicitud_id'), table_name='movimientos_solicitud')
    op.drop_table('movimientos_solicitud')
    op.drop_index(op.f('ix_evaluaciones_riesgo_solicitud_id'), table_name='evaluaciones_riesgo')
    op.drop_index(op.f('ix_evaluaciones_riesgo_semaforo'), table_name='evaluaciones_riesgo')
    op.drop_table('evaluaciones_riesgo')
    op.drop_index(op.f('ix_documentos_solicitud_solicitud_id'), table_name='documentos_solicitud')
    op.drop_table('documentos_solicitud')
    op.drop_index(op.f('ix_creditos_gestor_id'), table_name='creditos')
    op.drop_index(op.f('ix_creditos_estado'), table_name='creditos')
    op.drop_index(op.f('ix_creditos_cliente_id'), table_name='creditos')
    op.drop_table('creditos')
    op.drop_index(op.f('ix_solicitudes_estado'), table_name='solicitudes')
    op.drop_index(op.f('ix_solicitudes_cliente_id'), table_name='solicitudes')
    op.drop_index(op.f('ix_solicitudes_asesor_id'), table_name='solicitudes')
    op.drop_table('solicitudes')
    op.drop_index(op.f('ix_contactos_prospecto_prospecto_id'), table_name='contactos_prospecto')
    op.drop_table('contactos_prospecto')
    op.drop_index(op.f('ix_clientes_telefono'), table_name='clientes')
    op.drop_index(op.f('ix_clientes_dni'), table_name='clientes')
    op.drop_index(op.f('ix_clientes_asesor_id'), table_name='clientes')
    op.drop_table('clientes')
    op.drop_index(op.f('ix_prospectos_estado'), table_name='prospectos')
    op.drop_index(op.f('ix_prospectos_dni'), table_name='prospectos')
    op.drop_index(op.f('ix_prospectos_campana_id'), table_name='prospectos')
    op.drop_index(op.f('ix_prospectos_asesor_id'), table_name='prospectos')
    op.drop_table('prospectos')
    
