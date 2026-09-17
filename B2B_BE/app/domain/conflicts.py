from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.repositories.bookings import get_bookings_for_staff_in_window


class ConflictingBooking(BaseModel):
    """A single existing Booking that conflicts with a proposed block window."""

    booking_id: int
    start_time: datetime
    service_name: str


class ConflictCheckResult(BaseModel):
    """Outcome of checking a proposed availability-block window for conflicts.

    ``has_conflict`` is always accompanied by the specific conflicting
    booking(s) in ``conflicting_bookings`` — FR-26 requires naming the
    conflict, never a silent rejection.
    """

    has_conflict: bool
    conflicting_bookings: list[ConflictingBooking]


def check_conflicts(
    db: Session,
    *,
    staff_id: int,
    window_start: datetime,
    window_end: datetime,
) -> ConflictCheckResult:
    """Check a proposed block window against staff_id's existing bookings (FR-26).

    A conflict exists when a Booking's start_time falls inside
    [window_start, window_end). Booking has no end_time/duration field
    (no Service entity to derive one from yet), so this checks
    start-time-in-window rather than a true interval overlap — an accepted
    scope boundary, not a true overlap check.
    """
    bookings = get_bookings_for_staff_in_window(
        db, staff_id=staff_id, window_start=window_start, window_end=window_end
    )
    conflicting = [
        ConflictingBooking(
            booking_id=booking.id,
            start_time=booking.start_time,
            service_name=booking.service_name,
        )
        for booking in bookings
    ]
    return ConflictCheckResult(
        has_conflict=len(conflicting) > 0,
        conflicting_bookings=conflicting,
    )


def render_conflict_message(result: ConflictCheckResult) -> str:
    """Render a human-readable message for a ConflictCheckResult (FR-26).

    Names every conflicting booking (never just the first) when a conflict
    exists; otherwise confirms the window is clear to apply.
    """
    if not result.has_conflict:
        return "No conflicts found. This block can be applied."

    lines = [
        f"{booking.start_time.strftime('%A %I:%M %p')} is already booked "
        f"for {booking.service_name}."
        for booking in result.conflicting_bookings
    ]
    return "This block conflicts with existing bookings:\n" + "\n".join(lines)
