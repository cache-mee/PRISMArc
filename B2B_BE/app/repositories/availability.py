from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.availability import Availability


async def create_availability(
    db: AsyncSession,
    *,
    staff_id: int,
    start_time: datetime,
    end_time: datetime,
    blocked: bool,
) -> Availability:
    """Insert a new Availability row and return it.

    This is the sole insert path for an Availability row in the codebase.
    """
    availability = Availability(
        staff_id=staff_id,
        start_time=start_time,
        end_time=end_time,
        blocked=blocked,
    )
    db.add(availability)
    await db.commit()
    await db.refresh(availability)
    return availability


async def list_availability_for_staff_on_day(
    db: AsyncSession, *, staff_id: int, day: date
) -> list[Availability]:
    """List a staff member's Availability rows relevant to resolving ``day``'s block state.

    Returns every row whose ``[start_time, end_time)`` window overlaps
    ``day`` (not just rows created on ``day``) — the block/unblock
    resolution FR-7 needs (see ``app.domain.availability._is_blocked_at``)
    only cares about which windows actually cover a given instant, not when
    the row happened to be created relative to the calendar day.
    """
    day_start = datetime.combine(day, time.min)
    day_end = day_start + timedelta(days=1)
    result = await db.execute(
        select(Availability).where(
            Availability.staff_id == staff_id,
            Availability.start_time < day_end,
            Availability.end_time > day_start,
        )
    )
    return list(result.scalars().all())
