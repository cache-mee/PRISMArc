from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.booking import Booking


def get_bookings_for_staff_in_window(
    db: Session,
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
    return list(db.execute(stmt).scalars().all())


def create_booking(
    db: Session,
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
    db.commit()
    db.refresh(booking)
    return booking
