"""create salons table and seed the one salon

Revision ID: a1c2e3f4b5d6
Revises: b39e4a452f1e
Create Date: 2026-09-17 22:00:00.000000

APPOINTMEN-13 AC1: exactly one Salon record exists. Deliberately does not
add a salon_id FK to staff/services — no acceptance criterion requires it,
and every additional touch to those already-shipped, actively-depended-on
tables is unnecessary conflict surface in a fast-moving codebase.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c2e3f4b5d6"
down_revision: str | Sequence[str] | None = "b39e4a452f1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SALON_NAME = "The Salon"

salons_table = sa.table(
    "salons",
    sa.column("id", sa.Integer()),
    sa.column("name", sa.String()),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "salons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_salons"),
    )
    op.bulk_insert(salons_table, [{"name": SALON_NAME}])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("salons")
