from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.availability import Availability


async def get_blocking_availability_for_staff_in_window(
    db: AsyncSession,
    *,
    staff_id: int,
    window_start: datetime,
    window_end: datetime,
) -> list[Availability]:
    """Return staff_id's blocked Availability rows overlapping [window_start, window_end).

    Ordered by start_time. Mirrors
    ``app.repositories.bookings.get_bookings_for_staff_in_window``'s shape
    (FR-26), applied to the ``availability`` table instead of ``bookings`` —
    the "blocked" half of FR-8's reason determination
    (app.domain.appointments.find_nearest_alternatives). Only rows with
    ``blocked is True`` are returned; an unblocked row is never a reason a
    requested time is unavailable.
    """
    stmt = (
        select(Availability)
        .where(
            Availability.staff_id == staff_id,
            Availability.blocked.is_(True),
            Availability.start_time < window_end,
            Availability.end_time > window_start,
        )
        .order_by(Availability.start_time)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


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
