import uuid
from datetime import datetime

from app.agent.state import session_store
from app.domain.availability import ProposedAvailabilityChange


def _unique_session_id() -> str:
    return f"session-{uuid.uuid4()}"


def test_get_or_create_returns_fresh_state_with_additive_defaults() -> None:
    state = session_store.get_or_create(_unique_session_id())

    assert state.history == []
    assert state.pending_availability_change is None


def test_save_and_get_or_create_round_trips_history_and_pending_availability_change() -> None:
    session_id = _unique_session_id()
    state = session_store.get_or_create(session_id)

    state.history.append({"role": "user", "content": "I'm unavailable Friday morning"})
    change = ProposedAvailabilityChange(
        staff_name="Dr. Rao",
        start_time=datetime(2026, 9, 18, 9, 0),
        end_time=datetime(2026, 9, 18, 12, 0),
        blocked=True,
    )
    state.pending_availability_change = change

    session_store.save(session_id, state)

    reloaded = session_store.get_or_create(session_id)
    assert reloaded.history == [{"role": "user", "content": "I'm unavailable Friday morning"}]
    assert reloaded.pending_availability_change == change


def test_history_default_is_not_shared_between_sessions() -> None:
    first = session_store.get_or_create(_unique_session_id())
    second = session_store.get_or_create(_unique_session_id())

    first.history.append({"role": "user", "content": "hello"})

    assert second.history == []
