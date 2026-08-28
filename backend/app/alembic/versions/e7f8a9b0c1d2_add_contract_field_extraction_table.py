"""add contract field extraction table

Ten real named field columns, one per catalogue key, all NOT NULL DEFAULT '' —
the table maps one-to-one onto the ten-key JSON contract. Dates are DD/MM/YYYY
text, not a date column, so an unparseable source stays representable as ''.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "e7f8a9b0c1d2"
down_revision: str | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The ten catalogue keys, in catalogue order. Kept literal here on purpose: a
# migration is a historical record and must not change when the catalogue does.
FIELD_COLUMNS = (
    "contract_title",
    "parties",
    "effective_date",
    "term_end_date",
    "contract_value",
    "governing_law",
    "payment_terms",
    "notice_period",
    "renewal_terms",
    "termination_clause",
)


def upgrade() -> None:
    op.create_table(
        "contract_field_extraction",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False
        ),
        sa.Column(
            "source_sha256", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False
        ),
        *(
            sa.Column(
                name,
                sqlmodel.sql.sqltypes.AutoString(),
                server_default="",
                nullable=False,
            )
            for name in FIELD_COLUMNS
        ),
        sa.Column("selected_optional_fields", sa.JSON(), nullable=False),
        sa.Column(
            "extraction_status",
            sqlmodel.sql.sqltypes.AutoString(length=30),
            nullable=False,
        ),
        sa.Column("unresolved_fields", sa.JSON(), nullable=False),
        sa.Column("verified_values", sa.JSON(), nullable=False),
        sa.Column("verified_by", sa.Uuid(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("field_provenance", sa.JSON(), nullable=False),
        sa.Column("audit_events", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_by"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_contract_field_extraction_owner_id",
        "contract_field_extraction",
        ["owner_id"],
    )
    op.create_index(
        "ix_contract_field_extraction_document_id",
        "contract_field_extraction",
        ["document_id"],
    )
    op.create_index(
        "ix_contract_field_extraction_source_sha256",
        "contract_field_extraction",
        ["source_sha256"],
    )
    # The table view filters on status to find the failures.
    op.create_index(
        "ix_contract_field_extraction_extraction_status",
        "contract_field_extraction",
        ["extraction_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contract_field_extraction_extraction_status",
        table_name="contract_field_extraction",
    )
    op.drop_index(
        "ix_contract_field_extraction_source_sha256",
        table_name="contract_field_extraction",
    )
    op.drop_index(
        "ix_contract_field_extraction_document_id",
        table_name="contract_field_extraction",
    )
    op.drop_index(
        "ix_contract_field_extraction_owner_id",
        table_name="contract_field_extraction",
    )
    op.drop_table("contract_field_extraction")
