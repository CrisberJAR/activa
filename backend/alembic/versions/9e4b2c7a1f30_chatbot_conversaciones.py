"""chatbot: conversaciones y consentimiento de interesados

Revision ID: 9e4b2c7a1f30
Revises: 7c1f3a9d2e5b
Create Date: 2026-10-29 21:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e4b2c7a1f30'
down_revision: Union[str, Sequence[str], None] = '7c1f3a9d2e5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'conversaciones',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('sector', sa.String(length=40), nullable=True),
        sa.Column('campana_id', sa.Integer(), nullable=True),
        sa.Column('datos', sa.JSON(), nullable=False),
        sa.Column('mensajes', sa.JSON(), nullable=False),
        sa.Column('n_mensajes', sa.Integer(), nullable=False),
        sa.Column('ip_hash', sa.String(length=64), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['campana_id'], ['campanas.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_conversaciones_ip_hash'), 'conversaciones', ['ip_hash'], unique=False)
    op.add_column('interesados', sa.Column('consentimiento', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('interesados', 'consentimiento')
    op.drop_index(op.f('ix_conversaciones_ip_hash'), table_name='conversaciones')
    op.drop_table('conversaciones')
