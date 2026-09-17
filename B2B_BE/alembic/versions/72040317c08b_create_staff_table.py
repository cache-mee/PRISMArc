"""create staff table

Revision ID: 72040317c08b
Revises: d141a62b1e58
Create Date: 2026-09-17 19:35:42.749348

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "72040317c08b"
down_revision: str | Sequence[str] | None = "d141a62b1e58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    staff_role = sa.Enum("owner_admin", "staff", name="staff_role")
    staff_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "staff",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=False),
        sa.Column("role", staff_role, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_staff"),
    )
    op.create_index(
        "ix_staff_phone_number",
        "staff",
        ["phone_number"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_staff_phone_number", table_name="staff")
    op.drop_table("staff")

    staff_role = sa.Enum("owner_admin", "staff", name="staff_role")
    staff_role.drop(op.get_bind(), checkfirst=True)
