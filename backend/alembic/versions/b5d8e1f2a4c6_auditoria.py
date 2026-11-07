"""auditoria: registro de acciones y de intentos de inicio de sesion

Revision ID: b5d8e1f2a4c6
Revises: 9e4b2c7a1f30
Create Date: 2026-11-06 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5d8e1f2a4c6'
down_revision: Union[str, Sequence[str], None] = '9e4b2c7a1f30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'auditoria',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(length=160), nullable=True),
        sa.Column('accion', sa.String(length=40), nullable=False),
        sa.Column('detalle', sa.Text(), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_auditoria_usuario_id'), 'auditoria', ['usuario_id'], unique=False)
    op.create_index(op.f('ix_auditoria_email'), 'auditoria', ['email'], unique=False)
    op.create_index(op.f('ix_auditoria_accion'), 'auditoria', ['accion'], unique=False)
    op.create_index(op.f('ix_auditoria_creado_en'), 'auditoria', ['creado_en'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_auditoria_creado_en'), table_name='auditoria')
    op.drop_index(op.f('ix_auditoria_accion'), table_name='auditoria')
    op.drop_index(op.f('ix_auditoria_email'), table_name='auditoria')
    op.drop_index(op.f('ix_auditoria_usuario_id'), table_name='auditoria')
    op.drop_table('auditoria')
