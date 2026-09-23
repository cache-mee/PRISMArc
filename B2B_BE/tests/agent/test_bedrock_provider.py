import json
from unittest.mock import MagicMock

import pytest

from app.agent.providers.base import LLMResponse
from app.agent.providers.bedrock_provider import (
    BedrockProvider,
    LLMGenerationError,
    _to_converse_messages,
    _to_converse_tool_config,
)


def _provider() -> BedrockProvider:
    """A ``BedrockProvider`` with its real boto3 client's ``.converse`` swapped for a
    ``MagicMock`` — constructing a boto3 client never makes a network call or needs real
    credentials, only the actual ``.converse()`` invocation does.
    """
    provider = BedrockProvider(model="global.amazon.nova-2-lite-v1:0", region_name="ap-south-1")
    provider._client.converse = MagicMock()
    return provider


def _converse_response(*, text: str | None, tool_uses: list[dict] | None) -> dict:
    content = []
    if text is not None:
        content.append({"text": text})
    for tool_use in tool_uses or []:
        content.append({"toolUse": tool_use})
    return {"output": {"message": {"role": "assistant", "content": content}}}


@pytest.mark.asyncio
async def test_generate_builds_expected_request_and_maps_tool_calls() -> None:
    provider = _provider()
    provider._client.converse.return_value = _converse_response(
        text=None,
        tool_uses=[
            {
                "toolUseId": "call_1",
                "name": "extract_booking_intent",
                "input": {"service_name": "Haircut"},
            }
        ],
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

    result = await provider.generate(
        system="you are a booking assistant", messages=messages, tools=tools
    )

    provider._client.converse.assert_called_once_with(
        modelId="global.amazon.nova-2-lite-v1:0",
        system=[{"text": "you are a booking assistant"}],
        messages=[{"role": "user", "content": [{"text": "book a haircut"}]}],
        inferenceConfig={"maxTokens": 4096, "temperature": 0.7, "topP": 0.9},
        toolConfig={
            "tools": [
                {
                    "toolSpec": {
                        "name": "extract_booking_intent",
                        "description": "Record the booking intent.",
                        "inputSchema": {"json": {"type": "object", "properties": {}}},
                    }
                }
            ]
        },
    )

    assert isinstance(result, LLMResponse)
    assert result.text is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call_1"
    assert result.tool_calls[0].name == "extract_booking_intent"
    assert result.tool_calls[0].args == {"service_name": "Haircut"}
    assert result.raw_message == {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "extract_booking_intent",
                    "arguments": json.dumps({"service_name": "Haircut"}),
                },
            }
        ],
    }


@pytest.mark.asyncio
async def test_generate_maps_zero_tool_calls_response_and_omits_tool_config() -> None:
    provider = _provider()
    provider._client.converse.return_value = _converse_response(
        text="just a plain reply", tool_uses=None
    )

    result = await provider.generate(
        system="system prompt",
        messages=[{"role": "user", "content": "hi"}],
        tools=[],
    )

    _, kwargs = provider._client.converse.call_args
    assert "toolConfig" not in kwargs
    assert result.text == "just a plain reply"
    assert result.tool_calls == []
    assert result.raw_message == {
        "role": "assistant",
        "content": "just a plain reply",
        "tool_calls": None,
    }


@pytest.mark.asyncio
async def test_generate_raises_specific_error_when_converse_fails() -> None:
    provider = _provider()
    provider._client.converse.side_effect = RuntimeError("upstream Bedrock error")

    with pytest.raises(LLMGenerationError):
        await provider.generate(system="system prompt", messages=[], tools=[])


def test_to_converse_tool_config_returns_none_for_empty_tools() -> None:
    assert _to_converse_tool_config([]) is None


def test_to_converse_messages_coalesces_consecutive_tool_results_into_one_user_message() -> None:
    """The OpenAI-shape history a full tool-calling turn leaves behind — one assistant
    message with two tool calls, followed by two separate ``role: "tool"`` entries — must
    become exactly one Converse ``user`` message carrying both ``toolResult`` blocks, since
    Converse has no "tool" role and rejects unmatched/split-up tool results.
    """
    history = [
        {"role": "user", "content": "book a haircut and a shave"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "check_availability", "arguments": '{"service": "Haircut"}'},
                },
                {
                    "id": "call_2",
                    "type": "function",
                    "function": {"name": "check_availability", "arguments": '{"service": "Shave"}'},
                },
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": '{"available": true}'},
        {"role": "tool", "tool_call_id": "call_2", "content": '{"available": false}'},
    ]

    converse_messages = _to_converse_messages(history)

    assert converse_messages == [
        {"role": "user", "content": [{"text": "book a haircut and a shave"}]},
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "call_1",
                        "name": "check_availability",
                        "input": {"service": "Haircut"},
                    }
                },
                {
                    "toolUse": {
                        "toolUseId": "call_2",
                        "name": "check_availability",
                        "input": {"service": "Shave"},
                    }
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "call_1",
                        "content": [{"text": '{"available": true}'}],
                    }
                },
                {
                    "toolResult": {
                        "toolUseId": "call_2",
                        "content": [{"text": '{"available": false}'}],
                    }
                },
            ],
        },
    ]
