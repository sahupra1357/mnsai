"""Rename contract_field_extraction.parties to customer

The schema no longer records every contracting entity. It records the *counterparty*
— the organisation the agreement is with — because the party running the deployment
is configuration (`settings.CONTRACT_HOME_ORGANIZATIONS`), not something to extract.
That removes "how many parties are there" from the grounding path entirely.

Existing rows are renamed but not rewritten: they hold whatever the old field
extracted, which may name both sides. Stripping the home organisation out of stored
text in SQL would be a guess, and a wrong guess is worse than a stale value a human
can see. `extraction_status` is untouched, so nothing silently changes state.

Revision ID: c1d2e3f4a5b6
Revises: b9c0d1e2f3a4
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("contract_field_extraction", "parties", new_column_name="customer")


def downgrade() -> None:
    op.alter_column("contract_field_extraction", "customer", new_column_name="parties")
