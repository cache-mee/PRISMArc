"""``boto3``-backed implementation of ``LLMProvider`` calling AWS Bedrock's Converse API
directly, replacing the earlier ``litellm``-mediated approach.

Migrated to match a working Node.js reference (``@aws-sdk/client-bedrock-runtime``'s
``ConverseCommand``) already verified against this AWS account: boto3's
``bedrock-runtime`` client's ``converse()`` operation, authenticated via the AWS SDK's
default credential provider chain (``AWS_ACCESS_KEY_ID``/``AWS_SECRET_ACCESS_KEY``/
``AWS_SESSION_TOKEN`` env vars, a shared profile, or an IAM role) rather than a Bedrock
API-key bearer token — this module never reads or handles the credential values
themselves, exactly like the Node reference's ``config.js``.

``generate()`` still speaks the OpenAI/``litellm``-style message and tool-calling shape
every caller in ``app/agent/`` already uses, and that ``state.history`` is persisted in
(see ``app.agent.state.session_store``) — this module's job is exactly the translation
``litellm`` used to do for us: OpenAI shape in, Bedrock Converse shape out for the actual
API call, then Converse's response translated back to OpenAI shape so ``raw_message``
round-trips through ``state.history`` unchanged across turns. No caller, endpoint, or
conversation-loop logic changes — only how the Bedrock call itself is made.

boto3 is synchronous; ``asyncio.to_thread`` keeps ``generate()`` from blocking the event
loop while the real network call runs, mirroring how every other ``await``-based call
site in this codebase behaves from the caller's perspective.
"""

import asyncio
import json

import boto3

from app.agent.providers.base import LLMResponse, ToolCall


class LLMGenerationError(RuntimeError):
    """Raised when the underlying Bedrock ``converse()`` call itself fails.

    Wraps whatever boto3/botocore raised (a ``ClientError``, a network error, etc.) in a
    single, specific exception type for this module, rather than letting callers catch a
    bare, unspecified exception from a third-party library.
    """


# Mirrors the verified Node.js reference's inference defaults exactly (its
# ``config.js``/``.env.example``) rather than inventing new, untested values.
_DEFAULT_MAX_TOKENS = 4096
_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_TOP_P = 0.9


def _to_converse_tool_config(tools: list[dict]) -> dict | None:
    """OpenAI function-calling ``tools`` shape -> Converse ``toolConfig``.

    Converse rejects an empty ``toolConfig.tools`` list, so this returns ``None`` (meaning
    "omit ``toolConfig`` entirely") rather than ``{"tools": []}`` when there are no tools.
    """
    if not tools:
        return None
    return {
        "tools": [
            {
                "toolSpec": {
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "inputSchema": {"json": tool["function"]["parameters"]},
                }
            }
            for tool in tools
        ]
    }


def _to_converse_messages(messages: list[dict]) -> list[dict]:
    """OpenAI-shape conversation history -> Converse ``messages``.

    The two shapes disagree on tool results: OpenAI represents each tool result as its own
    ``{"role": "tool", "tool_call_id", "content"}`` entry, while Converse has no "tool" role
    at all — every tool result for a given assistant turn must instead be bundled as
    multiple ``toolResult`` content blocks inside a single following ``user`` message. This
    always coalesces consecutive ``"tool"`` entries (exactly the shape
    ``run_booking_conversation``/``run_manager_turn`` append them in, one per dispatched
    tool call) into one such message.
    """
    converse_messages: list[dict] = []
    pending_tool_results: list[dict] = []

    def flush_tool_results() -> None:
        if pending_tool_results:
            converse_messages.append(
                {"role": "user", "content": list(pending_tool_results)}
            )
            pending_tool_results.clear()

    for message in messages:
        role = message["role"]

        if role == "tool":
            pending_tool_results.append(
                {
                    "toolResult": {
                        "toolUseId": message["tool_call_id"],
                        "content": [{"text": message["content"]}],
                    }
                }
            )
            continue

        flush_tool_results()

        if role == "user":
            converse_messages.append(
                {"role": "user", "content": [{"text": message["content"]}]}
            )
        elif role == "assistant":
            content: list[dict] = []
            if message.get("content"):
                content.append({"text": message["content"]})
            for call in message.get("tool_calls") or []:
                content.append(
                    {
                        "toolUse": {
                            "toolUseId": call["id"],
                            "name": call["function"]["name"],
                            "input": json.loads(call["function"]["arguments"]),
                        }
                    }
                )
            converse_messages.append({"role": "assistant", "content": content})
        else:
            raise ValueError(f"Unsupported message role for Bedrock Converse: {role!r}")

    flush_tool_results()
    return converse_messages


def _from_converse_message(message: dict) -> LLMResponse:
    """Converse's ``output.message`` -> ``LLMResponse``, with an OpenAI-shape
    ``raw_message`` (not Converse's own shape) so it round-trips correctly the next time
    ``_to_converse_messages`` sees it in ``state.history``.
    """
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    raw_tool_calls: list[dict] = []

    for block in message.get("content", []):
        if "text" in block:
            text_parts.append(block["text"])
        elif "toolUse" in block:
            tool_use = block["toolUse"]
            tool_calls.append(
                ToolCall(tool_use["toolUseId"], tool_use["name"], tool_use["input"])
            )
            raw_tool_calls.append(
                {
                    "id": tool_use["toolUseId"],
                    "type": "function",
                    "function": {
                        "name": tool_use["name"],
                        "arguments": json.dumps(tool_use["input"]),
                    },
                }
            )

    text = "".join(text_parts) or None
    raw_message = {
        "role": "assistant",
        "content": text,
        "tool_calls": raw_tool_calls or None,
    }
    return LLMResponse(text, tool_calls, raw_message)


class BedrockProvider:
    """``LLMProvider`` implementation backed by boto3's Bedrock Runtime ``converse()``."""

    def __init__(
        self,
        model: str,
        region_name: str | None,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        temperature: float = _DEFAULT_TEMPERATURE,
        top_p: float = _DEFAULT_TOP_P,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self._client = boto3.client("bedrock-runtime", region_name=region_name)

    async def generate(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> LLMResponse:
        request: dict = {
            "modelId": self.model,
            "system": [{"text": system}],
            "messages": _to_converse_messages(messages),
            "inferenceConfig": {
                "maxTokens": self.max_tokens,
                "temperature": self.temperature,
                "topP": self.top_p,
            },
        }
        tool_config = _to_converse_tool_config(tools)
        if tool_config is not None:
            request["toolConfig"] = tool_config

        try:
            response = await asyncio.to_thread(self._client.converse, **request)
        except Exception as exc:
            raise LLMGenerationError(
                f"Bedrock converse() failed for model {self.model!r}: {exc}"
            ) from exc

        return _from_converse_message(response["output"]["message"])
