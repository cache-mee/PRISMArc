"""seed core demo data

Revision ID: 583f31e9e301
Revises: e5f6a7b8c9d0
Create Date: 2026-09-18 07:59:56.688522

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "583f31e9e301"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


salons_table = sa.table(
    "salons",
    sa.column("name", sa.String()),
)

services_table = sa.table(
    "services",
    sa.column("name", sa.String()),
    sa.column("price", sa.Numeric(10, 2)),
    sa.column("is_active", sa.Boolean()),
)

customers_table = sa.table(
    "customers",
    sa.column("phone_number", sa.String()),
    sa.column("name", sa.String()),
)

SALON_ROWS = [
    {"name": "Glow Studio"},
]

SERVICE_ROWS = [
    {"name": "Haircut", "price": "25.00", "is_active": True},
    {"name": "Hair Coloring", "price": "60.00", "is_active": True},
    {"name": "Manicure", "price": "20.00", "is_active": True},
    {"name": "Pedicure", "price": "25.00", "is_active": True},
    {"name": "Facial", "price": "45.00", "is_active": True},
]

CUSTOMER_ROWS = [
    {"phone_number": "+15550001001", "name": "Priya Sharma"},
    {"phone_number": "+15550001002", "name": "John Doe"},
    {"phone_number": "+15550001003", "name": "Aisha Khan"},
]


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(salons_table, SALON_ROWS)
    op.bulk_insert(services_table, SERVICE_ROWS)
    op.bulk_insert(customers_table, CUSTOMER_ROWS)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        customers_table.delete().where(
            customers_table.c.phone_number.in_(
                [row["phone_number"] for row in CUSTOMER_ROWS]
            )
        )
    )
    op.execute(
        services_table.delete().where(
            services_table.c.name.in_([row["name"] for row in SERVICE_ROWS])
        )
    )
    op.execute(
        salons_table.delete().where(
            salons_table.c.name.in_([row["name"] for row in SALON_ROWS])
        )
    )
