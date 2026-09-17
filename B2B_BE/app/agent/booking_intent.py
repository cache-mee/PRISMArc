from datetime import UTC, datetime

import anthropic
from pydantic import BaseModel, Field

from app.config import settings

_TOOL_NAME = "extract_booking_intent"


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
    """Raised when no known service could be identified in the customer's text.

    Enforces FR-5's "a Service is required for the agent to proceed" gate — the single place
    that guarantee is checked, mirroring how ``BookingNotConfirmedError`` and
    ``StaffNotFoundError`` gate their own required preconditions in
    ``app.domain.appointments``.
    """


def _build_tool_schema() -> dict:
    return {
        "name": _TOOL_NAME,
        "description": "Record the customer's parsed booking intent.",
        "input_schema": BookingIntent.model_json_schema(),
    }


def _resolve_known_service(service_name: str, known_services: list[str]) -> str | None:
    """Case-insensitive match of the extracted service name against the real catalog."""
    lowered = service_name.strip().lower()
    for known in known_services:
        if known.strip().lower() == lowered:
            return known
    return None


def _resolve_known_staff(staff_preference: str, known_staff: list[str]) -> str | None:
    """Case-insensitive match of the extracted staff preference against bookable staff.

    Mirrors ``_resolve_known_service``, but returns ``None`` on no match rather than
    raising: ``staff_preference`` is optional (FR-5), and a non-bookable or unmatched
    name (e.g. "Ramesh", who is seeded as ``role = owner_admin``) is FR-13's known,
    unmodeled limitation — treated as if no preference had been stated, not an error.
    """
    lowered = staff_preference.strip().lower()
    for known in known_staff:
        if known.strip().lower() == lowered:
            return known
    return None


def parse_booking_intent(
    text: str,
    *,
    known_services: list[str],
    known_staff: list[str] = [],
    now: datetime | None = None,
) -> BookingIntent:
    """Parse a Customer's free-text booking request into a ``BookingIntent`` (FR-5).

    Service is required to proceed: raises ``ServiceNotStatedError`` if the text does not
    name one of ``known_services``. Date/time and staff preference stay ``None`` when not
    stated — both are optional and independently omittable per the AC.

    ``known_staff`` limits an extracted ``staff_preference`` to a bookable staff member
    (FR-13): when non-empty, the extracted preference is matched case-insensitively
    against ``known_staff`` and dropped to ``None`` on no match (e.g. a stated preference
    for a non-bookable staff member) rather than raising. When ``known_staff`` is empty
    (the default — no caller has wired it in yet), no filtering is applied and
    ``staff_preference`` is returned exactly as extracted, preserving prior behavior.

    This is a hook point: it takes the current service catalog, bookable staff list, and
    reference time as plain arguments rather than reading them itself, the same pattern
    ``ResolvedBookingCandidate`` and the other Booking/Manager Agent hook functions use
    for state not yet wired up by a real conversation loop.
    """
    reference_time = now or datetime.now(UTC)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    staff_instruction = (
        f"The salon's bookable staff are: {', '.join(known_staff)}. "
        "Only match staff_preference to one of those staff members. "
        if known_staff
        else ""
    )
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=512,
        system=(
            "You extract a salon booking intent from a customer's free-text message. "
            f"The current date/time is {reference_time.isoformat()}. "
            f"The salon's offered services are: {', '.join(known_services)}. "
            "Only match service_name to one of those services. Resolve any relative "
            "date/time phrase (e.g. 'tomorrow at 3pm') against the current date/time. "
            f"{staff_instruction}"
            "Leave requested_time and staff_preference null when the customer did not "
            "state them."
        ),
        messages=[{"role": "user", "content": text}],
        tools=[_build_tool_schema()],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
    )

    tool_use = next(block for block in response.content if block.type == "tool_use")
    intent = BookingIntent.model_validate(tool_use.input)

    resolved_service = _resolve_known_service(intent.service_name, known_services)
    if resolved_service is None:
        raise ServiceNotStatedError(
            f"Could not match a known service in the customer's request: {text!r}"
        )
    intent.service_name = resolved_service

    if known_staff and intent.staff_preference is not None:
        intent.staff_preference = _resolve_known_staff(
            intent.staff_preference, known_staff
        )

    return intent
