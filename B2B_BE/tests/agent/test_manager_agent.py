import copy
import json
import logging
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.manager_agent import (
    SpeakerContext,
    _MAX_TOOL_ITERATIONS,
    _TOOL_LOOP_CAP_REACHED_MESSAGE,
    dispatch_tool,
    present_conflict_check_for_verification,
    render_proposed_availability_change_restatement,
    resolve_and_greet_speaker,
    run_manager_turn,
)
from app.agent.providers.base import LLMResponse, ToolCall
from app.agent.state import session_store
from app.domain.availability import ProposedAvailabilityChange
from app.domain.conflict_verification import VerifiedConflictCheck
from app.domain.conflicts import ConflictCheckResult, ConflictingBooking
from app.models.staff import StaffRole

STAFF_SPEAKER = SpeakerContext(id=1, name="Dr. Rao", role=StaffRole.STAFF)


def _unique_session_id() -> str:
    return f"session-{uuid.uuid4()}"


def _assistant_message(text: str | None = "Sure, here you go.") -> dict:
    return {"role": "assistant", "content": text}


NO_CONFLICT_RESULT = ConflictCheckResult(has_conflict=False, conflicting_bookings=[])

HAS_CONFLICT_RESULT = ConflictCheckResult(
    has_conflict=True,
    conflicting_bookings=[
        ConflictingBooking(
            booking_id=1,
            start_time="2026-09-17T10:00:00",
            service_name="Haircut",
        )
    ],
)


@pytest.mark.parametrize("result", [NO_CONFLICT_RESULT, HAS_CONFLICT_RESULT])
def test_present_conflict_check_for_verification_returns_unverified_wrapper(
    result: ConflictCheckResult,
) -> None:
    verified_check = present_conflict_check_for_verification(result)

    assert isinstance(verified_check, VerifiedConflictCheck)
    assert verified_check.result == result
    assert verified_check.verified is False


@pytest.mark.parametrize("result", [NO_CONFLICT_RESULT, HAS_CONFLICT_RESULT])
def test_present_conflict_check_for_verification_logs_outcome(
    caplog: pytest.LogCaptureFixture, result: ConflictCheckResult
) -> None:
    with caplog.at_level(logging.INFO, logger="app.agent.manager_agent"):
        present_conflict_check_for_verification(result)

    info_records = [record for record in caplog.records if record.levelno == logging.INFO]
    assert len(info_records) == 1
    message = info_records[0].getMessage()
    assert f"has_conflict={result.has_conflict!r}" in message
    for booking in result.conflicting_bookings:
        assert str(booking.booking_id) in message
        assert repr(booking.start_time) in message


def test_render_proposed_availability_change_restatement_block() -> None:
    change = ProposedAvailabilityChange(
        staff_name="Dr. Rao",
        start_time=datetime(2026, 9, 18, 9, 0),
        end_time=datetime(2026, 9, 18, 13, 0),
        blocked=True,
    )

    restatement = render_proposed_availability_change_restatement(change)

    assert "Dr. Rao" in restatement
    assert "block" in restatement.lower()
    assert "unblock" not in restatement.lower()
    assert restatement.rstrip().endswith("?")
    assert "confirm" in restatement.lower()


def test_render_proposed_availability_change_restatement_unblock() -> None:
    change = ProposedAvailabilityChange(
        staff_name="Dr. Rao",
        start_time=datetime(2026, 9, 18, 9, 0),
        end_time=datetime(2026, 9, 18, 13, 0),
        blocked=False,
    )

    restatement = render_proposed_availability_change_restatement(change)

    assert "Dr. Rao" in restatement
    assert "unblock" in restatement.lower()
    assert restatement.rstrip().endswith("?")
    assert "confirm" in restatement.lower()


def test_render_proposed_availability_change_restatement_block_and_unblock_differ() -> None:
    start_time = datetime(2026, 9, 18, 9, 0)
    end_time = datetime(2026, 9, 18, 13, 0)
    blocked_change = ProposedAvailabilityChange(
        staff_name="Dr. Rao", start_time=start_time, end_time=end_time, blocked=True
    )
    unblocked_change = ProposedAvailabilityChange(
        staff_name="Dr. Rao", start_time=start_time, end_time=end_time, blocked=False
    )

    blocked_text = render_proposed_availability_change_restatement(blocked_change)
    unblocked_text = render_proposed_availability_change_restatement(unblocked_change)

    assert blocked_text != unblocked_text


# --- run_manager_turn: the bounded tool-calling loop (Task 6) ---------------


@pytest.mark.asyncio
async def test_run_manager_turn_no_tool_calls_returns_text_after_one_generate_call() -> None:
    session_id = _unique_session_id()
    mock_generate = AsyncMock(
        return_value=LLMResponse(
            text="Hello there!",
            tool_calls=[],
            raw_message=_assistant_message("Hello there!"),
        )
    )

    with patch("app.agent.providers.litellm_provider.LiteLLMProvider.generate", mock_generate):
        result = await run_manager_turn(
            db=None, session_id=session_id, speaker=STAFF_SPEAKER, message="Hi"
        )

    assert mock_generate.call_count == 1
    assert result == "Hello there!"

    state = session_store.get_or_create(session_id)
    assert state.history == [
        {"role": "user", "content": "Hi"},
        _assistant_message("Hello there!"),
    ]


@pytest.mark.asyncio
async def test_run_manager_turn_dispatches_one_tool_then_returns_final_text() -> None:
    session_id = _unique_session_id()
    tool_call = ToolCall(
        id="call_1",
        name="propose_availability_change",
        args={
            "start_time": "2026-09-18T09:00:00",
            "end_time": "2026-09-18T13:00:00",
            "blocked": True,
        },
    )
    first_response = LLMResponse(
        text=None,
        tool_calls=[tool_call],
        raw_message={"role": "assistant", "content": None},
    )
    second_response = LLMResponse(
        text="Got it, all set.",
        tool_calls=[],
        raw_message=_assistant_message("Got it, all set."),
    )
    responses = [first_response, second_response]
    message_snapshots: list[list[dict]] = []

    async def fake_generate(*, system: str, messages: list[dict], tools: list[dict]):
        message_snapshots.append(copy.deepcopy(messages))
        return responses.pop(0)

    mock_generate = AsyncMock(side_effect=fake_generate)
    mock_propose = AsyncMock(
        return_value={"declined": False, "restatement": "You're blocking Friday morning."}
    )

    with (
        patch("app.agent.providers.litellm_provider.LiteLLMProvider.generate", mock_generate),
        patch("app.agent.tool_registry.propose_availability_change", mock_propose),
    ):
        result = await run_manager_turn(
            db=None,
            session_id=session_id,
            speaker=STAFF_SPEAKER,
            message="Block Friday morning",
        )

    assert mock_generate.call_count == 2

    mock_propose.assert_called_once()
    called_session_id, called_speaker, called_args = mock_propose.call_args.args
    assert called_session_id == session_id
    assert called_speaker == STAFF_SPEAKER
    assert called_args.blocked is True

    # The tool's JSON result must already be in the message list the *second*
    # `generate` call received — proven via a snapshot taken at call time
    # (not by inspecting the final, further-mutated list after the loop ends).
    assert len(message_snapshots) == 2
    second_call_messages = message_snapshots[1]
    tool_messages = [m for m in second_call_messages if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call_1"
    assert json.loads(tool_messages[0]["content"]) == {
        "declined": False,
        "restatement": "You're blocking Friday morning.",
    }

    assert result == "Got it, all set."


@pytest.mark.asyncio
async def test_run_manager_turn_caps_at_max_tool_iterations_without_hanging() -> None:
    session_id = _unique_session_id()
    mock_generate = AsyncMock(
        return_value=LLMResponse(
            text=None,
            tool_calls=[
                ToolCall(id="call_n", name="verify_booking_intent", args={"verified": True})
            ],
            raw_message={"role": "assistant", "content": None},
        )
    )

    with patch("app.agent.providers.litellm_provider.LiteLLMProvider.generate", mock_generate):
        result = await run_manager_turn(
            db=None,
            session_id=session_id,
            speaker=STAFF_SPEAKER,
            message="Keep going forever",
        )

    # The bounded-loop guarantee: `generate` is called at most
    # `_MAX_TOOL_ITERATIONS` times — never unboundedly, even though the mock
    # keeps returning tool calls every single time.
    assert mock_generate.call_count <= _MAX_TOOL_ITERATIONS
    assert mock_generate.call_count == _MAX_TOOL_ITERATIONS
    assert result == _TOOL_LOOP_CAP_REACHED_MESSAGE

    # `state.history` is still saved on the capped exit path, not dropped.
    state = session_store.get_or_create(session_id)
    assert len(state.history) == 1 + 2 * _MAX_TOOL_ITERATIONS
    assert state.history[0] == {"role": "user", "content": "Keep going forever"}


@pytest.mark.asyncio
async def test_dispatch_tool_returns_not_available_result_without_raising() -> None:
    owner_admin_speaker = SpeakerContext(id=2, name="Ramesh", role=StaffRole.OWNER_ADMIN)

    # Case 1: a fully hallucinated tool name.
    hallucinated_result = await dispatch_tool(
        "delete_all_appointments",
        {},
        db=None,
        session_id=_unique_session_id(),
        speaker=STAFF_SPEAKER,
    )
    assert hallucinated_result == {
        "error": "tool_not_available",
        "message": "Tool 'delete_all_appointments' is not available for this role.",
    }
    json.dumps(hallucinated_result)

    # Case 2: a real tool name that exists, but not for this speaker's role
    # (`propose_availability_change` is Staff-only, excluded from
    # `OWNER_ADMIN_TOOLS` per FR-21) — the underlying tool must never run.
    with patch("app.agent.tool_registry.propose_availability_change") as mock_underlying:
        role_scoped_result = await dispatch_tool(
            "propose_availability_change",
            {"message": "Block Friday morning"},
            db=None,
            session_id=_unique_session_id(),
            speaker=owner_admin_speaker,
        )

    mock_underlying.assert_not_called()
    assert role_scoped_result == {
        "error": "tool_not_available",
        "message": "Tool 'propose_availability_change' is not available for this role.",
    }
    json.dumps(role_scoped_result)


@pytest.mark.asyncio
async def test_run_manager_turn_persists_history_across_two_calls_same_session() -> None:
    session_id = _unique_session_id()
    mock_generate = AsyncMock(
        side_effect=[
            LLMResponse(
                text="First reply",
                tool_calls=[],
                raw_message=_assistant_message("First reply"),
            ),
            LLMResponse(
                text="Second reply",
                tool_calls=[],
                raw_message=_assistant_message("Second reply"),
            ),
        ]
    )

    with patch("app.agent.providers.litellm_provider.LiteLLMProvider.generate", mock_generate):
        first_result = await run_manager_turn(
            db=None, session_id=session_id, speaker=STAFF_SPEAKER, message="Hi"
        )
        second_result = await run_manager_turn(
            db=None,
            session_id=session_id,
            speaker=STAFF_SPEAKER,
            message="What about Friday?",
        )

    assert first_result == "First reply"
    assert second_result == "Second reply"

    # The second turn's `generate` call must have seen the first turn's
    # messages already in `state.history` — proof the loop actually reads
    # `state.history` back in on the next call rather than starting fresh.
    second_call_messages = mock_generate.call_args_list[1].kwargs["messages"]
    assert {"role": "user", "content": "Hi"} in second_call_messages
    assert _assistant_message("First reply") in second_call_messages
    assert {"role": "user", "content": "What about Friday?"} in second_call_messages

    state = session_store.get_or_create(session_id)
    assert state.history == [
        {"role": "user", "content": "Hi"},
        _assistant_message("First reply"),
        {"role": "user", "content": "What about Friday?"},
        _assistant_message("Second reply"),
    ]


# --- resolve_and_greet_speaker: wiring into run_manager_turn (Task 7) -------


@pytest.mark.asyncio
async def test_resolve_and_greet_speaker_already_resolved_calls_run_manager_turn() -> None:
    session_id = _unique_session_id()
    state = session_store.get_or_create(session_id)
    state.manager_resolved = True
    state.staff_id = 1
    state.staff_name = "Dr. Rao"
    state.staff_role = StaffRole.STAFF
    session_store.save(session_id, state)

    mock_run_manager_turn = AsyncMock(return_value="Sure, blocking Friday morning.")
    db_sentinel = object()

    with patch("app.agent.manager_agent.run_manager_turn", mock_run_manager_turn):
        result = await resolve_and_greet_speaker(
            session_id, "+911234567890", db_sentinel, "I'm unavailable Friday morning"
        )

    mock_run_manager_turn.assert_called_once_with(
        db=db_sentinel,
        session_id=session_id,
        speaker=SpeakerContext(id=1, name="Dr. Rao", role=StaffRole.STAFF),
        message="I'm unavailable Friday morning",
    )
    assert result == "Sure, blocking Friday morning."


@pytest.mark.asyncio
async def test_resolve_and_greet_speaker_not_yet_resolved_still_greets_without_looping() -> None:
    session_id = _unique_session_id()
    context = SpeakerContext(id=2, name="Ramesh", role=StaffRole.OWNER_ADMIN)
    mock_resolve_speaker = AsyncMock(return_value=context)
    mock_run_manager_turn = AsyncMock()

    with (
        patch("app.agent.manager_agent.resolve_speaker", mock_resolve_speaker),
        patch("app.agent.manager_agent.run_manager_turn", mock_run_manager_turn),
    ):
        result = await resolve_and_greet_speaker(
            session_id, "+911234500000", None, "+911234500000"
        )

    mock_resolve_speaker.assert_called_once_with("+911234500000")
    mock_run_manager_turn.assert_not_called()
    assert result == "Hi Ramesh! Want to update the service catalog?"

    state = session_store.get_or_create(session_id)
    assert state.manager_resolved is True
    assert state.staff_id == 2


@pytest.mark.asyncio
async def test_resolve_and_greet_speaker_no_match_falls_through_without_looping() -> None:
    session_id = _unique_session_id()
    mock_resolve_speaker = AsyncMock(return_value=None)
    mock_run_manager_turn = AsyncMock()

    with (
        patch("app.agent.manager_agent.resolve_speaker", mock_resolve_speaker),
        patch("app.agent.manager_agent.run_manager_turn", mock_run_manager_turn),
    ):
        result = await resolve_and_greet_speaker(
            session_id, "+919999999999", None, "+919999999999"
        )

    assert result is None
    mock_run_manager_turn.assert_not_called()
