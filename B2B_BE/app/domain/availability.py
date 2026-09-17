from collections.abc import Sequence
from datetime import date, datetime, time, timedelta

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.appointments import StaffNotFoundError
from app.models.availability import Availability
from app.repositories.availability import create_availability
from app.repositories.staff_repository import get_staff_by_name

# FR-7 slot grid (Technical Context assumption #1): a fixed salon-operating-
# hours window and slot granularity, since no working-hours/slot-duration
# concept exists anywhere else in the data model yet. Module-level constants
# rather than a config/env value or new DB entity — see the implementation
# plan's Risks for the explicit flag on this assumption.
_SALON_OPENING_TIME = time(9, 0)
_SALON_CLOSING_TIME = time(18, 0)
_SLOT_DURATION_MINUTES = 30


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


def _generate_slot_grid(day: date) -> list[datetime]:
    """Generate every slot-grid start time on ``day`` (FR-7).

    One entry per ``_SLOT_DURATION_MINUTES`` boundary from
    ``_SALON_OPENING_TIME`` up to, but never at or after,
    ``_SALON_CLOSING_TIME`` — a pure, DB-independent function so the slot
    grid itself can be exhaustively unit-tested.
    """
    slots: list[datetime] = []
    step = timedelta(minutes=_SLOT_DURATION_MINUTES)
    current = datetime.combine(day, _SALON_OPENING_TIME)
    closing = datetime.combine(day, _SALON_CLOSING_TIME)
    while current < closing:
        slots.append(current)
        current += step
    return slots


def _is_blocked_at(rows: Sequence[Availability], instant: datetime) -> bool:
    """Resolve whether ``instant`` is blocked per the latest-created covering row.

    A staff member is blocked at ``instant`` when the most-recently-created
    ``Availability`` row whose ``[start_time, end_time)`` window covers
    ``instant`` has ``blocked=True``. Rows that do not actually cover
    ``instant`` are ignored. With no covering row at all, ``instant`` is
    open by default (Technical Context assumption #2 — consistent with
    UJ-4's "open by default until blocked" framing).
    """
    covering = [row for row in rows if row.start_time <= instant < row.end_time]
    if not covering:
        return False
    latest = max(covering, key=lambda row: row.created_at)
    return latest.blocked
