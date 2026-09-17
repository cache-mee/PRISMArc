from datetime import date, datetime, time, timedelta

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
    commit: bool = True,
) -> Booking:
    """Insert a new Booking row and return it.

    This is the sole insert path for a Booking row in the codebase.

    When ``commit`` is ``True`` (default), commits and refreshes the row
    immediately — the exact prior behavior. When ``False``, only flushes
    (still assigning the row's autoincrement ``id``), leaving the
    transaction open for a caller composing multiple writes.
    """
    booking = Booking(
        customer_id=customer_id,
        staff_id=staff_id,
        service_name=service_name,
        start_time=start_time,
        status=status,
    )
    db.add(booking)
    if commit:
        await db.commit()
        await db.refresh(booking)
    else:
        await db.flush()
    return booking


async def get_booking_by_id(db: AsyncSession, booking_id: int) -> Booking | None:
    """Return the Booking row matching booking_id, or None if not found."""
    stmt = select(Booking).where(Booking.id == booking_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def set_booking_status(
    db: AsyncSession, booking: Booking, status: str, *, commit: bool = True
) -> Booking:
    """Set an already-fetched Booking's status field.

    When ``commit`` is ``True`` (default), commits and refreshes the row
    immediately. When ``False``, only flushes, leaving the transaction open
    for a caller composing multiple writes.
    """
    booking.status = status
    if commit:
        await db.commit()
        await db.refresh(booking)
    else:
        await db.flush()
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
