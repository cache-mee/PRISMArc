from datetime import datetime

from pydantic import BaseModel

from app.agent.availability_intent import parse_availability_change
from app.agent.catalog_intent import is_catalog_change_request
from app.domain.availability import ProposedAvailabilityChange
from app.models.staff import StaffRole
from app.tools.staff import resolve_staff_identity

_ROLE_LABELS: dict[StaffRole, str] = {
    StaffRole.OWNER_ADMIN: "Owner/Admin",
    StaffRole.STAFF: "Staff",
}

_STAFF_CATALOG_BOUNDARY_REDIRECT = (
    "That's something Ramesh manages — I can help you with your own availability."
)


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


def handle_staff_catalog_boundary(speaker: SpeakerContext, message: str) -> str | None:
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
    if speaker.role is StaffRole.STAFF and is_catalog_change_request(message):
        return _STAFF_CATALOG_BOUNDARY_REDIRECT
    return None
