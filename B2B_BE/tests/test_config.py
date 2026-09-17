import pytest

from app.config import Settings


def test_settings_defaults_to_anthropic_llm_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """``llm_model``/``llm_api_key`` are the single generic model+key pair (replacing the old
    ``anthropic_model``/``anthropic_api_key`` fields) — default model is the pinned Anthropic
    model, provider-prefixed per ``litellm``'s routing convention, and no key is required.
    """
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.llm_model == "anthropic/claude-haiku-4-5-20251001"
    assert settings.llm_api_key is None


def test_settings_reads_llm_model_and_api_key_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``LLM_MODEL``/``LLM_API_KEY`` env vars override the defaults, per pydantic-settings'
    standard env-var binding (case-insensitive by field name).
    """
    monkeypatch.setenv("LLM_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("LLM_API_KEY", "test-key-123")

    settings = Settings(_env_file=None)

    assert settings.llm_model == "openai/gpt-4o-mini"
    assert settings.llm_api_key == "test-key-123"
