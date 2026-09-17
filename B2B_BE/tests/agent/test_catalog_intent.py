from unittest.mock import AsyncMock, patch

import pytest

from app.agent.catalog_intent import NoToolCallReturnedError, is_catalog_change_request
from app.agent.providers.base import LLMResponse, ToolCall


def _mock_generate(is_catalog_change: bool) -> AsyncMock:
    """Builds an ``AsyncMock`` for ``LiteLLMProvider.generate`` returning one tool call."""
    return AsyncMock(
        return_value=LLMResponse(
            text=None,
            tool_calls=[
                ToolCall(
                    id="call_1",
                    name="classify_catalog_change_request",
                    args={"is_catalog_change": is_catalog_change},
                )
            ],
            raw_message={"role": "assistant"},
        )
    )


@pytest.mark.parametrize(
    "text",
    [
        "add beard trim for 150 rupees",
        "change haircut to 350",
        "remove beard trim",
    ],
)
@pytest.mark.asyncio
async def test_is_catalog_change_request_true_for_catalog_write_messages(text: str) -> None:
    mock_generate = _mock_generate(is_catalog_change=True)

    with patch("app.agent.catalog_intent.LiteLLMProvider.generate", mock_generate):
        assert await is_catalog_change_request(text) is True


@pytest.mark.asyncio
async def test_is_catalog_change_request_false_for_availability_message() -> None:
    mock_generate = _mock_generate(is_catalog_change=False)

    with patch("app.agent.catalog_intent.LiteLLMProvider.generate", mock_generate):
        assert await is_catalog_change_request("block out Friday morning") is False


@pytest.mark.asyncio
async def test_is_catalog_change_request_raises_when_no_tool_call_returned() -> None:
    mock_generate = AsyncMock(
        return_value=LLMResponse(text="a plain reply", tool_calls=[], raw_message={})
    )

    with patch("app.agent.catalog_intent.LiteLLMProvider.generate", mock_generate):
        with pytest.raises(NoToolCallReturnedError):
            await is_catalog_change_request("how much is a haircut?")
