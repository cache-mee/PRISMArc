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

from datetime import datetime

from pydantic import BaseModel

from app.agent.availability_intent import parse_availability_change
from app.domain.availability import ProposedAvailabilityChange
from app.models.staff import StaffRole
from app.tools.staff import resolve_staff_identity

_ROLE_LABELS: dict[StaffRole, str] = {
    StaffRole.OWNER_ADMIN: "Owner/Admin",
    StaffRole.STAFF: "Staff",
}

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
