import asyncio
import uuid
from datetime import UTC, datetime

from app.agent.state import session_store
from app.agent.state.session_store import SessionState
from app.domain.availability import ProposedAvailabilityChange


def _unique_session_id() -> str:
    return f"session-{uuid.uuid4()}"


def test_get_or_create_returns_fresh_state_with_additive_defaults() -> None:
    state = session_store.get_or_create(_unique_session_id())

    assert state.history == []
    assert state.pending_availability_change is None


def test_save_round_trips_history_and_pending_availability_change_unchanged() -> None:
    session_id = _unique_session_id()
    history = [
        {"role": "user", "content": "Hi, I'd like to book a haircut."},
        {"role": "assistant", "content": "Sure — what day works for you?"},
    ]
    change = ProposedAvailabilityChange(
        staff_name="Dr. Rao",
        start_time=datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
        blocked=True,
    )
    state = SessionState(history=history, pending_availability_change=change)

    session_store.save(session_id, state)
    saved_state = session_store.get_or_create(session_id)

    assert saved_state.history == history
    assert saved_state.pending_availability_change == change


def test_history_default_is_not_shared_between_sessions() -> None:
    first = session_store.get_or_create(_unique_session_id())
    second = session_store.get_or_create(_unique_session_id())

    first.history.append({"role": "user", "content": "hello"})

    assert second.history == []


def test_turn_lock_returns_the_same_lock_instance_for_the_same_session_id() -> None:
    session_id = _unique_session_id()

    assert session_store.turn_lock(session_id) is session_store.turn_lock(session_id)


def test_turn_lock_returns_independent_locks_for_different_session_ids() -> None:
    assert session_store.turn_lock(_unique_session_id()) is not session_store.turn_lock(
        _unique_session_id()
    )


async def test_turn_lock_serializes_concurrent_turns_for_the_same_session() -> None:
    """Regression test: two concurrent turns for one session_id must never interleave.

    Before the lock existed, two requests racing for the same session_id
    (e.g. Web Chat's auto-sent opening greeting racing a fast first reply)
    could interleave reads/writes of the same shared ``SessionState``,
    corrupting ``history`` and wedging the session on every later turn.
    """
    session_id = _unique_session_id()
    events: list[str] = []

    async def turn(label: str) -> None:
        async with session_store.turn_lock(session_id):
            events.append(f"{label}-start")
            await asyncio.sleep(0)
            events.append(f"{label}-end")

    await asyncio.gather(turn("a"), turn("b"))

    assert events in (
        ["a-start", "a-end", "b-start", "b-end"],
        ["b-start", "b-end", "a-start", "a-end"],
    )
