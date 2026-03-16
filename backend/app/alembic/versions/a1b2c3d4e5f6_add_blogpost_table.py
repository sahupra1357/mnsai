"""add blogpost table

Revision ID: a1b2c3d4e5f6
Revises: e480532b73da
Create Date: 2026-03-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e480532b73da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'blogpost',
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('summary', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tags', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_blogpost_slug'), 'blogpost', ['slug'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_blogpost_slug'), table_name='blogpost')
    op.drop_table('blogpost')
