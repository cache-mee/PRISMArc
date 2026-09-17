"""add bookings table

Revision ID: c8354b5d4b5c
Revises: 1b9376ed1c01
Create Date: 2026-09-17 20:14:34.097615

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8354b5d4b5c"
down_revision: str | Sequence[str] | None = "1b9376ed1c01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("staff_id", sa.Integer(), nullable=False),
        sa.Column("service_name", sa.String(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customers.id"], name="fk_bookings_customer_id_customers"
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"], ["staff.id"], name="fk_bookings_staff_id_staff"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bookings"),
    )
    op.create_index(
        op.f("ix_bookings_customer_id"), "bookings", ["customer_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_bookings_customer_id"), table_name="bookings")
    op.drop_table("bookings")
