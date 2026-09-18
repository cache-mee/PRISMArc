"""Manager Agent turn logic.

Houses the Manager Agent stub built by APPOINTMEN-17 (FR-24, Staff identity
resolution) — ``SpeakerContext``, ``resolve_speaker``, ``describe_speaker`` —
plus one addition by APPOINTMEN-16 (FR-14, Owner/Admin identity resolution):

- ``render_identity_greeting`` — the role-differentiated opening line the UX
  spec (`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/staff-owner-manager-chat.md`
  §2) defines for a resolved ``SpeakerContext``: one line for Owner/Admin,
  one for Staff. It is additive alongside ``describe_speaker`` (left
  unchanged, per APPOINTMEN-17), not a replacement for it.

APPOINTMEN-40 (FR-18, Confirmation required before catalog changes apply) adds
``render_proposed_service_change_restatement`` and
``present_proposed_service_change_for_confirmation`` — the restatement text and
SM-4a-equivalent checkpoint hook point for a pending ``ProposedService`` /
``ProposedServiceEdit`` / ``ProposedServiceDeletion`` (``app.domain.services``),
ahead of that module's existing ``confirm_and_*_service`` write gates.

APPOINTMEN-41 (FR-21, Owner/Admin cannot manage own availability) adds
``respond_to_owner_admin_availability_request`` — the hook point that consults
``app.domain.owner_admin_availability_boundary.decline_owner_admin_own_availability_request``
for an already-resolved speaker, ahead of
``app.tools.availability_change.propose_availability_change`` /
``confirm_and_apply_availability_change`` ever running for that speaker.

APPOINTMEN-49 (FR-14/FR-24, WhatsApp Staff/Owner identity resolution) adds
``resolve_and_greet_speaker`` — the WhatsApp-channel counterpart to
``app.agent.booking_agent.handle_message``'s customer-identity gate. It is the
one new piece of dispatch logic the WhatsApp webhook adapter
(``app.api.webhooks.whatsapp``) calls ahead of the customer flow: on a
not-yet-resolved session it calls ``resolve_speaker``/``render_identity_greeting``
(both unchanged, reused verbatim) and marks the session Staff/Owner-resolved on
a match; on an already-resolved session it now (APPOINTMEN-55 Task 7) calls
``run_manager_turn`` instead of returning a static placeholder.

APPOINTMEN-51 (WhatsApp channel-parity NFR, ``whatsapp-deltas.md`` §2) rewords
``render_proposed_service_change_restatement``'s closing question (stories
4.1-4.3) from the open-ended "Shall I confirm this?" to an explicit yes/no
("Reply YES to confirm or NO to cancel."), mirroring APPOINTMEN-50's fix to
``app.domain.appointments.render_direct_confirmation``. APPOINTMEN-51 also
independently added its own ``render_proposed_availability_change_restatement``
/ ``present_proposed_availability_change_for_confirmation`` pair (story 3.4,
FR-27), built in parallel with and merged concurrently to APPOINTMEN-55's own
version of the former. APPOINTMEN-55's implementation is kept as the single
``render_proposed_availability_change_restatement`` definition below — it is
the one actually called by ``app.tools.availability_change.propose_availability_change``
and exercised end-to-end through the wired loop (Task 6/7) — while
``present_proposed_availability_change_for_confirmation`` is kept from
APPOINTMEN-51 as an additional, still-unwired hook mirroring
``present_proposed_service_change_for_confirmation``'s existing pattern.
**Flagged, not silently fixed:** the two tickets' restatement copy differs —
APPOINTMEN-55's ends in an open-ended "Shall I confirm this?" while
APPOINTMEN-51's sibling functions use the explicit "Reply YES to confirm or
NO to cancel." framing; reconciling that copy inconsistency is out of scope
for this merge (it would require rewriting APPOINTMEN-55's own passing tests)
and is left for a follow-up.

APPOINTMEN-55 (FR-25/FR-27, Manager Agent conversational loop) adds
``render_proposed_availability_change_restatement`` — the restate half of the
FR-27 restate-then-confirm sequence for a pending ``ProposedAvailabilityChange``,
mirroring ``render_proposed_service_change_restatement``'s shape. It is called
by ``app.tools.availability_change.propose_availability_change`` (the
LLM-callable tool that builds the pending change and stores it on the
session), ahead of ``app.tools.availability_change.confirm_availability_change``
ever calling ``confirm_and_apply_availability_change``.

APPOINTMEN-55 Task 6 also adds ``run_manager_turn`` and its ``dispatch_tool``
helper — the ticket's core deliverable, the bounded tool-calling loop that
sends the resolved speaker's message plus session history to the
``LLMProvider`` (``app.agent.providers.base``), dispatches any tool calls the
model makes through the role-scoped registry
(``app.agent.tool_registry.get_tools_for_role``, Task 4), and feeds each
tool's JSON result back to the model — capped at ``_MAX_TOOL_ITERATIONS``
rounds (a bounded ``for``/``else`` loop, never an unbounded ``while True``) so
a model that keeps calling tools can never hang the turn. ``get_tools_for_role``,
``render_manager_agent_system_prompt`` (Task 5), and ``LiteLLMProvider`` are
imported locally inside these two functions rather than at module level:
``app.agent.tool_registry`` and ``app.agent.prompts.manager_agent_prompt`` both
import ``SpeakerContext`` from this module, so a module-level import back into
either would be a circular import.

APPOINTMEN-55 Task 7 wires that loop into the existing entry point: on an
already-``manager_resolved`` session, ``resolve_and_greet_speaker`` now calls
``run_manager_turn`` with the resolved ``SpeakerContext`` and the turn's
``message``, in place of the static ``_ALREADY_GREETED_PLACEHOLDER`` reply
APPOINTMEN-49 originally returned there — this is the exact "unwired loop" gap
APPOINTMEN-41/49/50 each independently flagged. ``resolve_and_greet_speaker``'s
signature gains ``db: AsyncSession | None`` and ``message: str``, both threaded
through from the WhatsApp webhook adapter (``app.api.webhooks.whatsapp``),
which already has both available at its only call site.
"""

import json
import logging
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.catalog_intent import is_catalog_change_request
from app.agent.state import session_store
from app.domain.availability import ProposedAvailabilityChange
from app.domain.conflict_verification import VerifiedConflictCheck
from app.domain.conflicts import ConflictCheckResult
from app.domain.dashboard_access import decline_staff_dashboard_request
from app.domain.owner_admin_availability_boundary import (
    decline_owner_admin_own_availability_request,
)
from app.domain.schedule_override import decline_staff_schedule_override
from app.domain.services import (
    ProposedService,
    ProposedServiceDeletion,
    ProposedServiceEdit,
)
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


async def resolve_and_greet_speaker(
    session_id: str, phone_number: str, db: AsyncSession | None, message: str
) -> str | None:
    """Run one WhatsApp Staff/Owner identity-resolution turn for ``session_id`` (FR-14/FR-24).

    This is the WhatsApp-channel counterpart to
    ``app.agent.booking_agent.handle_message``'s customer-identity gate,
    called by the WhatsApp webhook adapter ahead of the customer flow:

    - Once the session is ``manager_resolved``, ``resolve_speaker`` is never
      called again — this now calls ``run_manager_turn`` (Task 6) with the
      resolved ``SpeakerContext`` and the turn's ``message`` instead of the
      old static ``_ALREADY_GREETED_PLACEHOLDER`` reply, which is what closes
      the "unwired loop" gap APPOINTMEN-41/49/50 each independently flagged.
      Every turn after the first still never re-resolves identity or falls
      through to the customer flow — it now actually holds a conversation
      instead of echoing a fixed string.
    - Otherwise, ``resolve_speaker(phone_number)`` (unchanged) is called. No
      match returns ``None`` — the caller is expected to fall through to the
      customer flow. A match sets ``staff_id``/``staff_name``/``staff_role``/
      ``phone_number``/``manager_resolved`` on the session state, saves it,
      and returns ``render_identity_greeting(context)`` (unchanged, reused
      verbatim) — the AC's "first message is directly the role-based
      greeting." ``run_manager_turn`` is not called on this first turn: the
      identity-resolution message itself (the phone number) is not a request
      for the loop to act on.

    ``db``/``message`` are threaded through from the WhatsApp webhook adapter
    (``app.api.webhooks.whatsapp``, Task 7) — both already available at its
    only call site — purely so the already-resolved branch below can hand
    them to ``run_manager_turn``.
    """
    async with session_store.turn_lock(session_id):
        state = session_store.get_or_create(session_id)

        if state.manager_resolved:
            speaker = SpeakerContext(
                id=state.staff_id, name=state.staff_name, role=state.staff_role
            )
            return await run_manager_turn(
                db=db, session_id=session_id, speaker=speaker, message=message
            )

        context = await resolve_speaker(phone_number)
        if context is None:
            return None

        state.phone_number = phone_number
        state.staff_id = context.id
        state.staff_name = context.name
        state.staff_role = context.role
        state.manager_resolved = True
        session_store.save(session_id, state)
        return render_identity_greeting(context)


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


def render_proposed_service_change_restatement(
    proposed: ProposedService | ProposedServiceEdit | ProposedServiceDeletion,
) -> str:
    """Render the human-readable restatement of a pending catalog change (FR-18).

    Dispatches on the concrete type to produce the text Ramesh is shown ahead of
    confirming: ``ProposedService`` restates the new service's name and price;
    ``ProposedServiceEdit`` restates only the fields actually set on it (mirroring
    its own "at least one of new_name/new_price" shape); ``ProposedServiceDeletion``
    restates the ``service_id`` being removed, since that is all the type carries —
    resolving it to a service name would require a DB lookup, out of scope here (see
    the APPOINTMEN-40 plan's Risks). Every branch ends with an explicit yes/no
    framing ("Reply YES to confirm or NO to cancel."), per ``whatsapp-deltas.md``
    §2 (APPOINTMEN-51) — the same fix APPOINTMEN-50 applied to
    ``render_direct_confirmation``. This is a shared, channel-agnostic renderer
    with no ``channel`` parameter. Pure function, no I/O, no DB access — matches
    the style of this module's ``render_identity_greeting``/``describe_speaker``.
    """
    if isinstance(proposed, ProposedService):
        return (
            f"You're adding a new service: {proposed.name!r} at "
            f"{proposed.price!r}. Reply YES to confirm or NO to cancel."
        )
    if isinstance(proposed, ProposedServiceEdit):
        changes = []
        if proposed.new_name is not None:
            changes.append(f"name to {proposed.new_name!r}")
        if proposed.new_price is not None:
            changes.append(f"price to {proposed.new_price!r}")
        change_text = " and ".join(changes)
        return (
            f"You're editing service {proposed.service_id!r}: changing "
            f"{change_text}. Reply YES to confirm or NO to cancel."
        )
    return (
        f"You're removing service {proposed.service_id!r} from the catalog. "
        "Reply YES to confirm or NO to cancel."
    )


def render_proposed_availability_change_restatement(
    change: ProposedAvailabilityChange,
) -> str:
    """Render the human-readable restatement of a pending availability change (FR-25/FR-27).

    Mirrors ``render_proposed_service_change_restatement``'s shape: dispatches on
    ``change.blocked`` to produce copy distinct for a block (marking a window
    unavailable) versus an unblock (reopening a previously-blocked window),
    naming ``change.staff_name`` and the exact ``[start_time, end_time)``
    window. Every branch ends in an explicit ask for confirmation — the
    "restate" half of FR-27's restate-then-confirm sequence that
    ``confirm_and_apply_availability_change`` (``app.domain.availability``)
    ultimately gates on. Pure function, no I/O, no DB access — matches the
    style of this module's ``render_identity_greeting``/``describe_speaker``.
    """
    window = (
        f"{change.start_time.strftime('%A, %B %d %I:%M %p')} to "
        f"{change.end_time.strftime('%I:%M %p')}"
    )
    if change.blocked:
        return (
            f"You're blocking out {window} for {change.staff_name}. "
            "Shall I confirm this?"
        )
    return (
        f"You're unblocking {window} for {change.staff_name}. " "Shall I confirm this?"
    )


def present_proposed_service_change_for_confirmation(
    proposed: ProposedService | ProposedServiceEdit | ProposedServiceDeletion,
) -> str:
    """Surface a freshly-restated catalog change for the FR-18 checkpoint (APPOINTMEN-40).

    This is the hook point a future conversational Manager Agent loop will call
    immediately after a ``ProposedService``/``ProposedServiceEdit``/
    ``ProposedServiceDeletion`` has been built, before any call to
    ``confirm_and_create_service`` / ``confirm_and_update_service`` /
    ``confirm_and_delete_service`` (``app.domain.services``). It logs the restated
    proposal as the observable checkpoint moment and returns the restatement text
    from ``render_proposed_service_change_restatement`` for a future conversational
    loop to send to Ramesh, whose explicit yes/no is then recorded via
    ``app.tools.catalog_change_confirmation.confirm_catalog_change`` before any of
    the ``confirm_and_*_service`` gates will let the write through.
    """
    _logger.info(
        "FR-18 checkpoint - proposed catalog change awaiting human confirmation: %r",
        proposed,
    )
    return render_proposed_service_change_restatement(proposed)


def present_proposed_availability_change_for_confirmation(
    change: ProposedAvailabilityChange,
) -> str:
    """Surface a freshly-restated availability change for the FR-27 checkpoint.

    Mirrors ``present_proposed_service_change_for_confirmation``'s existing shape
    exactly: this is the hook point a future conversational Manager Agent loop
    will call immediately after a ``ProposedAvailabilityChange`` has been built
    (e.g. from ``app.tools.availability_change.propose_availability_change``), before any call to
    ``confirm_and_apply_availability_change`` (``app.domain.availability``). It
    logs the restated proposal as the observable checkpoint moment and returns
    the restatement text from ``render_proposed_availability_change_restatement``
    for a future conversational loop to send to the staff member, whose explicit
    yes/no is then recorded (setting ``confirmed=True``) before
    ``confirm_and_apply_availability_change`` will let the write through. This
    is a new, still-unwired hook point — consistent with every other function in
    this module — not a call-site wiring change; no endpoint or webhook file is
    touched.
    """
    _logger.info(
        "FR-27 checkpoint - proposed availability change awaiting human "
        "confirmation: %r",
        change,
    )
    return render_proposed_availability_change_restatement(change)


async def handle_staff_catalog_boundary(
    speaker: SpeakerContext, message: str
) -> str | None:
    """Redirect a Staff-identified speaker away from an Owner/Admin-only catalog change (FR-28).

    This is the hook point a future conversational Manager Agent loop calls once a phone
    number has already been resolved to a ``SpeakerContext`` (via ``resolve_speaker``), ahead
    of any other intent handling for the message. Returns the fixed UX-spec redirect string
    when ``speaker.role`` is ``StaffRole.STAFF`` and ``message`` is classified as a catalog-change
    request (``is_catalog_change_request``); returns ``None`` otherwise — for an Owner/Admin
    speaker (Ramesh is allowed to manage the catalog, Epic 4, not built here) or for a Staff
    message that is not a catalog-change request, in which case the caller should continue with
    other intent handling (e.g. FR-25's ``app.tools.availability_change.propose_availability_change``).

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
    ``ProposedAvailabilityChange`` exists (e.g. from ``app.tools.availability_change.propose_availability_change``),
    before ever confirming or applying it. Returns the decline string to send back verbatim
    when not ``None``; returns ``None`` when the change should proceed.
    """
    return decline_staff_schedule_override(
        speaker.name, speaker.role, change.staff_name
    )


def respond_to_owner_admin_availability_request(speaker: SpeakerContext) -> str | None:
    """Consult the FR-21 guard for an already-resolved Manager Agent speaker.

    Hook point a future conversational Manager Agent loop calls immediately after an incoming
    message has been classified as a block/unblock-availability request (that classification
    step does not exist yet — see the FR-21 implementation plan's Out of Scope), before
    ``app.tools.availability_change.propose_availability_change`` or ``confirm_and_apply_availability_change`` ever run
    for that speaker. Returns the decline string to send back verbatim when not ``None``;
    returns ``None`` when the request should proceed (Staff).
    """
    return decline_owner_admin_own_availability_request(speaker.role)


_MAX_TOOL_ITERATIONS = 6
"""Bounded-loop safety valve for ``run_manager_turn``: the maximum number of
``LLMProvider.generate`` rounds a single turn will run before giving up on the
model ever stopping its own tool-calling, per the ticket's explicit "never an
unbounded while True" requirement.
"""

_TOOL_LOOP_CAP_REACHED_MESSAGE = (
    "I've made several tool calls trying to help with this and want to check in "
    "before continuing — could you tell me what you'd like me to do next?"
)
"""Returned by ``run_manager_turn`` when the model is still calling tools after
``_MAX_TOOL_ITERATIONS`` rounds — the bounded-loop safety valve's user-visible
message, in place of ever hanging the turn or raising.
"""

_EMPTY_REPLY_FALLBACK = "I don't have anything further to add on that — is there anything else I can help with?"
"""Returned by ``run_manager_turn`` when the model stops calling tools but its
final response has no text (``response.text`` is ``None``/empty), so a turn
never returns an empty string to the speaker.
"""


async def dispatch_tool(
    name: str,
    args: dict,
    *,
    db: AsyncSession | None,
    session_id: str,
    speaker: SpeakerContext,
) -> dict:
    """Dispatch one model-issued tool call to its role-scoped ``ToolSpec.dispatch`` (Task 6).

    Looks up ``name`` only within ``get_tools_for_role(speaker.role)``
    (``app.agent.tool_registry``, Task 4) — never the full universe of tools
    registered across both roles — so a hallucinated tool name, or a tool that
    exists but belongs to the *other* role's registry (e.g. an Owner/Admin
    session naming ``propose_availability_change``, which FR-21 excludes from
    ``OWNER_ADMIN_TOOLS``), cannot execute. Returns a clear
    ``tool_not_available`` error result fed back to the model instead of
    raising, so one bad tool call from the model never crashes the loop.

    ``get_tools_for_role`` is imported locally rather than at module level:
    ``app.agent.tool_registry`` imports ``SpeakerContext`` from this module, so
    a module-level import back into it here would be a circular import.
    """
    from app.agent.tool_registry import get_tools_for_role

    for tool in get_tools_for_role(speaker.role):
        if tool.name == name:
            return await tool.dispatch(
                db=db, session_id=session_id, speaker=speaker, args=args
            )
    return {
        "error": "tool_not_available",
        "message": f"Tool {name!r} is not available for this role.",
    }


async def run_manager_turn(
    db: AsyncSession | None, session_id: str, speaker: SpeakerContext, message: str
) -> str:
    """Run one bounded tool-calling turn of the Manager Agent conversational loop (FR-25/FR-27).

    The ticket's core deliverable. Appends ``message`` to the session's saved
    ``state.history`` (Task 1) and repeatedly calls ``LLMProvider.generate``
    (``app.agent.providers.base``) — system prompt from
    ``render_manager_agent_system_prompt`` (Task 5), tools from
    ``get_tools_for_role(speaker.role)`` (Task 4) — dispatching every tool call
    the model makes via ``dispatch_tool`` and feeding each JSON result back
    into the message list as a ``role: "tool"`` entry, until the model stops
    calling tools or ``_MAX_TOOL_ITERATIONS`` rounds are reached (a bounded
    ``for``/``else`` loop, never an unbounded ``while True``).

    Every provider turn's ``response.raw_message`` — not only turns that call a
    tool — is appended to the running ``messages`` list before checking whether
    the model called a tool, so ``state.history`` always ends with a
    well-formed transcript (the assistant's own reply is part of the history
    the *next* call to ``run_manager_turn`` builds on, exactly like every
    ``role: "tool"`` entry already is). ``state.history`` is saved via
    ``session_store.save`` on every exit path — the normal reply path and the
    bounded-loop cap — so a capped turn's tool-call/tool-result history is
    never silently dropped.

    ``get_tools_for_role``, ``render_manager_agent_system_prompt``, and
    ``LiteLLMProvider`` are imported locally rather than at module level, for
    the same circular-import reason documented on ``dispatch_tool`` (and
    because ``app.agent.prompts.manager_agent_prompt`` also imports
    ``SpeakerContext`` from this module). ``LiteLLMProvider`` is constructed
    the same way ``app.agent.booking_agent.run_booking_conversation``
    already does: inline, from ``settings.llm_model``/``settings.llm_api_key``.
    """
    from app.agent.prompts.manager_agent_prompt import (
        render_manager_agent_system_prompt,
    )
    from app.agent.providers.litellm_provider import LiteLLMProvider
    from app.agent.tool_registry import get_tools_for_role
    from app.config import settings

    state = session_store.get_or_create(session_id)
    messages = state.history + [{"role": "user", "content": message}]
    provider = LiteLLMProvider(model=settings.llm_model, api_key=settings.llm_api_key)
    system = render_manager_agent_system_prompt(speaker, datetime.now(UTC))
    tools = [tool.schema for tool in get_tools_for_role(speaker.role)]

    for _ in range(_MAX_TOOL_ITERATIONS):
        response = await provider.generate(
            system=system, messages=messages, tools=tools
        )
        messages.append(response.raw_message)
        if not response.tool_calls:
            break
        for call in response.tool_calls:
            result = await dispatch_tool(
                call.name, call.args, db=db, session_id=session_id, speaker=speaker
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, default=str),
                }
            )
    else:
        state.history = messages
        session_store.save(session_id, state)
        return _TOOL_LOOP_CAP_REACHED_MESSAGE

    state.history = messages
    session_store.save(session_id, state)
    return response.text or _EMPTY_REPLY_FALLBACK
