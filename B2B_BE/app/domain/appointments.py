from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.repositories.bookings import (
    create_booking,
    get_booking_by_id,
    set_booking_status,
)
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
    """Raised when a referenced Booking id does not match any existing row."""


class BookingOwnershipError(ValueError):
    """Raised when a Booking does not belong to the requesting customer."""


class BookingAlreadyCancelledError(ValueError):
    """Raised when attempting to reschedule a Booking that is already cancelled."""


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
    db: AsyncSession,
    prompt: "DirectConfirmationPrompt",
    *,
    customer_id: int,
    commit: bool = True,
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
        commit=commit,
    )


async def reschedule_booking(
    db: AsyncSession,
    *,
    existing_booking_id: int,
    prompt: "DirectConfirmationPrompt",
    customer_id: int,
) -> Booking:
    """Cancel an existing Booking and create its replacement atomically (FR-12).

    Ends with exactly one active booking for ``customer_id``: the original
    is marked ``"cancelled"`` and the new booking is created from ``prompt``
    via the existing FR-9 confirmation gate (``confirm_and_create_booking``),
    both inside a single transaction. If the rebook half raises (e.g.
    ``BookingNotConfirmedError`` or ``StaffNotFoundError``), the transaction
    is rolled back and the original exception re-raised, so the cancellation
    of the original booking is discarded too and nothing partial persists.

    Raises ``BookingNotFoundError`` if ``existing_booking_id`` does not match
    any Booking, ``BookingOwnershipError`` if that Booking does not belong to
    ``customer_id``, and ``BookingAlreadyCancelledError`` if it is already
    cancelled.
    """
    existing_booking = await get_booking_by_id(db, existing_booking_id)
    if existing_booking is None:
        raise BookingNotFoundError(f"No Booking found for id={existing_booking_id!r}.")

    if existing_booking.customer_id != customer_id:
        raise BookingOwnershipError(
            f"Booking id={existing_booking_id!r} does not belong to "
            f"customer_id={customer_id!r}."
        )

    if existing_booking.status == "cancelled":
        raise BookingAlreadyCancelledError(
            f"Booking id={existing_booking_id!r} is already cancelled."
        )

    await set_booking_status(db, existing_booking, "cancelled", commit=False)

    try:
        new_booking = await confirm_and_create_booking(
            db, prompt, customer_id=customer_id, commit=False
        )
    except Exception:
        await db.rollback()
        raise

    await db.commit()
    await db.refresh(new_booking)
    return new_booking
