"""seed staff records

Revision ID: 8aac3e937d39
Revises: 72040317c08b
Create Date: 2026-09-17 19:35:43.418660

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8aac3e937d39"
down_revision: str | Sequence[str] | None = "72040317c08b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


staff_table = sa.table(
    "staff",
    sa.column("name", sa.String()),
    sa.column("phone_number", sa.String()),
    sa.column("role", sa.Enum("owner_admin", "staff", name="staff_role")),
)

SEED_ROWS = [
    {
        "name": "Ramesh",
        "phone_number": "+15550000001",
        "role": "owner_admin",
    },
    {
        "name": "Meena",
        "phone_number": "+15550000002",
        "role": "staff",
    },
    {
        "name": "Arjun",
        "phone_number": "+15550000003",
        "role": "staff",
    },
]


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(staff_table, SEED_ROWS)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        staff_table.delete().where(
            staff_table.c.phone_number.in_([row["phone_number"] for row in SEED_ROWS])
        )
    )
