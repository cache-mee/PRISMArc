from datetime import UTC, datetime

import anthropic
from pydantic import BaseModel, Field

from app.config import settings
from app.domain.availability import ProposedAvailabilityChange

_TOOL_NAME = "extract_availability_change"


class _ExtractedAvailabilityWindow(BaseModel):
    """The LLM's parsed reading of a Staff member's free-text availability change (FR-25).

    Deliberately has no ``staff_name`` (or any other identity) field: whose schedule is being
    changed is always the already-resolved speaker (``app.agent.manager_agent.SpeakerContext``),
    never something parsed from the message text. This is what keeps FR-30's "a staff member
    cannot alter another staff member's schedule" boundary intact even against a message phrased
    as if it named someone else — the LLM is structurally unable to supply an identity here, and
    ``parse_availability_change`` below layers the caller-supplied ``staff_name`` on afterward.
    """

    start_time: datetime = Field(
        description=(
            "The start of the availability window, resolved to an ISO 8601 date-time against "
            "the current date/time given in the prompt (e.g. 'Friday morning' becomes that "
            "Friday at 09:00)."
        )
    )
    end_time: datetime = Field(
        description=(
            "The end of the availability window, resolved to an ISO 8601 date-time against the "
            "current date/time given in the prompt (e.g. 'Friday morning' becomes that Friday "
            "at 13:00; 'all of Friday' or a bare day name with no daypart becomes that day's "
            "00:00 to 23:59:59)."
        )
    )
    blocked: bool = Field(
        description=(
            "True if the staff member is blocking (marking unavailable) the window, false if "
            "they are unblocking (reopening) it."
        )
    )


def _build_tool_schema() -> dict:
    return {
        "name": _TOOL_NAME,
        "description": "Record the staff member's parsed availability change.",
        "input_schema": _ExtractedAvailabilityWindow.model_json_schema(),
    }


def parse_availability_change(
    text: str,
    *,
    staff_name: str,
    now: datetime | None = None,
) -> ProposedAvailabilityChange:
    """Parse a Staff member's free-text availability change into a ``ProposedAvailabilityChange``
    (FR-25).

    ``staff_name`` is always the caller-supplied, already-resolved speaker identity — never asked
    of the LLM and never parsed from ``text`` — so this function cannot be tricked into producing
    a change for a different staff member than the one actually speaking (see
    ``_ExtractedAvailabilityWindow``'s docstring).

    Returns the change with ``confirmed=False``: restating the change back to the staff member and
    obtaining explicit confirmation is Story 3.3, not built here. ``confirm_and_apply_availability_change``
    (``app.domain.availability``) already refuses to write an unconfirmed change.

    This is a hook point: it takes the reference time as a plain argument rather than reading it
    itself, the same pattern ``parse_booking_intent`` (``app.agent.booking_intent``) uses for state
    not yet wired up by a real conversation loop.
    """
    reference_time = now or datetime.now(UTC)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=512,
        system=(
            "You extract a staff member's availability change (block or unblock) from their "
            f"free-text message. The current date/time is {reference_time.isoformat()}. "
            "Resolve any relative day/window phrase (e.g. 'Friday morning', 'all of Friday', "
            "'Saturday') against the current date/time: 'morning' means 09:00-13:00 on that day; "
            "a bare day name with no daypart (e.g. 'all of Friday', 'Saturday') means the whole "
            "day, 00:00 to 23:59:59. Set blocked=true when the staff member is marking time "
            "unavailable (e.g. 'block out', \"I'm out\"), and blocked=false when they are "
            "reopening previously blocked time (e.g. 'unblock')."
        ),
        messages=[{"role": "user", "content": text}],
        tools=[_build_tool_schema()],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
    )

    tool_use = next(block for block in response.content if block.type == "tool_use")
    window = _ExtractedAvailabilityWindow.model_validate(tool_use.input)

    return ProposedAvailabilityChange(
        staff_name=staff_name,
        start_time=window.start_time,
        end_time=window.end_time,
        blocked=window.blocked,
        confirmed=False,
    )
