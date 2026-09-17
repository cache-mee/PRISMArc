from app.agent.state import session_store
from app.agent.state.session_store import SessionState


def test_get_or_create_defaults_history_to_empty_list() -> None:
    state = session_store.get_or_create("session-history-default")

    assert state.history == []


def test_save_round_trips_non_empty_history_unchanged() -> None:
    session_id = "session-history-roundtrip"
    history = [
        {"role": "user", "content": "Hi, I'd like to book a haircut."},
        {"role": "assistant", "content": "Sure — what day works for you?"},
    ]
    state = SessionState(history=history)

    session_store.save(session_id, state)
    saved_state = session_store.get_or_create(session_id)

    assert saved_state.history == history
