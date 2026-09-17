from pydantic import BaseModel

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


def resolve_speaker(phone_number: str) -> SpeakerContext | None:
    """Resolve which Staff member is speaking, from their phone number.

    This is the hook point a future conversational Manager Agent loop calls
    once a phone number has been collected from the user. Returns None when
    the phone number does not match any pre-seeded Staff record.
    """
    identity = resolve_staff_identity(phone_number)
    if identity is None:
        return None
    return SpeakerContext(id=identity.id, name=identity.name, role=identity.role)


def describe_speaker(context: SpeakerContext) -> str:
    """Render an unambiguous statement of which Staff member is speaking."""
    role_label = _ROLE_LABELS[context.role]
    return f"Recognized as {context.name} ({role_label})."
