from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.repositories.bookings import cancel_booking, create_booking, get_booking_by_id
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


class BookingNotFoundError(ValueError):
    """Raised when a ``booking_id`` does not resolve to any Booking row."""


class BookingNotOwnedError(ValueError):
    """Raised when the resolved Booking's ``customer_id`` does not match the caller's."""


class BookingAlreadyCancelledError(ValueError):
    """Raised when the resolved Booking's ``status`` is already ``"cancelled"``."""


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


async def cancel_customer_booking(
    db: AsyncSession, *, booking_id: int, customer_id: int
) -> Booking:
    """Cancel an existing Booking on behalf of the requesting Customer (FR-11).

    Resolves ``booking_id`` via ``get_booking_by_id`` and raises rather than
    silently no-op'ing when the request cannot be satisfied:

    - ``BookingNotFoundError`` if ``booking_id`` does not resolve to any row.
    - ``BookingNotOwnedError`` if the resolved booking's ``customer_id`` does
      not match ``customer_id``.
    - ``BookingAlreadyCancelledError`` if the resolved booking's ``status``
      is already ``"cancelled"``.

    Otherwise immediately delegates to ``cancel_booking`` and returns the
    updated row. Per the ticket's explicit note (unlike FR-9/FR-18/FR-27),
    there is no confirmation flag or confirmation step here — cancellation
    executes on request.
    """
    booking = await get_booking_by_id(db, booking_id)
    if booking is None:
        raise BookingNotFoundError(
            f"No Booking record found for booking_id={booking_id!r}."
        )

    if booking.customer_id != customer_id:
        raise BookingNotOwnedError(
            f"Booking booking_id={booking_id!r} is not owned by customer_id={customer_id!r}."
        )

    if booking.status == "cancelled":
        raise BookingAlreadyCancelledError(
            f"Booking booking_id={booking_id!r} is already cancelled."
        )

    cancelled = await cancel_booking(db, booking_id=booking_id)
    assert cancelled is not None  # booking_id was just resolved above
    return cancelled
