"""Role-scoped tool registry for the Manager Agent's tool-calling loop (APPOINTMEN-55).

The first real per-role tool registry in this codebase (see the implementation
plan's Technical Context design-decision section). Existing guard functions
(``decline_staff_dashboard_request``, ``decline_owner_admin_own_availability_request``,
``decline_staff_schedule_override``, ``handle_staff_catalog_boundary``) gate an
*already-chosen* action; they say nothing about which actions a role is even
*offered* in the first place. ``stack/rules/base-rules.md``'s Architecture
Constraints require that "a tool a role should not be able to invoke MUST
simply not be registered into that role's registry for that session" — this
module is that registry. It does not replace or modify the existing guard
functions, which remain in force as defense-in-depth for any code path
outside the loop this registry serves.

Defines:
- ``ToolSpec`` — one registrable tool: its name, its LLM function-calling
  schema dict (the ``{"type": "function", "function": {...}}`` shape
  ``app.agent.providers.base.LLMProvider.generate``'s ``tools`` parameter
  expects — confirmed against ``app/tools/booking_flow.py``'s existing
  ``_build_tool_schema`` helper, the only other call site that builds this
  shape today), and an async ``dispatch`` callable.
- ``STAFF_TOOLS`` / ``OWNER_ADMIN_TOOLS`` — the two per-role tool lists.
- ``get_tools_for_role`` — the single lookup the loop (Task 6) calls.
- The dispatch adapters bridging an LLM tool call's flat ``args`` dict to the
  existing ``(pending, args)``-shaped ``verify_booking_intent`` /
  ``verify_alternative_slot`` / ``verify_conflict_check`` functions, using
  ``app.agent.state.pending_verification_store`` (Task 2) to supply
  ``pending`` and to clear the verified item back out afterward — mirroring
  how ``app.tools.availability_change.confirm_availability_change`` (Task 3)
  clears its own pending slot once acted on.

Every ``ToolSpec.dispatch`` callable shares one uniform, keyword-only
signature — ``async def dispatch(*, db, session_id, speaker, args) -> dict``
— even though individual tools only need a subset of those (the verification
tools never touch ``db``; ``propose_availability_change`` doesn't either).
A single shape lets the future loop (Task 6) call every tool identically
without needing to know which underlying function needs what.
"""

from typing import Any, Awaitable, Callable

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.manager_agent import SpeakerContext
from app.agent.state import pending_verification_store
from app.models.staff import StaffRole
from app.tools.alternative_slot_verification import (
    VerifyAlternativeSlotArgs,
    verify_alternative_slot,
)
from app.tools.availability_change import (
    ConfirmAvailabilityChangeArgs,
    ProposeAvailabilityChangeArgs,
    confirm_availability_change,
    propose_availability_change,
)
from app.tools.conflict_verification import (
    VerifyConflictCheckArgs,
    verify_conflict_check,
)
from app.tools.intent_verification import (
    VerifyBookingIntentArgs,
    verify_booking_intent,
)

DispatchFn = Callable[..., Awaitable[dict]]


class ToolSpec:
    """One registrable tool offered to the model for a given role's session.

    ``schema`` is the exact dict placed into ``LLMProvider.generate``'s
    ``tools`` list; ``dispatch`` is the async callable the loop invokes when
    the model calls this tool by ``name``.
    """

    def __init__(self, name: str, schema: dict, dispatch: DispatchFn) -> None:
        self.name = name
        self.schema = schema
        self.dispatch = dispatch


def _build_tool_schema(
    name: str, description: str, args_model: type[BaseModel]
) -> dict:
    """Build the OpenAI function-calling schema dict for one tool.

    Matches ``app.tools.booking_flow``'s existing ``_build_tool_schema``
    shape exactly — the same shape
    ``LLMProvider.generate``'s ``tools`` parameter documents itself as
    expecting (``app/agent/providers/base.py``).
    """
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": args_model.model_json_schema(),
        },
    }


async def _dispatch_verify_booking_intent(
    *,
    db: AsyncSession | None,
    session_id: str,
    speaker: SpeakerContext,
    args: dict[str, Any],
) -> dict:
    """Adapt an LLM ``verify_booking_intent`` tool call to the underlying function.

    Reads the current pending SM-4a item from
    ``pending_verification_store`` (there is nothing else a flat tool-call
    ``args`` dict could supply it from), calls the existing
    ``(pending, args)``-shaped ``verify_booking_intent``, clears the pending
    slot, and returns a JSON-serializable dict. Returns a clear
    "nothing pending" result instead of raising when nothing is pending.
    """
    pending = pending_verification_store.get_pending_booking_intent()
    if pending is None:
        return {
            "error": "nothing_pending",
            "message": "No pending booking intent is awaiting verification.",
        }
    verified = verify_booking_intent(
        pending, VerifyBookingIntentArgs.model_validate(args)
    )
    pending_verification_store.set_pending_booking_intent(None)
    return verified.model_dump(mode="json")


async def _dispatch_verify_alternative_slot(
    *,
    db: AsyncSession | None,
    session_id: str,
    speaker: SpeakerContext,
    args: dict[str, Any],
) -> dict:
    """Adapt an LLM ``verify_alternative_slot`` tool call to the underlying function.

    Mirrors ``_dispatch_verify_booking_intent`` for the SM-4b pending item.
    """
    pending = pending_verification_store.get_pending_alternative_slot()
    if pending is None:
        return {
            "error": "nothing_pending",
            "message": "No pending alternative-slot suggestion is awaiting verification.",
        }
    verified = verify_alternative_slot(
        pending, VerifyAlternativeSlotArgs.model_validate(args)
    )
    pending_verification_store.set_pending_alternative_slot(None)
    return verified.model_dump(mode="json")


async def _dispatch_verify_conflict_check(
    *,
    db: AsyncSession | None,
    session_id: str,
    speaker: SpeakerContext,
    args: dict[str, Any],
) -> dict:
    """Adapt an LLM ``verify_conflict_check`` tool call to the underlying function.

    Mirrors ``_dispatch_verify_booking_intent`` for the SM-4c pending item.
    """
    pending = pending_verification_store.get_pending_conflict_check()
    if pending is None:
        return {
            "error": "nothing_pending",
            "message": "No pending conflict check is awaiting verification.",
        }
    verified = verify_conflict_check(
        pending, VerifyConflictCheckArgs.model_validate(args)
    )
    pending_verification_store.set_pending_conflict_check(None)
    return verified.model_dump(mode="json")


async def _dispatch_propose_availability_change(
    *,
    db: AsyncSession | None,
    session_id: str,
    speaker: SpeakerContext,
    args: dict[str, Any],
) -> dict:
    """Adapt an LLM ``propose_availability_change`` tool call to Task 3's tool.

    ``db`` is accepted for signature uniformity but unused —
    ``propose_availability_change`` performs no write.
    """
    return await propose_availability_change(
        session_id, speaker, ProposeAvailabilityChangeArgs.model_validate(args)
    )


async def _dispatch_confirm_availability_change(
    *,
    db: AsyncSession | None,
    session_id: str,
    speaker: SpeakerContext,
    args: dict[str, Any],
) -> dict:
    """Adapt an LLM ``confirm_availability_change`` tool call to Task 3's tool."""
    return await confirm_availability_change(
        db, session_id, speaker, ConfirmAvailabilityChangeArgs.model_validate(args)
    )


VERIFY_BOOKING_INTENT_TOOL = ToolSpec(
    name="verify_booking_intent",
    schema=_build_tool_schema(
        "verify_booking_intent",
        "Review or correct the pending SM-4a parsed booking intent and record the "
        "human verification decision (verified true/false).",
        VerifyBookingIntentArgs,
    ),
    dispatch=_dispatch_verify_booking_intent,
)

VERIFY_ALTERNATIVE_SLOT_TOOL = ToolSpec(
    name="verify_alternative_slot",
    schema=_build_tool_schema(
        "verify_alternative_slot",
        "Review or correct the pending SM-4b suggested alternative slot and record "
        "the human verification decision (verified true/false).",
        VerifyAlternativeSlotArgs,
    ),
    dispatch=_dispatch_verify_alternative_slot,
)

VERIFY_CONFLICT_CHECK_TOOL = ToolSpec(
    name="verify_conflict_check",
    schema=_build_tool_schema(
        "verify_conflict_check",
        "Record the human sign-off decision (verified true/false) on the pending "
        "SM-4c conflict-check result.",
        VerifyConflictCheckArgs,
    ),
    dispatch=_dispatch_verify_conflict_check,
)

PROPOSE_AVAILABILITY_CHANGE_TOOL = ToolSpec(
    name="propose_availability_change",
    schema=_build_tool_schema(
        "propose_availability_change",
        "Record the staff member's block/unblock availability change as a structured "
        "time window and return its restatement for confirmation (FR-25).",
        ProposeAvailabilityChangeArgs,
    ),
    dispatch=_dispatch_propose_availability_change,
)

CONFIRM_AVAILABILITY_CHANGE_TOOL = ToolSpec(
    name="confirm_availability_change",
    schema=_build_tool_schema(
        "confirm_availability_change",
        "Record the staff member's explicit yes/no on the pending proposed "
        "availability change; only a 'yes' performs the real write (FR-27).",
        ConfirmAvailabilityChangeArgs,
    ),
    dispatch=_dispatch_confirm_availability_change,
)

_VERIFICATION_TOOLS: list[ToolSpec] = [
    VERIFY_BOOKING_INTENT_TOOL,
    VERIFY_ALTERNATIVE_SLOT_TOOL,
    VERIFY_CONFLICT_CHECK_TOOL,
]

STAFF_TOOLS: list[ToolSpec] = [
    *_VERIFICATION_TOOLS,
    PROPOSE_AVAILABILITY_CHANGE_TOOL,
    CONFIRM_AVAILABILITY_CHANGE_TOOL,
]
"""The tools offered to a Staff speaker's session: the three SM-4a/b/c
verification tools plus the two availability-change tools (Task 3). No
catalog-change tool is included — out of scope per the implementation plan.
"""

OWNER_ADMIN_TOOLS: list[ToolSpec] = list(_VERIFICATION_TOOLS)
"""The tools offered to an Owner/Admin speaker's session: the three SM-4a/b/c
verification tools only. The availability-change tools are deliberately
excluded per FR-21 (Owner/Admin cannot manage their own availability) — the
registry's role-based visibility is the enforcement point ``base-rules.md``
requires, not merely the tools' own internal guard re-checks (Task 3).
"""


def get_tools_for_role(role: StaffRole) -> list[ToolSpec]:
    """Return the tool list a session for ``role`` should be offered.

    A fresh list is returned each call so a caller mutating the result (e.g.
    appending) never corrupts the module-level canonical lists above.
    """
    if role == StaffRole.STAFF:
        return list(STAFF_TOOLS)
    if role == StaffRole.OWNER_ADMIN:
        return list(OWNER_ADMIN_TOOLS)
    raise ValueError(f"No tool registry is defined for role: {role!r}")
