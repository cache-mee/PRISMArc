from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.appointments import StaffNotFoundError
from app.models.availability import Availability
from app.models.staff import StaffRole
from app.repositories.availability import (
    create_availability,
    list_availability_for_staff_on_day,
)
from app.repositories.bookings import list_confirmed_bookings_for_staff_on_day
from app.repositories.staff_repository import get_staff_by_name, list_bookable_staff

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

    Explicitly UTC-aware (not naive): ``_is_blocked_at`` compares these
    against ``Availability.start_time``/``end_time``, which are
    ``DateTime(timezone=True)`` columns — psycopg/Postgres hands back
    timezone-aware datetimes for those, and Python raises ``TypeError`` on a
    naive-vs-aware comparison. Every other ``_is_blocked_at`` caller
    (``is_staff_blocked_now``) already passes an aware ``datetime.now(UTC)``.
    """
    slots: list[datetime] = []
    step = timedelta(minutes=_SLOT_DURATION_MINUTES)
    current = datetime.combine(day, _SALON_OPENING_TIME, tzinfo=UTC)
    closing = datetime.combine(day, _SALON_CLOSING_TIME, tzinfo=UTC)
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


async def is_staff_blocked_now(
    db: AsyncSession, *, staff_id: int, now: datetime | None = None
) -> bool:
    """Whether staff_id is blocked right now (FR-19's Dashboard status pill).

    A thin public wrapper: defaults ``now`` to ``datetime.now(UTC)``, fetches
    that day's ``Availability`` rows via the existing
    ``list_availability_for_staff_on_day``, and delegates to the existing
    ``_is_blocked_at`` rule — so the Dashboard's status pill and FR-7's own
    slot-search block resolution can never disagree (single source of truth,
    not a second implementation of the same rule).
    """
    if now is None:
        now = datetime.now(UTC)
    rows = await list_availability_for_staff_on_day(
        db, staff_id=staff_id, day=now.date()
    )
    return _is_blocked_at(rows, now)


class OpenSlot(BaseModel):
    """A single open, bookable slot resolved for a day (FR-7)."""

    staff_name: str
    start_time: datetime


async def list_open_slots_for_day(
    db: AsyncSession, day: date, staff_name: str | None = None
) -> list[OpenSlot]:
    """List every currently-open, bookable slot on ``day`` (FR-7).

    Resolves candidate staff first: a stated ``staff_name`` is looked up via
    ``get_staff_by_name`` and restricted to ``StaffRole.STAFF``, raising the
    existing ``StaffNotFoundError`` (``app.domain.appointments``, reused the
    same way FR-27's ``confirm_and_apply_availability_change`` already does)
    if unmatched or not bookable; with no ``staff_name`` stated, every
    bookable staff member (``list_bookable_staff``) is a candidate.

    For each candidate staff member, builds the day's slot grid
    (``_generate_slot_grid``), excludes any slot blocked per
    ``_is_blocked_at`` against that staff's ``Availability`` rows, and
    excludes any slot matching a confirmed ``Booking``'s exact
    ``start_time``. The remaining slots are returned sorted by
    ``start_time`` then ``staff_name``.
    """
    if staff_name is not None:
        staff = await get_staff_by_name(db, staff_name)
        if staff is None or staff.role != StaffRole.STAFF:
            raise StaffNotFoundError(
                f"No bookable Staff record found for staff_name={staff_name!r}."
            )
        candidate_staff = [staff]
    else:
        candidate_staff = await list_bookable_staff(db)

    grid = _generate_slot_grid(day)
    open_slots: list[OpenSlot] = []
    for staff in candidate_staff:
        availability_rows = await list_availability_for_staff_on_day(
            db, staff_id=staff.id, day=day
        )
        confirmed_bookings = await list_confirmed_bookings_for_staff_on_day(
            db, staff_id=staff.id, day=day
        )
        booked_start_times = {booking.start_time for booking in confirmed_bookings}

        for slot in grid:
            if _is_blocked_at(availability_rows, slot):
                continue
            if slot in booked_start_times:
                continue
            open_slots.append(OpenSlot(staff_name=staff.name, start_time=slot))

    open_slots.sort(key=lambda slot: (slot.start_time, slot.staff_name))
    return open_slots


def render_day_slot_list(day: date, slots: list[OpenSlot]) -> str:
    """Render the FR-7 Customer-facing listing of a day's open slots.

    Mirrors ``render_direct_confirmation``'s shape (``app.domain.appointments``):
    a plain, ready-to-send string naming the day and each slot's time/staff.
    Falls back to a minimal literal message when ``slots`` is empty — the
    only zero-availability UX this ticket provides (see the plan's Out of
    Scope).

    Renders as a numbered plain-text list with a trailing reply prompt, per
    ``whatsapp-deltas.md`` §1's FR-7 example — this is a shared,
    channel-agnostic renderer with no ``channel`` parameter, so both Web
    Chat and WhatsApp get the same numbered format once wired.
    """
    formatted_day = day.strftime("%A, %B %d")
    if not slots:
        return f"Sorry, I don't have any open slots on {formatted_day}."

    lines = [f"Here are the open slots on {formatted_day}:"]
    for index, slot in enumerate(slots, start=1):
        formatted_time = slot.start_time.strftime("%I:%M %p")
        lines.append(f"{index}) {formatted_time} with {slot.staff_name}")
    lines.append("Reply with a number or a time.")
    return "\n".join(lines)
