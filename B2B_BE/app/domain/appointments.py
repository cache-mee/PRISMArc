from datetime import datetime

from pydantic import BaseModel


class ResolvedBookingCandidate(BaseModel):
    """An already-resolved, already-available booking slot.

    Availability and staff assignment are assumed already resolved by
    upstream (not-yet-built) logic by the time this model is constructed.
    """

    service_name: str
    start_time: datetime
    staff_name: str


def render_direct_confirmation(candidate: ResolvedBookingCandidate) -> str:
    """Render the FR-6 direct-confirmation message for a resolved candidate.

    Names the service, date/time, and assigned staff, and explicitly asks
    the Customer to confirm before any Booking is created.
    """
    formatted_time = candidate.start_time.strftime("%A, %B %d at %I:%M %p")
    return (
        f"I can book {candidate.service_name} with {candidate.staff_name} on "
        f"{formatted_time}. Shall I go ahead and confirm this booking?"
    )
