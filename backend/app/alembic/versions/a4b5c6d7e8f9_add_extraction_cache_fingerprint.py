"""add extraction cache fingerprint

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4b5c6d7e8f9"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_extraction",
        sa.Column(
            "extraction_fingerprint",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_document_extraction_extraction_fingerprint",
        "document_extraction",
        ["extraction_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_extraction_extraction_fingerprint",
        table_name="document_extraction",
    )
    op.drop_column("document_extraction", "extraction_fingerprint")
