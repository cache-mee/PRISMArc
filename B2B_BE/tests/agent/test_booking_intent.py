import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.booking_intent import (
    NoToolCallReturnedError,
    ServiceNotStatedError,
    parse_booking_intent,
)
from app.agent.providers.base import LLMResponse, ToolCall

KNOWN_SERVICES = ["Haircut", "Beard Trim"]
KNOWN_STAFF = ["Asha", "Ravi"]


def _mock_generate(args: dict) -> AsyncMock:
    """Builds an ``AsyncMock`` for ``LiteLLMProvider.generate`` returning one tool call."""
    return AsyncMock(
        return_value=LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="call_1", name="extract_booking_intent", args=args)],
            raw_message={"role": "assistant"},
        )
    )


@pytest.mark.asyncio
async def test_parse_booking_intent_resolves_known_service_case_insensitively() -> None:
    mock_generate = _mock_generate({"service_name": "haircut"})

    with patch(
        "app.agent.booking_intent.LiteLLMProvider.generate", mock_generate
    ):
        intent = await parse_booking_intent(
            "I want a haircut", known_services=KNOWN_SERVICES
        )

    assert intent.service_name == "Haircut"
    assert intent.requested_time is None
    assert intent.staff_preference is None


@pytest.mark.asyncio
async def test_parse_booking_intent_raises_when_service_not_stated() -> None:
    mock_generate = _mock_generate({"service_name": "Massage"})

    with patch(
        "app.agent.booking_intent.LiteLLMProvider.generate", mock_generate
    ):
        with pytest.raises(ServiceNotStatedError):
            await parse_booking_intent(
                "I want a massage", known_services=KNOWN_SERVICES
            )


@pytest.mark.asyncio
async def test_parse_booking_intent_omitted_time_and_staff_stay_none() -> None:
    mock_generate = _mock_generate({"service_name": "Beard Trim"})

    with patch(
        "app.agent.booking_intent.LiteLLMProvider.generate", mock_generate
    ):
        intent = await parse_booking_intent(
            "beard trim please",
            known_services=KNOWN_SERVICES,
            known_staff=KNOWN_STAFF,
        )

    assert intent.service_name == "Beard Trim"
    assert intent.requested_time is None
    assert intent.staff_preference is None


@pytest.mark.asyncio
async def test_parse_booking_intent_raises_when_no_tool_call_returned() -> None:
    mock_generate = AsyncMock(
        return_value=LLMResponse(text="a plain reply", tool_calls=[], raw_message={})
    )

    with patch(
        "app.agent.booking_intent.LiteLLMProvider.generate", mock_generate
    ):
        with pytest.raises(NoToolCallReturnedError):
            await parse_booking_intent("book me something", known_services=KNOWN_SERVICES)
