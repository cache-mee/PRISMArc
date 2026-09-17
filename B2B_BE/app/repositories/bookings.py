from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking


async def get_bookings_for_staff_in_window(
    db: AsyncSession,
    *,
    staff_id: int,
    window_start: datetime,
    window_end: datetime,
) -> list[Booking]:
    """Return staff_id's bookings whose start_time falls in [window_start, window_end).

    Ordered by start_time. Used by the FR-26 conflict-check mechanism
    (app.domain.conflicts.check_conflicts).
    """
    stmt = (
        select(Booking)
        .where(
            Booking.staff_id == staff_id,
            Booking.start_time >= window_start,
            Booking.start_time < window_end,
        )
        .order_by(Booking.start_time)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_booking(
    db: AsyncSession,
    *,
    customer_id: int,
    staff_id: int,
    service_name: str,
    start_time: datetime,
    status: str = "confirmed",
) -> Booking:
    """Insert a new Booking row and return it.

    This is the sole insert path for a Booking row in the codebase.
    """
    booking = Booking(
        customer_id=customer_id,
        staff_id=staff_id,
        service_name=service_name,
        start_time=start_time,
        status=status,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


async def list_confirmed_bookings_for_staff_on_day(
    db: AsyncSession, *, staff_id: int, day: date
) -> list[Booking]:
    """List a staff member's confirmed Bookings on ``day`` (FR-7 booked-slot exclusion).

    Filters on ``status == "confirmed"`` and ``start_time`` falling within
    ``day``. ``Booking`` has no ``end_time``, so this is exact-start-time
    granularity only — the same single-time-field treatment already used
    everywhere else in the codebase.
    """
    day_start = datetime.combine(day, time.min)
    day_end = day_start + timedelta(days=1)
    result = await db.execute(
        select(Booking).where(
            Booking.staff_id == staff_id,
            Booking.status == "confirmed",
            Booking.start_time >= day_start,
            Booking.start_time < day_end,
        )
    )
    return list(result.scalars().all())
