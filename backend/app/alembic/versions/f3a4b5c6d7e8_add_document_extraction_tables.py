"""add durable visual document extraction tables

Revision ID: f3a4b5c6d7e8
Revises: b2c3d4e5f6a7
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_extraction",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("media_type", sa.String(length=150), nullable=False),
        sa.Column("source_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("normalized_result", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_extraction_owner_id",
        "document_extraction",
        ["owner_id"],
    )
    op.create_index(
        "ix_document_extraction_source_sha256",
        "document_extraction",
        ["source_sha256"],
    )
    op.create_table(
        "document_preview_artifact",
        sa.Column("cache_key", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["document_extraction.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("cache_key"),
    )
    op.create_index(
        "ix_document_preview_artifact_document_id",
        "document_preview_artifact",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_preview_artifact_document_id",
        table_name="document_preview_artifact",
    )
    op.drop_table("document_preview_artifact")
    op.drop_index(
        "ix_document_extraction_source_sha256",
        table_name="document_extraction",
    )
    op.drop_index(
        "ix_document_extraction_owner_id",
        table_name="document_extraction",
    )
    op.drop_table("document_extraction")
