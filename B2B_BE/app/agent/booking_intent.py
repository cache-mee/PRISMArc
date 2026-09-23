from datetime import datetime

from pydantic import BaseModel, Field


class BookingIntent(BaseModel):
    """The Booking Agent's parsed reading of a Customer's free-text booking request (FR-5)."""

    service_name: str = Field(
        description=(
            "The salon service the customer wants, matched as closely as possible to one "
            "of the offered service names given in the prompt."
        )
    )
    requested_time: datetime | None = Field(
        default=None,
        description=(
            "The date/time the customer requested, resolved to an ISO 8601 date-time "
            "against the current date/time given in the prompt, or null if none was stated."
        ),
    )
    staff_preference: str | None = Field(
        default=None,
        description=(
            "The staff member's name the customer asked for by name, or null if none was "
            "stated."
        ),
    )


class ServiceNotStatedError(ValueError):
    """Raised when no known service could be identified in the customer's request.

    Enforces FR-5's "a Service is required for the agent to proceed" gate — the single place
    that guarantee is checked, mirroring how ``BookingNotConfirmedError`` and
    ``StaffNotFoundError`` gate their own required preconditions in
    ``app.domain.appointments``.
    """


def resolve_known_service(service_name: str, known_services: list[str]) -> str | None:
    """Case-insensitive match of a candidate service name against the real catalog."""
    lowered = service_name.strip().lower()
    for known in known_services:
        if known.strip().lower() == lowered:
            return known
    return None


def resolve_known_staff(staff_preference: str, known_staff: list[str]) -> str | None:
    """Case-insensitive match of a candidate staff preference against bookable staff.

    Mirrors ``resolve_known_service``, but returns ``None`` on no match rather than
    raising: ``staff_preference`` is optional (FR-5), and a non-bookable or unmatched
    name (e.g. "Ramesh", who is seeded as ``role = owner_admin``) is FR-13's known,
    unmodeled limitation — treated as if no preference had been stated, not an error.
    """
    lowered = staff_preference.strip().lower()
    for known in known_staff:
        if known.strip().lower() == lowered:
            return known
    return None
