"""Provider-agnostic LLM call types and interface.

Defines the general seam every LLM call site in ``app/agent/`` calls through, instead of
each call site hardcoding a specific provider SDK (e.g. ``anthropic.Anthropic``). A
concrete implementation (see ``litellm_provider.py``) adapts one real provider-calling
library to this shape; callers depend only on this module, never on a provider SDK
directly.
"""

from typing import Protocol


class ToolCall:
    """One resolved tool invocation returned by the model for a single turn."""

    def __init__(self, id: str, name: str, args: dict) -> None:
        self.id = id
        self.name = name
        self.args = args


class LLMResponse:
    """One model turn's result.

    ``tool_calls`` may be empty (the model did not invoke a tool) or contain more than
    one — this shape does not assume "exactly one forced tool call", even though today's
    callers each only ever read the first element.
    """

    def __init__(
        self, text: str | None, tool_calls: list[ToolCall], raw_message: dict
    ) -> None:
        self.text = text
        self.tool_calls = tool_calls
        self.raw_message = raw_message


class LLMProvider(Protocol):
    """The interface every LLM provider implementation satisfies.

    ``tools`` uses the OpenAI function-calling shape (``{"type": "function", "function":
    {"name", "description", "parameters"}}``) — the same shape ``litellm`` normalizes
    every provider's tool-calling request to, so a future non-``litellm`` implementation
    could still satisfy this same ``Protocol`` without changing any caller.
    """

    async def generate(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> LLMResponse: ...
