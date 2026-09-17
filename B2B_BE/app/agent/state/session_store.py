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

from dataclasses import dataclass


@dataclass
class SessionState:
    """Turn state for a single Web Chat conversation, keyed by session id."""

    phone_number: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None
    resolved: bool = False
    awaiting_name: bool = False


_sessions: dict[str, SessionState] = {}


def get_or_create(session_id: str) -> SessionState:
    """Return the existing state for ``session_id``, or a fresh one."""
    return _sessions.setdefault(session_id, SessionState())


def save(session_id: str, state: SessionState) -> None:
    """Persist (in-process) ``state`` as the current state for ``session_id``."""
    _sessions[session_id] = state
