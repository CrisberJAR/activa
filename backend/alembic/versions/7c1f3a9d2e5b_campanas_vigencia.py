"""campanas: tipo, bloque, generado_con y vigencia

Revision ID: 7c1f3a9d2e5b
Revises: 23b4905a6183
Create Date: 2026-10-29 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c1f3a9d2e5b'
down_revision: Union[str, Sequence[str], None] = '23b4905a6183'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('campanas', sa.Column('tipo_campana', sa.String(length=40), nullable=True))
    op.add_column('campanas', sa.Column('bloque_id', sa.Integer(), nullable=True))
    op.add_column('campanas', sa.Column('generado_con', sa.String(length=60), nullable=True))
    op.add_column('campanas', sa.Column('vigente_desde', sa.Date(), nullable=True))
    op.add_column('campanas', sa.Column('vigente_hasta', sa.Date(), nullable=True))
    op.create_foreign_key('campanas_bloque_id_fkey', 'campanas', 'bloques', ['bloque_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('campanas_bloque_id_fkey', 'campanas', type_='foreignkey')
    op.drop_column('campanas', 'vigente_hasta')
    op.drop_column('campanas', 'vigente_desde')
    op.drop_column('campanas', 'generado_con')
    op.drop_column('campanas', 'bloque_id')
    op.drop_column('campanas', 'tipo_campana')
