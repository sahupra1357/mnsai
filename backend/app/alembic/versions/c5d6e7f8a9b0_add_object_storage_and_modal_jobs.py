"""add configurable object storage and Modal extraction jobs

Revision ID: c5d6e7f8a9b0
Revises: a4b5c6d7e8f9
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5d6e7f8a9b0"
down_revision: str | None = "a4b5c6d7e8f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("document_extraction") as batch_op:
        batch_op.alter_column("source_bytes", nullable=True)
        batch_op.add_column(
            sa.Column(
                "source_storage_provider",
                sa.String(length=20),
                server_default="postgres",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("source_object_key", sa.String(length=1024), nullable=True)
        )
    with op.batch_alter_table("document_preview_artifact") as batch_op:
        batch_op.alter_column("content", nullable=True)
        batch_op.add_column(
            sa.Column(
                "storage_provider",
                sa.String(length=20),
                server_default="postgres",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("object_key", sa.String(length=1024), nullable=True)
        )
    op.create_table(
        "document_extraction_job",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("operator_parser", sa.String(length=100), nullable=True),
        sa.Column("remote_call_id", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"], ["document_extraction.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id"),
    )
    op.create_index(
        "ix_document_extraction_job_document_id",
        "document_extraction_job",
        ["document_id"],
    )
    op.create_index(
        "ix_document_extraction_job_owner_id", "document_extraction_job", ["owner_id"]
    )
    op.create_index(
        "ix_document_extraction_job_status", "document_extraction_job", ["status"]
    )
    op.create_table(
        "document_job_token",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.String(length=40), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=30), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("use_count", sa.Integer(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("last_failure_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"], ["document_extraction_job.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["document_extraction.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_document_job_token_token_id", "document_job_token", ["token_id"]
    )
    op.create_index(
        "ix_document_job_token_token_hash", "document_job_token", ["token_hash"]
    )
    op.create_index("ix_document_job_token_job_id", "document_job_token", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_document_job_token_job_id", table_name="document_job_token")
    op.drop_index("ix_document_job_token_token_hash", table_name="document_job_token")
    op.drop_index("ix_document_job_token_token_id", table_name="document_job_token")
    op.drop_table("document_job_token")
    op.drop_index(
        "ix_document_extraction_job_status", table_name="document_extraction_job"
    )
    op.drop_index(
        "ix_document_extraction_job_owner_id", table_name="document_extraction_job"
    )
    op.drop_index(
        "ix_document_extraction_job_document_id", table_name="document_extraction_job"
    )
    op.drop_table("document_extraction_job")
    with op.batch_alter_table("document_preview_artifact") as batch_op:
        batch_op.drop_column("object_key")
        batch_op.drop_column("storage_provider")
        batch_op.alter_column("content", nullable=False)
    with op.batch_alter_table("document_extraction") as batch_op:
        batch_op.drop_column("source_object_key")
        batch_op.drop_column("source_storage_provider")
        batch_op.alter_column("source_bytes", nullable=False)
