from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.appointments import StaffNotFoundError
from app.models.availability import Availability
from app.repositories.availability import create_availability
from app.repositories.staff_repository import get_staff_by_name


class AvailabilityChangeNotConfirmedError(ValueError):
    """Raised when an Availability write is attempted without an explicit confirmation.

    Enforces FR-27: no Availability record may be created until
    ``ProposedAvailabilityChange.confirmed`` is ``True``.
    """


class ProposedAvailabilityChange(BaseModel):
    """An already-restated block/unblock change awaiting explicit confirmation.

    Mirrors ``DirectConfirmationPrompt``'s shape: the upstream conversational
    step (Story 3.3, not built here) is responsible for restating the change
    to Meena or Arjun and setting ``confirmed`` to ``True`` once they agree.
    """

    staff_name: str
    start_time: datetime
    end_time: datetime
    blocked: bool
    confirmed: bool = False


async def confirm_and_apply_availability_change(
    db: AsyncSession, change: ProposedAvailabilityChange
) -> Availability:
    """Create an Availability row from a confirmed proposed change (FR-27).

    Raises ``AvailabilityChangeNotConfirmedError`` if ``change.confirmed`` is
    not ``True`` rather than touching the database at all — this is the
    single place FR-27's guarantee ("no availability record changes until an
    explicit confirmation follows the agent's restated version") is enforced.

    ``staff_id`` is resolved from ``change.staff_name`` via the existing
    ``get_staff_by_name`` (``app.repositories.staff_repository``), reusing
    the existing ``StaffNotFoundError`` (``app.domain.appointments``) if no
    match is found, rather than defining a duplicate exception type for an
    identical failure mode.
    """
    if change.confirmed is not True:
        raise AvailabilityChangeNotConfirmedError(
            "Cannot apply an unconfirmed ProposedAvailabilityChange."
        )

    staff = await get_staff_by_name(db, change.staff_name)
    if staff is None:
        raise StaffNotFoundError(
            f"No Staff record found for staff_name={change.staff_name!r}."
        )

    return await create_availability(
        db,
        staff_id=staff.id,
        start_time=change.start_time,
        end_time=change.end_time,
        blocked=change.blocked,
    )
