"""Manager Agent turn logic.

Houses the Manager Agent stub built by APPOINTMEN-17 (FR-24, Staff identity
resolution) — ``SpeakerContext``, ``resolve_speaker``, ``describe_speaker``,
and ``build_proposed_availability_change`` — plus one addition by APPOINTMEN-16
(FR-14, Owner/Admin identity resolution):

- ``render_identity_greeting`` — the role-differentiated opening line the UX
  spec (`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/staff-owner-manager-chat.md`
  §2) defines for a resolved ``SpeakerContext``: one line for Owner/Admin,
  one for Staff. It is additive alongside ``describe_speaker`` (left
  unchanged, per APPOINTMEN-17), not a replacement for it.
"""

import logging
from datetime import datetime

from pydantic import BaseModel

from app.agent.availability_intent import parse_availability_change
from app.agent.catalog_intent import is_catalog_change_request
from app.domain.availability import ProposedAvailabilityChange
from app.domain.conflict_verification import VerifiedConflictCheck
from app.domain.conflicts import ConflictCheckResult
from app.domain.dashboard_access import decline_staff_dashboard_request
from app.domain.schedule_override import decline_staff_schedule_override
from app.models.staff import StaffRole
from app.tools.staff import resolve_staff_identity

_logger = logging.getLogger(__name__)

_ROLE_LABELS: dict[StaffRole, str] = {
    StaffRole.OWNER_ADMIN: "Owner/Admin",
    StaffRole.STAFF: "Staff",
}

_STAFF_CATALOG_BOUNDARY_REDIRECT = (
    "That's something Ramesh manages — I can help you with your own availability."
)

_ROLE_GREETINGS: dict[StaffRole, str] = {
    StaffRole.OWNER_ADMIN: "Hi {name}! Want to update the service catalog?",
    StaffRole.STAFF: "Hi {name}! Want to update your availability?",
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


def render_identity_greeting(context: SpeakerContext) -> str:
    """Render the role-differentiated opening line for a resolved speaker (FR-14).

    This is the hook point a future conversational Manager Agent loop calls
    immediately after ``resolve_speaker`` returns a match, in place of (or
    alongside) ``describe_speaker``, to produce the actual role-specific
    greeting the UX spec (§2) defines: Owner/Admin is asked about the service
    catalog, Staff is asked about their availability. It performs no I/O and
    does not itself grant any permission — enforcing what a role may actually
    do remains out of scope here, as it was for ``describe_speaker``.
    """
    template = _ROLE_GREETINGS[context.role]
    return template.format(name=context.name)


async def build_proposed_availability_change(
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
    return await parse_availability_change(message, staff_name=speaker.name, now=now)


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


async def handle_staff_catalog_boundary(speaker: SpeakerContext, message: str) -> str | None:
    """Redirect a Staff-identified speaker away from an Owner/Admin-only catalog change (FR-28).

    This is the hook point a future conversational Manager Agent loop calls once a phone
    number has already been resolved to a ``SpeakerContext`` (via ``resolve_speaker``), ahead
    of any other intent handling for the message. Returns the fixed UX-spec redirect string
    when ``speaker.role`` is ``StaffRole.STAFF`` and ``message`` is classified as a catalog-change
    request (``is_catalog_change_request``); returns ``None`` otherwise — for an Owner/Admin
    speaker (Ramesh is allowed to manage the catalog, Epic 4, not built here) or for a Staff
    message that is not a catalog-change request, in which case the caller should continue with
    other intent handling (e.g. FR-25's ``build_proposed_availability_change``).

    The returned string is always the fixed redirect copy — never templated from ``message`` or
    ``speaker.name`` — matching the "plain one-line redirect, not an error state" decision, the
    same reasoning already applied to keeping identity/content out of free text elsewhere in this
    module.
    """
    if speaker.role is StaffRole.STAFF and await is_catalog_change_request(message):
        return _STAFF_CATALOG_BOUNDARY_REDIRECT
    return None


def respond_to_dashboard_request(speaker: SpeakerContext) -> str | None:
    """Consult the FR-29 guard for an already-resolved Manager Agent speaker.

    Hook point a future conversational Manager Agent loop calls once an incoming message has
    been classified as asking for the staff list, another staff member's schedule, or
    dashboard-equivalent data (that classification step does not exist yet — see the FR-29
    implementation plan's Out of Scope). Returns the decline string to send back verbatim when
    not ``None``; returns ``None`` when the request should proceed (Owner/Admin).
    """
    return decline_staff_dashboard_request(speaker.role)


def respond_to_schedule_override_request(
    speaker: SpeakerContext, change: ProposedAvailabilityChange
) -> str | None:
    """Consult the FR-30 guard for an already-resolved speaker and proposed change.

    Hook point a future conversational Manager Agent loop calls once a
    ``ProposedAvailabilityChange`` exists (e.g. from ``build_proposed_availability_change``),
    before ever confirming or applying it. Returns the decline string to send back verbatim
    when not ``None``; returns ``None`` when the change should proceed.
    """
    return decline_staff_schedule_override(
        speaker.name, speaker.role, change.staff_name
    )
