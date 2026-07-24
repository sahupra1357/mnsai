"""add profileimage table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'profileimage',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('slot', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('content_type', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('filename', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_profileimage_slot'), 'profileimage', ['slot'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_profileimage_slot'), table_name='profileimage')
    op.drop_table('profileimage')
