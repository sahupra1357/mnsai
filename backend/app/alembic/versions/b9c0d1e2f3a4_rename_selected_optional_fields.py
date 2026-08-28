"""Rename contract_field_extraction.selected_optional_fields to selected_fields

Every one of the ten contract fields is now individually selectable and
deselectable — there is no always-extracted subset any more — so the column no
longer holds "the optional ones that were picked" but the whole requested set.

Existing rows recorded only the *optional* keys they asked for, because the five
former-fixed fields were implicit. Under the new meaning the column is the whole
requested set, so those rows are backfilled with the five formerly-implicit keys —
otherwise a row would claim it never requested `contract_title`, while holding an
extracted value for it and listing it in `unresolved_fields`, which the response
model rejects.

Revision ID: b9c0d1e2f3a4
Revises: e7f8a9b0c1d2
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9c0d1e2f3a4"
down_revision: str | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#: The five fields that used to be extracted unconditionally, so were never recorded
#: in the old column. Order matches the catalogue.
_FORMERLY_IMPLICIT = [
    "contract_title",
    "parties",
    "effective_date",
    "term_end_date",
    "contract_value",
]


def upgrade() -> None:
    op.alter_column(
        "contract_field_extraction",
        "selected_optional_fields",
        new_column_name="selected_fields",
    )

    # Backfill in Python rather than SQL: the column is portable JSON (not JSONB), so
    # there is no cross-dialect array-concat operator to rely on here.
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, selected_fields FROM contract_field_extraction")
    ).fetchall()
    for row_id, selected in rows:
        existing = selected if isinstance(selected, list) else []
        merged = _FORMERLY_IMPLICIT + [
            key for key in existing if key not in _FORMERLY_IMPLICIT
        ]
        connection.execute(
            sa.text(
                "UPDATE contract_field_extraction SET selected_fields = :value "
                "WHERE id = :id"
            ),
            {
                "value": sa.JSON().bind_processor(connection.dialect)(merged),
                "id": row_id,
            },
        )


def downgrade() -> None:
    # The backfill is not reversed: dropping keys would lose the record of what was
    # actually requested, and the old column tolerates the extra entries.
    op.alter_column(
        "contract_field_extraction",
        "selected_fields",
        new_column_name="selected_optional_fields",
    )
