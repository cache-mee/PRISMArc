"""The Manager Agent tool-calling loop's system prompt (APPOINTMEN-55).

``app.agent.manager_agent.run_manager_turn`` (Task 6) sends this prompt to the
``LLMProvider`` on every turn, alongside ``tools=[t.schema for t in
get_tools_for_role(speaker.role)]`` (``app.agent.tool_registry``, Task 4). It
is kept in its own module rather than inlined in ``manager_agent.py`` — unlike
this codebase's existing single-tool-classifier prompts
(``app.agent.booking_intent.parse_booking_intent``,
``app.agent.availability_intent.parse_availability_change``,
``app.agent.catalog_intent.is_catalog_change_request``), which are short,
one-shot extraction instructions inlined at their single call site, this
prompt is a stable, multi-turn persona instruction reused every turn of a
bounded loop — long/stable enough to warrant the ``app/agent/prompts/``
package APPOINTMEN-14 scaffolded but left empty.

Deliberately does not name any tool: the tool list itself is passed
separately via ``tools=`` (Task 4's registry already enforces which tools a
given role's session is even offered), so this text stays about behavior and
persona, not a tool catalog that could drift out of sync with the registry.
"""

from app.agent.manager_agent import SpeakerContext
from app.models.staff import StaffRole

_ROLE_LABEL: dict[StaffRole, str] = {
    StaffRole.OWNER_ADMIN: "Owner/Admin",
    StaffRole.STAFF: "Staff",
}

_ROLE_INSTRUCTIONS: dict[StaffRole, str] = {
    StaffRole.OWNER_ADMIN: (
        "As Owner/Admin, you help them review pending booking-intent, "
        "alternative-slot, and conflict-check items awaiting human "
        "verification. You do not manage their own availability — that is "
        "not something they can ask you to change."
    ),
    StaffRole.STAFF: (
        "As Staff, you help them review pending booking-intent, "
        "alternative-slot, and conflict-check items awaiting human "
        "verification, and help them report a schedule change (e.g. "
        "blocking or unblocking a window of availability)."
    ),
}


def render_manager_agent_system_prompt(speaker: SpeakerContext) -> str:
    """Render the system prompt for one turn of the Manager Agent loop (FR-25/FR-27).

    Always names ``speaker.name`` and their resolved role, mirroring
    ``manager_agent.render_identity_greeting``'s existing role split
    (``_ROLE_GREETINGS``) — an Owner/Admin speaker and a Staff speaker get
    distinct, role-appropriate wording, and every rendering is bound to the
    one resolved speaker passed in, so a session can never read as if it were
    speaking for someone else.

    Instructs the model to call a tool — rather than answer from memory —
    for anything requiring a domain write (e.g. an availability change) or a
    pending human-verification checkpoint (SM-4a/b/c), without naming any
    tool by name: the tool list itself is supplied separately via the
    ``tools=`` parameter (``app.agent.tool_registry.get_tools_for_role``).
    """
    role_instructions = _ROLE_INSTRUCTIONS[speaker.role]
    return (
        f"You are the Manager Agent, a conversational assistant for salon staff and "
        f"owner/admin users, speaking with {speaker.name}, who is resolved and "
        f"authenticated as {_ROLE_LABEL[speaker.role]}. {role_instructions} "
        "For anything that requires making a real change to the schedule or the "
        "catalog, or recording a decision on a pending item awaiting human "
        "verification, you must call the appropriate available tool rather than "
        "answer from memory or assume the change has already happened — never "
        "claim a change was made unless a tool call actually performed it. When a "
        "tool call proposes a change, restate it back to the speaker and wait for "
        "their explicit confirmation before treating it as final."
    )
