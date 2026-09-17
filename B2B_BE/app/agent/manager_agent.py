import logging
from datetime import datetime

from pydantic import BaseModel

from app.agent.availability_intent import parse_availability_change
from app.domain.availability import ProposedAvailabilityChange
from app.domain.conflict_verification import VerifiedConflictCheck
from app.domain.conflicts import ConflictCheckResult
from app.models.staff import StaffRole
from app.tools.staff import resolve_staff_identity

_logger = logging.getLogger(__name__)

_ROLE_LABELS: dict[StaffRole, str] = {
    StaffRole.OWNER_ADMIN: "Owner/Admin",
    StaffRole.STAFF: "Staff",
}


class SpeakerContext(BaseModel):
    """The unambiguous "who is speaking" result for a resolved phone number."""

    id: int
    name: str
    role: StaffRole


async def resolve_speaker(phone_number: str) -> SpeakerContext | None:
    """Resolve which Staff member is speaking, from their phone number.

    This is the hook point a future conversational Manager Agent loop calls
    once a phone number has been collected from the user. Returns None when
    the phone number does not match any pre-seeded Staff record.
    """
    identity = await resolve_staff_identity(phone_number)
    if identity is None:
        return None
    return SpeakerContext(id=identity.id, name=identity.name, role=identity.role)


def describe_speaker(context: SpeakerContext) -> str:
    """Render an unambiguous statement of which Staff member is speaking."""
    role_label = _ROLE_LABELS[context.role]
    return f"Recognized as {context.name} ({role_label})."


def build_proposed_availability_change(
    speaker: SpeakerContext,
    message: str,
    *,
    now: datetime | None = None,
) -> ProposedAvailabilityChange:
    """Turn a resolved Staff speaker's free-text message into a proposed change (FR-25).

    This is the hook point a future conversational Manager Agent loop calls once a phone
    number has already been resolved to a ``SpeakerContext`` (via ``resolve_speaker``) and
    the message has been identified as a block/unblock request. ``speaker.name`` — never
    anything parsed from ``message`` — is always the staff member the resulting
    ``ProposedAvailabilityChange`` is attributed to, which is what keeps FR-30's "a staff
    member cannot alter another staff member's schedule" boundary intact.

    Returns the change with ``confirmed=False`` unchanged from
    ``parse_availability_change``: restating the change back to the staff member for
    explicit confirmation is Story 3.3, not built here.
    """
    return parse_availability_change(message, staff_name=speaker.name, now=now)


def present_conflict_check_for_verification(
    result: ConflictCheckResult,
) -> VerifiedConflictCheck:
    """Surface a freshly-run ``ConflictCheckResult`` for the SM-4c checkpoint (APPOINTMEN-32).

    This is the hook point a future conversational Manager Agent loop will call
    immediately after ``check_conflicts`` (``app.domain.conflicts``), before any code calls
    ``confirm_and_apply_availability_change()``. Not customer- or staff-visible — it logs the
    conflict-detection outcome as the observable checkpoint moment and returns an unverified
    ``VerifiedConflictCheck``; a human operator/judge reviews the logged outcome and sets
    ``verified`` to ``True`` before
    ``app.domain.conflict_verification.require_verified_conflict_check`` will let it through.
    """
    _logger.info(
        "SM-4c checkpoint - conflict-check outcome awaiting human verification: "
        "has_conflict=%r conflicting_bookings=%r",
        result.has_conflict,
        [
            {"booking_id": booking.booking_id, "start_time": booking.start_time}
            for booking in result.conflicting_bookings
        ],
    )
    return VerifiedConflictCheck(result=result)
