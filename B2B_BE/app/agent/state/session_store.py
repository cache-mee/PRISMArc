"""In-memory, session-id-keyed conversation/turn state.

Recorded explicitly as the `stack/stack-proposal.md` §6.4-permitted
in-memory fallback, **not** the primary persisted-state recommendation
(backend-persisted state keyed by ``(channel, phone_number)``). Before a
phone number is captured there is no ``(channel, phone_number)`` key to
persist against yet, so this ticket (APPOINTMEN-14) uses a client-supplied
``session_id`` as the interim key, process-local and not shared across
worker processes — see the APPOINTMEN-14 implementation plan, *Technical
Context* decision 5, and *Risks*. This is expected to be replaced by
`(channel, phone_number)`-keyed persisted storage once Story 1.1's
``messages`` table exists.
"""

import asyncio
from dataclasses import dataclass, field

from app.domain.availability import ProposedAvailabilityChange
from app.models.staff import StaffRole


@dataclass
class SessionState:
    """Turn state for a single Web Chat conversation, keyed by session id."""

    phone_number: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None
    resolved: bool = False
    awaiting_name: bool = False

    # Staff/Owner (Manager Agent) resolution fields — additive only, added by
    # APPOINTMEN-49 (WhatsApp Staff/Owner identity). All default so every
    # existing customer-flow (``booking_agent``) call site and behavior is
    # unaffected; see ``app.agent.manager_agent.resolve_and_greet_speaker``.
    staff_id: int | None = None
    staff_name: str | None = None
    staff_role: StaffRole | None = None
    manager_resolved: bool = False

    # Conversation history and pending availability-change fields — additive
    # only, added by APPOINTMEN-54 (Booking Agent conversational loop) and
    # APPOINTMEN-55 (Manager Agent conversational loop). All default so every
    # existing call site and behavior (Booking-Agent-only or otherwise) is
    # unaffected; see ``app.agent.manager_agent.run_manager_turn``.
    history: list[dict] = field(default_factory=list)
    pending_availability_change: ProposedAvailabilityChange | None = None


_sessions: dict[str, SessionState] = {}
_turn_locks: dict[str, asyncio.Lock] = {}


def get_or_create(session_id: str) -> SessionState:
    """Return the existing state for ``session_id``, or a fresh one."""
    return _sessions.setdefault(session_id, SessionState())


def save(session_id: str, state: SessionState) -> None:
    """Persist (in-process) ``state`` as the current state for ``session_id``."""
    _sessions[session_id] = state


def turn_lock(session_id: str) -> asyncio.Lock:
    """Return the lock serializing turns for ``session_id``.

    ``SessionState`` is a single mutable object shared by every request for
    the same ``session_id`` (e.g. Web Chat's auto-sent opening greeting
    racing a customer's fast first reply). Without serialization, two
    concurrent turns can interleave reads/writes of the same state — most
    damagingly ``history``, corrupting it into a message sequence the LLM
    provider rejects on every later turn, wedging the session until process
    restart. Callers must hold this for the full turn, from
    ``get_or_create`` through ``save``.
    """
    return _turn_locks.setdefault(session_id, asyncio.Lock())
