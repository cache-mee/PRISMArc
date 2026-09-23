"""Booking-flow LLM tools for the Booking Agent's conversational loop (APPOINTMEN-54).

Four ``BOOKING_TOOLS`` schema entries the loop's ``provider.generate(..., tools=BOOKING_TOOLS)``
call lets the model choose between, each a thin wrapper around already-existing, unchanged
domain/agent functions (``app.agent.booking_agent.confirm_exact_match``/``list_day_slots``,
``app.domain.appointments.find_nearest_alternatives``/``confirm_and_create_booking``,
``app.domain.availability.list_open_slots_for_day``):

- ``extract_booking_intent`` — takes the structured ``BookingIntent`` (FR-5) the main loop
  model itself extracted (the live service catalog/bookable-staff lists are given to that
  model directly in its own system prompt, ``build_booking_agent_system_prompt`` — no second,
  nested LLM call parses the customer's message here), validates ``service_name``/
  ``staff_preference`` against the live catalog/staff lists, then immediately runs the SM-4a
  human-verification checkpoint (``present_intent_for_verification`` -> ``verify_booking_intent``
  -> ``require_verified_intent``).
- ``check_availability`` — resolves either a day-only listing (FR-7) or an exact-time
  check (FR-8's alternative-slot search on a miss), running the SM-4b checkpoint
  (``present_alternative_for_verification`` -> ``verify_alternative_slot`` ->
  ``require_verified_alternative_slot``) on any alternative-slot result before returning it.
- ``propose_booking`` — renders FR-6's direct-confirmation message for a resolved candidate.
  Never touches the database.
- ``confirm_booking`` — the FR-9 confirm-before-write step. ``customer_id`` is always taken
  from the passed-in ``SessionState`` (never from the model-supplied args) so a
  misbehaving/prompt-injected model cannot book — or claim — a booking under a different
  Customer's identity than the one the FR-1 identity gate already resolved for this session.

**Interim SM-4a/SM-4b auto-verify (implementation plan, Business Context):** APPOINTMEN-55
(the Manager Agent conversational loop — the only real "human operator" surface for
``verify_booking_intent``/``verify_alternative_slot``) does not exist yet. Until it does, this
module calls those verification functions itself, immediately, with ``verified=True`` and no
corrections, right after logging the checkpoint's observable moment
(the ``SM-4a checkpoint ...``/``SM-4b checkpoint ...`` log lines). This ships the checkpoint's
observable moment now; the actual human-in-the-loop review of that moment is deferred to
APPOINTMEN-55, which can swap these auto-verify calls for a real pause/resume against the same
``VerifiedBookingIntent``/``VerifiedAlternativeSlotSuggestion`` wrapper types without changing
this module's tool functions' external shape.

Registered only into ``app.agent.booking_agent``'s own ``BOOKING_TOOLS`` list — never into any
Manager Agent registry — per ``base-rules.md``'s role-scoped-tool-registry-per-agent rule.
"""

from collections.abc import Awaitable, Callable
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.booking_agent import (
    DirectConfirmationPrompt,
    confirm_exact_match,
    list_day_slots,
    present_alternative_for_verification,
    present_intent_for_verification,
)
from app.agent.booking_intent import (
    BookingIntent,
    ServiceNotStatedError,
    resolve_known_service,
    resolve_known_staff,
)
from app.agent.state.session_store import SessionState
from app.domain.alternative_slot_verification import (
    AlternativeSlotSuggestion,
    require_verified_alternative_slot,
)
from app.domain.appointments import (
    ResolvedBookingCandidate,
    confirm_and_create_booking,
    find_nearest_alternatives,
    render_alternative_slots,
    render_direct_confirmation,
)
from app.domain.availability import list_open_slots_for_day
from app.domain.booking_intent_verification import require_verified_intent
from app.tools.alternative_slot_verification import (
    VerifyAlternativeSlotArgs,
    verify_alternative_slot,
)
from app.tools.intent_verification import VerifyBookingIntentArgs, verify_booking_intent
from app.tools.services import get_service_catalog
from app.tools.staff import list_bookable_staff_names


class UnknownBookingToolError(ValueError):
    """Raised when ``dispatch_booking_tool`` is given a tool ``name`` with no matching function."""


class MissingCustomerIdError(ValueError):
    """Raised when ``confirm_booking`` is called for a session with no resolved ``customer_id``.

    Enforces the security-relevant contract that ``customer_id`` always comes from the
    session's own FR-1-resolved identity, never from the model-supplied args — a session that
    somehow reaches this tool unresolved must fail loudly rather than create a Booking with no
    (or a guessed) customer.
    """


class ExtractBookingIntentArgs(BaseModel):
    """LLM-callable tool arguments for ``extract_booking_intent`` (FR-5).

    Filled directly by the main loop model from the customer's free-text message — the
    live service catalog/bookable-staff lists it needs to do that are given to it in its
    own system prompt (``build_booking_agent_system_prompt``), the same context the old
    nested extraction call used to receive instead.
    """

    service_name: str = Field(
        description="The salon service the customer wants, matched to one of the offered "
        "service names given in the system prompt."
    )
    requested_time: datetime | None = Field(
        default=None,
        description="The date/time the customer requested, resolved against the current "
        "date/time given in the system prompt, or null if none was stated.",
    )
    staff_preference: str | None = Field(
        default=None,
        description="The staff member's name the customer asked for by name, or null if "
        "none was stated.",
    )


class CheckAvailabilityArgs(BaseModel):
    """LLM-callable tool arguments for ``check_availability``.

    Exactly one of ``requested_time`` (an exact date/time) or ``day`` (a day-only request,
    no specific time stated) is expected to be set — mirroring the day-only-vs-exact-time
    split the implementation plan's Risks table documents as a happy-flow-only
    simplification of ``BookingIntent.requested_time``'s single nullable-datetime shape.
    """

    service_name: str = Field(description="The service the customer wants to book.")
    requested_time: datetime | None = Field(
        default=None,
        description="The exact date/time requested, or null for a day-only request.",
    )
    day: date | None = Field(
        default=None,
        description="The day requested, when the customer named no specific time.",
    )
    staff_preference: str | None = Field(
        default=None, description="The staff member requested by name, or null."
    )


class ProposeBookingArgs(BaseModel):
    """LLM-callable tool arguments for ``propose_booking``."""

    service_name: str
    staff_name: str
    start_time: datetime


class ConfirmBookingArgs(BaseModel):
    """LLM-callable tool arguments for ``confirm_booking``.

    Deliberately has no ``customer_id``/``customer`` field of any kind — see the module
    docstring and ``confirm_booking`` below.
    """

    service_name: str
    staff_name: str
    start_time: datetime
    customer_confirmed: bool = Field(
        default=False,
        description=(
            "True only once the customer's own message in the conversation explicitly "
            "confirmed the proposed booking."
        ),
    )


def _build_tool_schema(
    name: str, description: str, args_model: type[BaseModel]
) -> dict:
    """Build one ``BOOKING_TOOLS`` entry, mirroring ``booking_intent.py``'s ``_build_tool_schema``."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": args_model.model_json_schema(),
        },
    }


async def extract_booking_intent(
    db: AsyncSession, state: SessionState, args: ExtractBookingIntentArgs
) -> dict:
    """Validate the model-extracted booking intent into a verified ``BookingIntent`` (FR-5, SM-4a).

    ``args`` is already structured — the main loop model filled it directly from the
    customer's message using the live catalog/staff names given in its own system prompt.
    This still re-validates ``service_name``/``staff_preference`` against the live service
    catalog/bookable-staff lists fetched here (never trusting the model's spelling/match
    unchecked), raising ``ServiceNotStatedError`` on no match, exactly as the prior
    nested-LLM-call design did — then runs the SM-4a checkpoint (interim auto-verify — see
    module docstring) before returning. ``state`` is unused here (no session-scoped value
    this tool needs) but accepted for a uniform ``dispatch_booking_tool`` call shape.
    """
    known_services = [item.name for item in await get_service_catalog(db)]
    known_staff = await list_bookable_staff_names(db)

    resolved_service = resolve_known_service(args.service_name, known_services)
    if resolved_service is None:
        raise ServiceNotStatedError(
            f"Could not match a known service in the customer's request: {args.service_name!r}"
        )

    resolved_staff_preference = args.staff_preference
    if known_staff and resolved_staff_preference is not None:
        resolved_staff_preference = resolve_known_staff(
            resolved_staff_preference, known_staff
        )

    intent = BookingIntent(
        service_name=resolved_service,
        requested_time=args.requested_time,
        staff_preference=resolved_staff_preference,
    )

    pending_intent = present_intent_for_verification(intent)
    # Interim SM-4a auto-verify (APPOINTMEN-55 not yet built) — see module docstring.
    verified_intent = verify_booking_intent(
        pending_intent, VerifyBookingIntentArgs(verified=True)
    )
    checked_intent = require_verified_intent(verified_intent)

    return checked_intent.model_dump(mode="json")


async def check_availability(
    db: AsyncSession, state: SessionState, args: CheckAvailabilityArgs
) -> dict:
    """Check live availability for an exact time (FR-8) or list a day's open slots (FR-7).

    ``args.requested_time`` set resolves the exact-time branch: available at that exact
    time (optionally restricted to ``args.staff_preference``) returns a bookable candidate;
    unavailable falls through to ``find_nearest_alternatives`` and runs the SM-4b checkpoint
    (interim auto-verify — see module docstring) on the nearest alternative before returning
    the full alternative-slot message. ``args.day`` set (no ``requested_time``) resolves the
    day-only branch via ``list_day_slots``. ``state`` is unused here but accepted for a
    uniform ``dispatch_booking_tool`` call shape.
    """
    if args.requested_time is not None:
        day = args.requested_time.date()
        slots = await list_open_slots_for_day(db, day, args.staff_preference)
        match = next(
            (
                slot
                for slot in slots
                if slot.start_time == args.requested_time
                and (
                    args.staff_preference is None
                    or slot.staff_name == args.staff_preference
                )
            ),
            None,
        )
        if match is not None:
            return {
                "available": True,
                "candidate": {
                    "service_name": args.service_name,
                    "start_time": match.start_time.isoformat(),
                    "staff_name": match.staff_name,
                },
            }

        result = await find_nearest_alternatives(
            db,
            service_name=args.service_name,
            requested_time=args.requested_time,
            staff_name=args.staff_preference,
        )
        nearest = result.alternatives[0]
        pending_suggestion = AlternativeSlotSuggestion(
            requested_time=result.requested_time,
            unavailable_reason=result.reason.value,
            alternative=ResolvedBookingCandidate(
                service_name=args.service_name,
                start_time=nearest.start_time,
                staff_name=nearest.staff_name,
            ),
        )
        pending_verification = present_alternative_for_verification(pending_suggestion)
        # Interim SM-4b auto-verify (APPOINTMEN-55 not yet built) — see module docstring.
        verified_suggestion = verify_alternative_slot(
            pending_verification, VerifyAlternativeSlotArgs(verified=True)
        )
        checked_suggestion = require_verified_alternative_slot(verified_suggestion)

        return {
            "available": False,
            "message": render_alternative_slots(result, args.service_name),
            "nearest_alternative": {
                "service_name": checked_suggestion.alternative.service_name,
                "start_time": checked_suggestion.alternative.start_time.isoformat(),
                "staff_name": checked_suggestion.alternative.staff_name,
            },
        }

    if args.day is not None:
        listing = await list_day_slots(db, args.day, args.staff_preference)
        return {
            "day": listing.day.isoformat(),
            "message": listing.message,
            "slots": [
                {
                    "start_time": slot.start_time.isoformat(),
                    "staff_name": slot.staff_name,
                }
                for slot in listing.slots
            ],
        }

    raise ValueError("check_availability requires either requested_time or day.")


async def propose_booking(
    db: AsyncSession, state: SessionState, args: ProposeBookingArgs
) -> dict:
    """Render FR-6's direct-confirmation message for a resolved candidate.

    Never touches the database — ``confirm_exact_match`` is a pure, synchronous render.
    ``db``/``state`` are unused here but accepted for a uniform ``dispatch_booking_tool``
    call shape. The system prompt instructs the model to send this message back to the
    Customer verbatim, preserving FR-6's exact confirmation wording.
    """
    candidate = ResolvedBookingCandidate(
        service_name=args.service_name,
        start_time=args.start_time,
        staff_name=args.staff_name,
    )
    prompt = confirm_exact_match(candidate)
    return {"message": prompt.message}


async def confirm_booking(
    db: AsyncSession, state: SessionState, args: ConfirmBookingArgs
) -> dict:
    """Create the Booking once the customer has explicitly confirmed (FR-9).

    ``customer_id`` always comes from ``state.customer_id`` (the FR-1 identity gate's
    result), never from ``args`` — the model has no way to supply or override it. Delegates
    the actual confirm-before-write gate to the existing, unchanged
    ``confirm_and_create_booking``, which raises ``BookingNotConfirmedError`` (propagated
    here, not caught) if ``args.customer_confirmed`` is not ``True``, without touching the
    database at all in that case.
    """
    if state.customer_id is None:
        raise MissingCustomerIdError(
            "Cannot confirm a booking for a session with no resolved customer_id."
        )

    candidate = ResolvedBookingCandidate(
        service_name=args.service_name,
        start_time=args.start_time,
        staff_name=args.staff_name,
    )
    prompt = DirectConfirmationPrompt(
        candidate=candidate,
        message=render_direct_confirmation(candidate),
        confirmed=args.customer_confirmed,
    )

    booking = await confirm_and_create_booking(
        db, prompt, customer_id=state.customer_id
    )

    return {
        "booking_id": booking.id,
        "service_name": booking.service_name,
        "staff_name": args.staff_name,
        "start_time": booking.start_time.isoformat(),
    }


BOOKING_TOOLS: list[dict] = [
    _build_tool_schema(
        "extract_booking_intent",
        "Record the customer's booking intent (service, requested time, staff preference) "
        "as structured fields, validated against the live catalog/staff lists.",
        ExtractBookingIntentArgs,
    ),
    _build_tool_schema(
        "check_availability",
        "Check live availability for an exact time, or list a day's open slots.",
        CheckAvailabilityArgs,
    ),
    _build_tool_schema(
        "propose_booking",
        "Render the direct-confirmation message for a resolved, available booking candidate.",
        ProposeBookingArgs,
    ),
    _build_tool_schema(
        "confirm_booking",
        "Create the Booking once the customer has explicitly confirmed the proposed slot.",
        ConfirmBookingArgs,
    ),
]

_TOOL_HANDLERS: dict[
    str,
    tuple[
        type[BaseModel],
        Callable[[AsyncSession, SessionState, Any], Awaitable[dict]],
    ],
] = {
    "extract_booking_intent": (ExtractBookingIntentArgs, extract_booking_intent),
    "check_availability": (CheckAvailabilityArgs, check_availability),
    "propose_booking": (ProposeBookingArgs, propose_booking),
    "confirm_booking": (ConfirmBookingArgs, confirm_booking),
}


async def dispatch_booking_tool(
    db: AsyncSession, state: SessionState, name: str, args: dict
) -> dict:
    """Route one ``ToolCall.name``/``.args`` pair to the matching booking-flow tool function.

    Raises ``UnknownBookingToolError`` if ``name`` does not match any ``BOOKING_TOOLS``
    entry, rather than silently no-op'ing on a model-hallucinated tool name.
    """
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        raise UnknownBookingToolError(f"No booking tool named {name!r}.")

    args_model, tool_function = handler
    parsed_args = args_model.model_validate(args)
    return await tool_function(db, state, parsed_args)
