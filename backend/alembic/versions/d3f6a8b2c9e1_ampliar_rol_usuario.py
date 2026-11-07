"""Ampliar usuarios.rol a 30 caracteres ('gestor_recuperaciones' tiene 21)

Revision ID: d3f6a8b2c9e1
Revises: c7e2a9f4d1b3
Create Date: 2026-11-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd3f6a8b2c9e1'
down_revision: Union[str, Sequence[str], None] = 'c7e2a9f4d1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('usuarios') as batch:
        batch.alter_column('rol', existing_type=sa.String(20), type_=sa.String(30), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('usuarios') as batch:
        batch.alter_column('rol', existing_type=sa.String(30), type_=sa.String(20), existing_nullable=False)
