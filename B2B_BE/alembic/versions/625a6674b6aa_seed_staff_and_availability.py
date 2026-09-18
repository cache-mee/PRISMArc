"""seed staff and availability

Revision ID: 625a6674b6aa
Revises: 583f31e9e301
Create Date: 2026-09-18 08:30:00.000000

"""

from collections.abc import Sequence
from datetime import datetime, timezone

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "625a6674b6aa"
down_revision: str | Sequence[str] | None = "583f31e9e301"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


staff_table = sa.table(
    "staff",
    sa.column("id", sa.Integer()),
    sa.column("name", sa.String()),
    sa.column("phone_number", sa.String()),
    sa.column("role", sa.Enum("owner_admin", "staff", name="staff_role")),
)

availability_table = sa.table(
    "availability",
    sa.column("staff_id", sa.Integer()),
    sa.column("start_time", sa.DateTime(timezone=True)),
    sa.column("end_time", sa.DateTime(timezone=True)),
    sa.column("blocked", sa.Boolean()),
)

STAFF_ROWS = [
    {
        "name": "Divya",
        "phone_number": "+15550000004",
        "role": "staff",
    },
    {
        "name": "Karan",
        "phone_number": "+15550000005",
        "role": "staff",
    },
]

_WORK_START = datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc)
_WORK_END = datetime(2026, 9, 19, 17, 0, tzinfo=timezone.utc)

# staff phone_number -> daily working window seeded for the day after
# Create Date, one row per existing/new staff member.
AVAILABILITY_BY_PHONE = {
    "+15550000001": (_WORK_START, _WORK_END),
    "+15550000002": (_WORK_START, _WORK_END),
    "+15550000003": (_WORK_START, _WORK_END),
    "+15550000004": (_WORK_START, _WORK_END),
    "+15550000005": (_WORK_START, _WORK_END),
}


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(staff_table, STAFF_ROWS)

    conn = op.get_bind()
    phone_to_id = dict(
        conn.execute(sa.select(staff_table.c.phone_number, staff_table.c.id)).fetchall()
    )

    availability_rows = [
        {
            "staff_id": phone_to_id[phone],
            "start_time": start,
            "end_time": end,
            "blocked": False,
        }
        for phone, (start, end) in AVAILABILITY_BY_PHONE.items()
        if phone in phone_to_id
    ]
    op.bulk_insert(availability_table, availability_rows)


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    phone_to_id = dict(
        conn.execute(sa.select(staff_table.c.phone_number, staff_table.c.id)).fetchall()
    )
    for phone, (start, end) in AVAILABILITY_BY_PHONE.items():
        staff_id = phone_to_id.get(phone)
        if staff_id is None:
            continue
        op.execute(
            availability_table.delete().where(
                sa.and_(
                    availability_table.c.staff_id == staff_id,
                    availability_table.c.start_time == start,
                    availability_table.c.end_time == end,
                )
            )
        )
    op.execute(
        staff_table.delete().where(
            staff_table.c.phone_number.in_([row["phone_number"] for row in STAFF_ROWS])
        )
    )
