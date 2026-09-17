from datetime import datetime

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


async def get_booking_by_id(db: AsyncSession, booking_id: int) -> Booking | None:
    """Return the Booking row matching booking_id, or None if no row exists.

    Needed by app.domain.appointments.cancel_customer_booking (FR-11) to
    resolve not-found/ownership/already-cancelled before any write is
    attempted.
    """
    stmt = select(Booking).where(Booking.id == booking_id)
    result = await db.execute(stmt)
    return result.scalars().first()


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
