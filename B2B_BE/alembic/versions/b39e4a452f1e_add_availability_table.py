"""add availability table

Revision ID: b39e4a452f1e
Revises: 46fe8dea4e24
Create Date: 2026-09-17 20:35:05.949418

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b39e4a452f1e"
down_revision: str | Sequence[str] | None = "46fe8dea4e24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "availability",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("staff_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"], ["staff.id"], name="fk_availability_staff_id_staff"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_availability"),
    )
    op.create_index(
        op.f("ix_availability_staff_id"), "availability", ["staff_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_availability_staff_id"), table_name="availability")
    op.drop_table("availability")
