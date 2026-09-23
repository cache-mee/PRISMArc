"""link bookings to service_id, backfilled by name match

Revision ID: d4f5a6c7e8b9
Revises: a1c2e3f4b5d6
Create Date: 2026-09-17 22:10:00.000000

APPOINTMEN-13 AC4: bookings.service_name predates the Service entity (a gap
noted in Booking's own docstring). Adds service_id as a nullable FK,
backfilled by matching service_name against services.name where an exact
match exists. Left nullable rather than fabricating a match for any
historical row whose service_name has no equivalent services row —
service_name itself is untouched, so no existing caller breaks.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4f5a6c7e8b9"
down_revision: str | Sequence[str] | None = "a1c2e3f4b5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("bookings", sa.Column("service_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE bookings
        SET service_id = services.id
        FROM services
        WHERE bookings.service_name = services.name
        """
    )
    op.create_foreign_key(
        "fk_bookings_service_id_services", "bookings", "services", ["service_id"], ["id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_bookings_service_id_services", "bookings", type_="foreignkey")
    op.drop_column("bookings", "service_id")
