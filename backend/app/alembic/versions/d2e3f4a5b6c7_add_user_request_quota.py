"""Add per-user lifetime request quota to "user"

Two columns, both NOT NULL with a server default so existing rows are valid the
moment the column lands:

  request_limit  the ceiling this account is allowed, editable per user from the
                 user management screen. Seeded from settings.DEFAULT_REQUEST_LIMIT
                 for new accounts; the column is the enforced value, the setting is
                 only where a new account starts.
  request_count  how many metered actions the account has spent, lifetime.

Existing accounts are backfilled to the same default limit with zero spent, so
nobody is locked out by the upgrade itself. Superusers carry the columns too but
are never metered, so their values are inert.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.config import settings

revision: str = "d2e3f4a5b6c7"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "request_limit",
            sa.Integer(),
            nullable=False,
            server_default=str(settings.DEFAULT_REQUEST_LIMIT),
        ),
    )
    op.add_column(
        "user",
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("user", "request_count")
    op.drop_column("user", "request_limit")
