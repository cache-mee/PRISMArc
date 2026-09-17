from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.availability_intent import (
    NoToolCallReturnedError,
    parse_availability_change,
)
from app.agent.providers.base import LLMResponse, ToolCall
from app.domain.availability import ProposedAvailabilityChange


def _mock_generate(args: dict) -> AsyncMock:
    """Builds an ``AsyncMock`` for ``LiteLLMProvider.generate`` returning one tool call."""
    return AsyncMock(
        return_value=LLMResponse(
            text=None,
            tool_calls=[
                ToolCall(id="call_1", name="extract_availability_change", args=args)
            ],
            raw_message={"role": "assistant"},
        )
    )


@pytest.mark.asyncio
async def test_parse_availability_change_extracts_blocked_window() -> None:
    mock_generate = _mock_generate(
        {
            "start_time": "2026-09-18T09:00:00",
            "end_time": "2026-09-18T13:00:00",
            "blocked": True,
        }
    )

    with patch(
        "app.agent.availability_intent.LiteLLMProvider.generate", mock_generate
    ):
        change = await parse_availability_change(
            "block out Friday morning", staff_name="Meena"
        )

    assert isinstance(change, ProposedAvailabilityChange)
    assert change.start_time == datetime(2026, 9, 18, 9, 0, 0)
    assert change.end_time == datetime(2026, 9, 18, 13, 0, 0)
    assert change.blocked is True


@pytest.mark.asyncio
async def test_parse_availability_change_extracts_unblocked_window() -> None:
    mock_generate = _mock_generate(
        {
            "start_time": "2026-09-19T00:00:00",
            "end_time": "2026-09-19T23:59:59",
            "blocked": False,
        }
    )

    with patch(
        "app.agent.availability_intent.LiteLLMProvider.generate", mock_generate
    ):
        change = await parse_availability_change(
            "unblock Saturday", staff_name="Ravi"
        )

    assert change.blocked is False


@pytest.mark.asyncio
async def test_parse_availability_change_passes_through_staff_name() -> None:
    mock_generate = _mock_generate(
        {
            "start_time": "2026-09-18T09:00:00",
            "end_time": "2026-09-18T13:00:00",
            "blocked": True,
        }
    )

    with patch(
        "app.agent.availability_intent.LiteLLMProvider.generate", mock_generate
    ):
        change = await parse_availability_change(
            "block out Friday morning", staff_name="Asha"
        )

    assert change.staff_name == "Asha"


@pytest.mark.asyncio
async def test_parse_availability_change_always_sets_confirmed_false() -> None:
    mock_generate = _mock_generate(
        {
            "start_time": "2026-09-18T09:00:00",
            "end_time": "2026-09-18T13:00:00",
            "blocked": True,
        }
    )

    with patch(
        "app.agent.availability_intent.LiteLLMProvider.generate", mock_generate
    ):
        change = await parse_availability_change(
            "block out Friday morning", staff_name="Meena"
        )

    assert change.confirmed is False


@pytest.mark.asyncio
async def test_parse_availability_change_raises_when_no_tool_call_returned() -> None:
    mock_generate = AsyncMock(
        return_value=LLMResponse(text="a plain reply", tool_calls=[], raw_message={})
    )

    with patch(
        "app.agent.availability_intent.LiteLLMProvider.generate", mock_generate
    ):
        with pytest.raises(NoToolCallReturnedError):
            await parse_availability_change("block out Friday morning", staff_name="Meena")
