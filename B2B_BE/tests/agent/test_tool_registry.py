import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.booking_intent import BookingIntent
from app.agent.manager_agent import SpeakerContext
from app.agent.state import pending_verification_store
from app.agent.tool_registry import (
    CONFIRM_AVAILABILITY_CHANGE_TOOL,
    OWNER_ADMIN_TOOLS,
    PROPOSE_AVAILABILITY_CHANGE_TOOL,
    STAFF_TOOLS,
    VERIFY_ALTERNATIVE_SLOT_TOOL,
    VERIFY_BOOKING_INTENT_TOOL,
    VERIFY_CONFLICT_CHECK_TOOL,
    get_tools_for_role,
)
from app.domain.alternative_slot_verification import (
    AlternativeSlotSuggestion,
    VerifiedAlternativeSlotSuggestion,
)
from app.domain.appointments import ResolvedBookingCandidate
from app.domain.booking_intent_verification import VerifiedBookingIntent
from app.domain.conflict_verification import VerifiedConflictCheck
from app.domain.conflicts import ConflictCheckResult
from app.models.staff import StaffRole

STAFF_SPEAKER = SpeakerContext(id=1, name="Dr. Rao", role=StaffRole.STAFF)
OWNER_ADMIN_SPEAKER = SpeakerContext(id=2, name="Ramesh", role=StaffRole.OWNER_ADMIN)


def _unique_session_id() -> str:
    return f"session-{uuid.uuid4()}"


def _make_verified_booking_intent(service_name: str = "Haircut") -> VerifiedBookingIntent:
    return VerifiedBookingIntent(
        intent=BookingIntent(service_name=service_name), verified=False
    )


def _make_verified_alternative_slot() -> VerifiedAlternativeSlotSuggestion:
    return VerifiedAlternativeSlotSuggestion(
        suggestion=AlternativeSlotSuggestion(
            requested_time=datetime(2026, 9, 18, 9, 0),
            unavailable_reason="Requested slot already booked",
            alternative=ResolvedBookingCandidate(
                service_name="Haircut",
                start_time=datetime(2026, 9, 18, 10, 0),
                staff_name="Dr. Rao",
            ),
        ),
        verified=False,
    )


def _make_verified_conflict_check() -> VerifiedConflictCheck:
    return VerifiedConflictCheck(
        result=ConflictCheckResult(has_conflict=False, conflicting_bookings=[]),
        verified=False,
    )


@pytest.fixture(autouse=True)
def _reset_pending_verification_store() -> None:
    """Every test starts with a clean pending-verification slot for each type."""
    pending_verification_store.set_pending_booking_intent(None)
    pending_verification_store.set_pending_alternative_slot(None)
    pending_verification_store.set_pending_conflict_check(None)
    yield
    pending_verification_store.set_pending_booking_intent(None)
    pending_verification_store.set_pending_alternative_slot(None)
    pending_verification_store.set_pending_conflict_check(None)


# --- Role-scoped visibility -------------------------------------------------


def test_staff_tools_include_availability_change_and_verification_tools() -> None:
    tools = get_tools_for_role(StaffRole.STAFF)
    names = {tool.name for tool in tools}

    assert names == {
        "verify_booking_intent",
        "verify_alternative_slot",
        "verify_conflict_check",
        "propose_availability_change",
        "confirm_availability_change",
    }
    assert not any("catalog" in name for name in names)


def test_owner_admin_tools_include_only_verification_tools() -> None:
    tools = get_tools_for_role(StaffRole.OWNER_ADMIN)
    names = {tool.name for tool in tools}

    assert names == {
        "verify_booking_intent",
        "verify_alternative_slot",
        "verify_conflict_check",
    }
    assert "propose_availability_change" not in names
    assert "confirm_availability_change" not in names


def test_get_tools_for_role_returns_independent_list_copies() -> None:
    first_call = get_tools_for_role(StaffRole.STAFF)
    first_call.append(CONFIRM_AVAILABILITY_CHANGE_TOOL)

    second_call = get_tools_for_role(StaffRole.STAFF)

    assert len(second_call) == len(STAFF_TOOLS)


def test_registry_lists_reference_the_same_tool_specs() -> None:
    assert PROPOSE_AVAILABILITY_CHANGE_TOOL in STAFF_TOOLS
    assert CONFIRM_AVAILABILITY_CHANGE_TOOL in STAFF_TOOLS
    assert PROPOSE_AVAILABILITY_CHANGE_TOOL not in OWNER_ADMIN_TOOLS
    assert CONFIRM_AVAILABILITY_CHANGE_TOOL not in OWNER_ADMIN_TOOLS


# --- Tool schema shape -------------------------------------------------


@pytest.mark.parametrize(
    "tool",
    [
        VERIFY_BOOKING_INTENT_TOOL,
        VERIFY_ALTERNATIVE_SLOT_TOOL,
        VERIFY_CONFLICT_CHECK_TOOL,
        PROPOSE_AVAILABILITY_CHANGE_TOOL,
        CONFIRM_AVAILABILITY_CHANGE_TOOL,
    ],
)
def test_tool_schema_matches_llm_provider_function_calling_shape(tool) -> None:
    assert tool.schema["type"] == "function"
    function = tool.schema["function"]
    assert function["name"] == tool.name
    assert isinstance(function["description"], str) and function["description"]
    assert "properties" in function["parameters"]


# --- Verification dispatch adapters: nothing pending ------------------------


@pytest.mark.asyncio
async def test_dispatch_verify_booking_intent_with_nothing_pending_returns_clear_result() -> None:
    result = await VERIFY_BOOKING_INTENT_TOOL.dispatch(
        db=None,
        session_id=_unique_session_id(),
        speaker=STAFF_SPEAKER,
        args={"verified": True},
    )

    assert isinstance(result, dict)
    assert result["error"] == "nothing_pending"
    json.dumps(result)


@pytest.mark.asyncio
async def test_dispatch_verify_alternative_slot_with_nothing_pending_returns_clear_result() -> None:
    result = await VERIFY_ALTERNATIVE_SLOT_TOOL.dispatch(
        db=None,
        session_id=_unique_session_id(),
        speaker=STAFF_SPEAKER,
        args={"verified": True},
    )

    assert isinstance(result, dict)
    assert result["error"] == "nothing_pending"
    json.dumps(result)


@pytest.mark.asyncio
async def test_dispatch_verify_conflict_check_with_nothing_pending_returns_clear_result() -> None:
    result = await VERIFY_CONFLICT_CHECK_TOOL.dispatch(
        db=None,
        session_id=_unique_session_id(),
        speaker=STAFF_SPEAKER,
        args={"verified": True},
    )

    assert isinstance(result, dict)
    assert result["error"] == "nothing_pending"
    json.dumps(result)


# --- Verification dispatch adapters: pending item set -----------------------


@pytest.mark.asyncio
async def test_dispatch_verify_booking_intent_with_pending_item_calls_underlying_function() -> None:
    pending = _make_verified_booking_intent()
    pending_verification_store.set_pending_booking_intent(pending)

    with patch(
        "app.agent.tool_registry.verify_booking_intent",
        return_value=_make_verified_booking_intent("Manicure").model_copy(
            update={"verified": True}
        ),
    ) as mock_verify:
        result = await VERIFY_BOOKING_INTENT_TOOL.dispatch(
            db=None,
            session_id=_unique_session_id(),
            speaker=STAFF_SPEAKER,
            args={"verified": True, "service_name": "Manicure"},
        )

    mock_verify.assert_called_once()
    called_pending, called_args = mock_verify.call_args.args
    assert called_pending == pending
    assert called_args.verified is True
    assert called_args.service_name == "Manicure"

    assert isinstance(result, dict)
    json.dumps(result)
    assert pending_verification_store.get_pending_booking_intent() is None


@pytest.mark.asyncio
async def test_dispatch_verify_alternative_slot_with_pending_item_calls_underlying_function() -> None:
    pending = _make_verified_alternative_slot()
    pending_verification_store.set_pending_alternative_slot(pending)

    with patch(
        "app.agent.tool_registry.verify_alternative_slot",
        return_value=_make_verified_alternative_slot().model_copy(update={"verified": True}),
    ) as mock_verify:
        result = await VERIFY_ALTERNATIVE_SLOT_TOOL.dispatch(
            db=None,
            session_id=_unique_session_id(),
            speaker=STAFF_SPEAKER,
            args={"verified": True},
        )

    mock_verify.assert_called_once()
    called_pending, called_args = mock_verify.call_args.args
    assert called_pending == pending
    assert called_args.verified is True

    assert isinstance(result, dict)
    json.dumps(result)
    assert pending_verification_store.get_pending_alternative_slot() is None


@pytest.mark.asyncio
async def test_dispatch_verify_conflict_check_with_pending_item_calls_underlying_function() -> None:
    pending = _make_verified_conflict_check()
    pending_verification_store.set_pending_conflict_check(pending)

    with patch(
        "app.agent.tool_registry.verify_conflict_check",
        return_value=_make_verified_conflict_check().model_copy(update={"verified": True}),
    ) as mock_verify:
        result = await VERIFY_CONFLICT_CHECK_TOOL.dispatch(
            db=None,
            session_id=_unique_session_id(),
            speaker=STAFF_SPEAKER,
            args={"verified": True},
        )

    mock_verify.assert_called_once()
    called_pending, called_args = mock_verify.call_args.args
    assert called_pending == pending
    assert called_args.verified is True

    assert isinstance(result, dict)
    json.dumps(result)
    assert pending_verification_store.get_pending_conflict_check() is None


# --- Availability-change dispatch adapters (Task 3 bridging) ----------------


@pytest.mark.asyncio
async def test_dispatch_propose_availability_change_calls_underlying_tool() -> None:
    with patch(
        "app.agent.tool_registry.propose_availability_change",
        AsyncMock(return_value={"declined": False, "restatement": "Restated text"}),
    ) as mock_propose:
        result = await PROPOSE_AVAILABILITY_CHANGE_TOOL.dispatch(
            db=None,
            session_id="session-1",
            speaker=STAFF_SPEAKER,
            args={"message": "I'm unavailable Friday morning"},
        )

    mock_propose.assert_called_once()
    called_session_id, called_speaker, called_args = mock_propose.call_args.args
    assert called_session_id == "session-1"
    assert called_speaker == STAFF_SPEAKER
    assert called_args.message == "I'm unavailable Friday morning"

    assert result == {"declined": False, "restatement": "Restated text"}
    json.dumps(result)


@pytest.mark.asyncio
async def test_dispatch_confirm_availability_change_calls_underlying_tool() -> None:
    with patch(
        "app.agent.tool_registry.confirm_availability_change",
        AsyncMock(return_value={"confirmed": True, "applied": True, "availability_id": 7}),
    ) as mock_confirm:
        result = await CONFIRM_AVAILABILITY_CHANGE_TOOL.dispatch(
            db="fake-db-session",
            session_id="session-1",
            speaker=STAFF_SPEAKER,
            args={"confirmed": True},
        )

    mock_confirm.assert_called_once()
    called_db, called_session_id, called_speaker, called_args = mock_confirm.call_args.args
    assert called_db == "fake-db-session"
    assert called_session_id == "session-1"
    assert called_speaker == STAFF_SPEAKER
    assert called_args.confirmed is True

    assert result == {"confirmed": True, "applied": True, "availability_id": 7}
    json.dumps(result)
