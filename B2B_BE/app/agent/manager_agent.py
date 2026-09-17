from datetime import datetime

from pydantic import BaseModel

from app.agent.availability_intent import parse_availability_change
from app.domain.availability import ProposedAvailabilityChange
from app.domain.dashboard_access import decline_staff_dashboard_request
from app.models.staff import StaffRole
from app.tools.staff import resolve_staff_identity

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


def respond_to_dashboard_request(speaker: SpeakerContext) -> str | None:
    """Consult the FR-29 guard for an already-resolved Manager Agent speaker.

    Hook point a future conversational Manager Agent loop calls once an incoming message has
    been classified as asking for the staff list, another staff member's schedule, or
    dashboard-equivalent data (that classification step does not exist yet — see the FR-29
    implementation plan's Out of Scope). Returns the decline string to send back verbatim when
    not ``None``; returns ``None`` when the request should proceed (Owner/Admin).
    """
    return decline_staff_dashboard_request(speaker.role)
