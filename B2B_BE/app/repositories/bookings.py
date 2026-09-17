from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.staff import Staff


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


async def get_bookings_with_staff_for_customer(
    db: AsyncSession, *, customer_id: int
) -> list[tuple[Booking, str]]:
    """Return customer_id's own bookings, each paired with its staff's name.

    Joins Booking to Staff on Booking.staff_id == Staff.id so callers get the
    staff display name (e.g. "Haircut with Meena") without a second round
    trip. Filtering on Booking.customer_id == customer_id is the sole
    enforcement point, at the data-access layer, for "never another
    customer's bookings". Ordered by start_time so upcoming/past partitioning
    downstream sees a stable, chronological sequence.
    """
    stmt = (
        select(Booking, Staff.name)
        .join(Staff, Booking.staff_id == Staff.id)
        .where(Booking.customer_id == customer_id)
        .order_by(Booking.start_time)
    )
    result = await db.execute(stmt)
    return [(booking, staff_name) for booking, staff_name in result.all()]


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
