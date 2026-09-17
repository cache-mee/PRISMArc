"""``litellm``-backed implementation of ``LLMProvider``.

``litellm`` (https://github.com/BerriAI/litellm) exposes a single ``acompletion()``
interface across Anthropic, OpenAI, Azure, Gemini, Grok, etc., inferring the provider
from a ``provider/model`` prefix in the model string (e.g.
``anthropic/claude-haiku-4-5-20251001``). This module is the one call path every LLM
call site in ``app/agent/`` goes through, regardless of which provider/model
``settings.llm_model`` currently points at.

Response-shape note: the extraction logic below (``message.tool_calls[i].function.name``
/ ``.function.arguments`` as a JSON string, ``message.model_dump()`` for
``raw_message``) was confirmed against the actually-installed ``litellm`` version
(1.101.0) — ``litellm.types.utils.Message``/``ChatCompletionMessageToolCall``/
``Function`` — before this code was written, not assumed from documentation alone.
"""

import json

import litellm

from app.agent.providers.base import LLMResponse, ToolCall


class LLMGenerationError(RuntimeError):
    """Raised when the underlying ``litellm.acompletion`` call itself fails.

    Wraps whatever ``litellm`` raised (a provider HTTP error, an auth error, etc.) in a
    single, specific exception type for this module, rather than letting callers catch a
    bare, unspecified exception from a third-party library.
    """


class LiteLLMProvider:
    """``LLMProvider`` implementation backed by ``litellm.acompletion``."""

    def __init__(self, model: str, api_key: str | None) -> None:
        self.model = model
        self.api_key = api_key

    async def generate(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> LLMResponse:
        try:
            response = await litellm.acompletion(
                model=self.model,
                api_key=self.api_key,
                messages=[{"role": "system", "content": system}, *messages],
                tools=tools,
            )
        except Exception as exc:
            raise LLMGenerationError(
                f"litellm.acompletion failed for model {self.model!r}: {exc}"
            ) from exc

        message = response.choices[0].message
        tool_calls = [
            ToolCall(tc.id, tc.function.name, json.loads(tc.function.arguments))
            for tc in (message.tool_calls or [])
        ]
        return LLMResponse(message.content, tool_calls, message.model_dump())
