"""add document extraction api keys

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6e7f8a9b0c1"
down_revision: str | None = "c5d6e7f8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_extraction_api_key",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key_prefix", sa.String(length=20), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index(
        op.f("ix_document_extraction_api_key_owner_id"),
        "document_extraction_api_key",
        ["owner_id"],
    )
    op.create_index(
        op.f("ix_document_extraction_api_key_key_prefix"),
        "document_extraction_api_key",
        ["key_prefix"],
    )
    op.create_index(
        op.f("ix_document_extraction_api_key_key_hash"),
        "document_extraction_api_key",
        ["key_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_document_extraction_api_key_revoked_at"),
        "document_extraction_api_key",
        ["revoked_at"],
    )


def downgrade() -> None:
    op.drop_table("document_extraction_api_key")
