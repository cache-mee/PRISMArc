import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.providers.base import LLMResponse
from app.agent.providers.litellm_provider import LiteLLMProvider, LLMGenerationError


def _mock_completion_response(*, content: str | None, tool_calls: list | None):
    """Builds a fake ``litellm.acompletion`` response carrying ``response.choices[0].message``,
    matching the real shape confirmed against the installed ``litellm`` (1.101.0)
    ``Message``/``ChatCompletionMessageToolCall``/``Function`` types.
    """
    from litellm.types.utils import ChatCompletionMessageToolCall, Function, Message

    message = Message(
        content=content,
        role="assistant",
        tool_calls=(
            [
                ChatCompletionMessageToolCall(
                    id=tc["id"],
                    type="function",
                    function=Function(name=tc["name"], arguments=tc["arguments"]),
                )
                for tc in tool_calls
            ]
            if tool_calls
            else None
        ),
    )
    choice = type("Choice", (), {"message": message})()
    return type("Response", (), {"choices": [choice]})()


@pytest.mark.asyncio
async def test_generate_builds_expected_request_and_maps_tool_calls() -> None:
    mock_response = _mock_completion_response(
        content=None,
        tool_calls=[
            {
                "id": "call_1",
                "name": "extract_booking_intent",
                "arguments": json.dumps({"service_name": "Haircut"}),
            }
        ],
    )
    mock_acompletion = AsyncMock(return_value=mock_response)

    provider = LiteLLMProvider(
        model="anthropic/claude-haiku-4-5-20251001", api_key="sk-test"
    )
    messages = [{"role": "user", "content": "book a haircut"}]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "extract_booking_intent",
                "description": "Record the booking intent.",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]

    with patch(
        "app.agent.providers.litellm_provider.litellm.acompletion", mock_acompletion
    ):
        result = await provider.generate(
            system="you are a booking assistant", messages=messages, tools=tools
        )

    mock_acompletion.assert_awaited_once_with(
        model="anthropic/claude-haiku-4-5-20251001",
        api_key="sk-test",
        messages=[
            {"role": "system", "content": "you are a booking assistant"},
            {"role": "user", "content": "book a haircut"},
        ],
        tools=tools,
    )

    assert isinstance(result, LLMResponse)
    assert result.text is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call_1"
    assert result.tool_calls[0].name == "extract_booking_intent"
    assert result.tool_calls[0].args == {"service_name": "Haircut"}
    assert result.raw_message["role"] == "assistant"


@pytest.mark.asyncio
async def test_generate_maps_zero_tool_calls_response() -> None:
    mock_response = _mock_completion_response(
        content="just a plain reply", tool_calls=None
    )
    mock_acompletion = AsyncMock(return_value=mock_response)

    provider = LiteLLMProvider(
        model="anthropic/claude-haiku-4-5-20251001", api_key="sk-test"
    )

    with patch(
        "app.agent.providers.litellm_provider.litellm.acompletion", mock_acompletion
    ):
        result = await provider.generate(
            system="system prompt",
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
        )

    assert result.text == "just a plain reply"
    assert result.tool_calls == []


@pytest.mark.asyncio
async def test_generate_raises_specific_error_when_acompletion_fails() -> None:
    mock_acompletion = AsyncMock(side_effect=RuntimeError("upstream provider error"))

    provider = LiteLLMProvider(
        model="anthropic/claude-haiku-4-5-20251001", api_key="sk-test"
    )

    with patch(
        "app.agent.providers.litellm_provider.litellm.acompletion", mock_acompletion
    ):
        with pytest.raises(LLMGenerationError):
            await provider.generate(system="system prompt", messages=[], tools=[])
