from datetime import datetime, time, timedelta
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.conflicts import check_conflicts
from app.models.booking import Booking
from app.models.staff import Staff
from app.repositories.availability import get_blocking_availability_for_staff_in_window
from app.repositories.bookings import create_booking
from app.repositories.staff_repository import get_staff_by_name, list_bookable_staff

if TYPE_CHECKING:
    from app.agent.booking_agent import DirectConfirmationPrompt

# FR-8 (find_nearest_alternatives): a Service-duration column does not exist
# on Booking, so this stands in for a per-service duration — the same
# accepted gap FR-26's check_conflicts already documents for itself.
_SLOT_GRANULARITY = timedelta(minutes=30)

# FR-8: no working-hours/business-hours domain entity exists yet (no such
# table in stack/rules/base-rules.md's Database tables list). These bound
# the alternative-slot search to a hardcoded window on requested_time's own
# calendar date — an explicit, documented simplification, not a modeled
# entity. An Architect decision to model real salon/staff hours would
# supersede these constants without changing find_nearest_alternatives's
# external contract.
_BUSINESS_HOURS_START = time(9, 0)
_BUSINESS_HOURS_END = time(19, 0)

# FR-8: matches the UX spec's own two-option example
# (customer-booking-chat.md §3.3).
_MAX_ALTERNATIVES = 2


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


class UnavailabilityReason(str, Enum):
    """Why a requested_time turned out unavailable (FR-8)."""

    ALREADY_BOOKED = "already_booked"
    BLOCKED = "blocked"


class AlternativeSlot(BaseModel):
    """A single free (staff, time) pair offered as an FR-8 alternative."""

    staff_name: str
    start_time: datetime


class NearestAlternativesResult(BaseModel):
    """The outcome of an FR-8 nearest-alternative(s) search."""

    requested_time: datetime
    staff_name: str | None
    reason: UnavailabilityReason
    alternatives: list[AlternativeSlot]


class NoAlternativeSlotFoundError(ValueError):
    """Raised when the bounded business-hours search finds zero free slots.

    An explicit typed failure rather than returning an empty, misleading
    "success" result — FR-8's AC guarantees at least one alternative slot,
    so a search that cannot meet it must say so, not silently return an
    empty ``NearestAlternativesResult``.
    """


async def _determine_unavailability_reason(
    db: AsyncSession, candidates: list[Staff], requested_time: datetime
) -> UnavailabilityReason:
    """Determine why requested_time is unavailable across candidates (FR-8).

    ``ALREADY_BOOKED`` takes priority over ``BLOCKED`` when candidates
    disagree — more specific/actionable to the Customer than "blocked" —
    per the salon-wide reason-attribution rule in the APPOINTMEN-24
    implementation plan's Technical Context. Not a per-candidate breakdown,
    a deliberate simplification for this hackathon's happy-flow-only scope.
    """
    window_end = requested_time + _SLOT_GRANULARITY
    remaining: list[Staff] = []
    for staff in candidates:
        conflict = await check_conflicts(
            db, staff_id=staff.id, window_start=requested_time, window_end=window_end
        )
        if conflict.has_conflict:
            return UnavailabilityReason.ALREADY_BOOKED
        remaining.append(staff)

    for staff in remaining:
        blocking = await get_blocking_availability_for_staff_in_window(
            db, staff_id=staff.id, window_start=requested_time, window_end=window_end
        )
        if blocking:
            return UnavailabilityReason.BLOCKED

    # No candidate is actually booked or blocked at requested_time. This
    # function is only ever called once the caller already knows
    # requested_time is unavailable, so this branch is not expected in
    # practice; BLOCKED is the safer default here (a false "already booked"
    # claim would be actively misleading to the Customer).
    return UnavailabilityReason.BLOCKED


async def _search_nearest_alternatives(
    db: AsyncSession, candidates: list[Staff], requested_time: datetime
) -> list[AlternativeSlot]:
    """Step outward from requested_time to find free (staff, time) pairs (FR-8).

    Steps in ``_SLOT_GRANULARITY`` increments, alternating later then
    earlier, bounded to ``[_BUSINESS_HOURS_START, _BUSINESS_HOURS_END)`` on
    requested_time's own calendar date, until up to ``_MAX_ALTERNATIVES``
    free slots are found or the business-hours bound is exhausted in both
    directions. A slot is "free" for a candidate when neither
    ``check_conflicts`` (FR-26) nor
    ``get_blocking_availability_for_staff_in_window`` (Task 2) finds
    anything for that candidate in ``[slot_time, slot_time +
    _SLOT_GRANULARITY)``.
    """
    day = requested_time.date()
    business_start = datetime.combine(
        day, _BUSINESS_HOURS_START, tzinfo=requested_time.tzinfo
    )
    business_end = datetime.combine(
        day, _BUSINESS_HOURS_END, tzinfo=requested_time.tzinfo
    )

    alternatives: list[AlternativeSlot] = []
    step = 1
    while len(alternatives) < _MAX_ALTERNATIVES:
        later = requested_time + step * _SLOT_GRANULARITY
        earlier = requested_time - step * _SLOT_GRANULARITY
        later_in_bounds = business_start <= later < business_end
        earlier_in_bounds = business_start <= earlier < business_end
        if not later_in_bounds and not earlier_in_bounds:
            break

        for slot_time, in_bounds in (
            (later, later_in_bounds),
            (earlier, earlier_in_bounds),
        ):
            if not in_bounds:
                continue
            slot_window_end = slot_time + _SLOT_GRANULARITY
            for staff in candidates:
                conflict = await check_conflicts(
                    db,
                    staff_id=staff.id,
                    window_start=slot_time,
                    window_end=slot_window_end,
                )
                if conflict.has_conflict:
                    continue
                blocking = await get_blocking_availability_for_staff_in_window(
                    db,
                    staff_id=staff.id,
                    window_start=slot_time,
                    window_end=slot_window_end,
                )
                if blocking:
                    continue
                alternatives.append(
                    AlternativeSlot(staff_name=staff.name, start_time=slot_time)
                )
                if len(alternatives) >= _MAX_ALTERNATIVES:
                    break
            if len(alternatives) >= _MAX_ALTERNATIVES:
                break

        step += 1

    return alternatives


async def find_nearest_alternatives(
    db: AsyncSession,
    *,
    service_name: str,
    requested_time: datetime,
    staff_name: str | None = None,
) -> NearestAlternativesResult:
    """Find the nearest bookable alternative(s) to requested_time, with a reason (FR-8).

    Mirrors ``confirm_exact_match``'s layering (domain function, called by an
    agent-layer hook point) but, unlike it, is ``async`` and performs its own
    DB work — nothing upstream can hand this a pre-resolved alternative;
    resolving one against ``bookings``/``availability``/``staff`` is exactly
    this function's job.

    ``staff_name`` given resolves to that single Staff record via
    ``get_staff_by_name``, raising the existing ``StaffNotFoundError`` if no
    match (the same exception ``confirm_and_create_booking`` already raises
    for the same failure mode). ``staff_name`` is ``None`` (no stated
    preference) searches ``list_bookable_staff`` salon-wide.

    Raises ``NoAlternativeSlotFoundError`` if the bounded business-hours
    search (see the module-level constants above) finds zero free slots.
    """
    if staff_name is not None:
        staff = await get_staff_by_name(db, staff_name)
        if staff is None:
            raise StaffNotFoundError(
                f"No Staff record found for staff_name={staff_name!r}."
            )
        candidates = [staff]
    else:
        candidates = await list_bookable_staff(db)

    reason = await _determine_unavailability_reason(db, candidates, requested_time)
    alternatives = await _search_nearest_alternatives(db, candidates, requested_time)

    if not alternatives:
        raise NoAlternativeSlotFoundError(
            f"No free slot found for {service_name!r} within business hours on "
            f"{requested_time.date()}."
        )

    return NearestAlternativesResult(
        requested_time=requested_time,
        staff_name=staff_name,
        reason=reason,
        alternatives=alternatives,
    )
