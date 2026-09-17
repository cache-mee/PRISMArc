"""add services.is_active

Revision ID: e5f6a7b8c9d0
Revises: d4f5a6c7e8b9
Create Date: 2026-09-17 23:00:00.000000

APPOINTMEN-39 (FR-17): soft-delete support for Service. Adds a non-nullable
``is_active`` boolean column (default ``True``) so an existing row can be
"removed" (``is_active = False``) without violating
``bookings.service_id``'s FK, which has no ``ondelete`` clause and would
raise an integrity error on a hard delete for any service referenced by an
existing booking. Every existing row backfills to active via the server
default, so no separate data migration step is needed.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4f5a6c7e8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "services",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("services", "is_active")
