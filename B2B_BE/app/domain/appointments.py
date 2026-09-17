from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.repositories.bookings import create_booking, get_bookings_with_staff_for_customer
from app.repositories.staff_repository import get_staff_by_name

if TYPE_CHECKING:
    from app.agent.booking_agent import DirectConfirmationPrompt


class BookingNotConfirmedError(ValueError):
    """Raised when a Booking write is attempted without an explicit confirmation.

    Enforces FR-9: no Booking record may be created until
    ``DirectConfirmationPrompt.confirmed`` is ``True``.
    """


class StaffNotFoundError(ValueError):
    """Raised when the candidate's ``staff_name`` cannot be resolved to a Staff row."""


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


async def confirm_and_create_booking(
    db: AsyncSession, prompt: "DirectConfirmationPrompt", *, customer_id: int
) -> Booking:
    """Create a Booking row from a confirmed direct-confirmation prompt (FR-9).

    Raises ``BookingNotConfirmedError`` if ``prompt.confirmed`` is not
    ``True`` rather than touching the database at all — this is the single
    place FR-9's guarantee ("no Booking record exists until an explicit
    confirmation follows a proposed slot") is enforced.

    Two resolution gaps beyond the plan's exact wording, both necessary
    because ``ResolvedBookingCandidate`` (APPOINTMEN-22) carries neither a
    customer nor a resolved ``staff_id``:

    - ``customer_id`` is accepted as an explicit keyword argument here,
      supplied by the caller. No conversation-state/session mechanism exists
      yet to derive it automatically from the prompt.
    - ``staff_id`` is resolved from ``prompt.candidate.staff_name`` via the
      new ``get_staff_by_name`` lookup in
      ``app.repositories.staff_repository``. Raises ``StaffNotFoundError``
      if no Staff row matches that name.
    """
    if prompt.confirmed is not True:
        raise BookingNotConfirmedError(
            "Cannot create a Booking from an unconfirmed DirectConfirmationPrompt."
        )

    candidate = prompt.candidate
    staff = await get_staff_by_name(db, candidate.staff_name)
    if staff is None:
        raise StaffNotFoundError(
            f"No Staff record found for staff_name={candidate.staff_name!r}."
        )

    return await create_booking(
        db,
        customer_id=customer_id,
        staff_id=staff.id,
        service_name=candidate.service_name,
        start_time=candidate.start_time,
    )


class BookingHistoryItem(BaseModel):
    """One booking as shown in a Customer's history (FR-10)."""

    booking_id: int
    service_name: str
    staff_name: str
    start_time: datetime
    status: str


class BookingHistory(BaseModel):
    """A Customer's bookings, split into upcoming and past (FR-10)."""

    upcoming: list[BookingHistoryItem]
    past: list[BookingHistoryItem]


async def get_booking_history(db: AsyncSession, *, customer_id: int) -> BookingHistory:
    """Return customer_id's own booking history, split into upcoming/past.

    Reads through app.repositories.bookings.get_bookings_with_staff_for_customer
    (the sole enforcement point for "never another customer's bookings"), then
    partitions the rows using datetime.now(UTC) as the boundary: a start_time
    at or after now is "upcoming", otherwise "past". This is the single place
    FR-10's "distinguishes upcoming from past" AC is satisfied, decoupled from
    any specific transport — both the REST endpoint and the future Booking
    Agent tool call this unchanged.
    """
    rows = await get_bookings_with_staff_for_customer(db, customer_id=customer_id)
    now = datetime.now(UTC)

    upcoming: list[BookingHistoryItem] = []
    past: list[BookingHistoryItem] = []
    for booking, staff_name in rows:
        item = BookingHistoryItem(
            booking_id=booking.id,
            service_name=booking.service_name,
            staff_name=staff_name,
            start_time=booking.start_time,
            status=booking.status,
        )
        if booking.start_time >= now:
            upcoming.append(item)
        else:
            past.append(item)

    return BookingHistory(upcoming=upcoming, past=past)
