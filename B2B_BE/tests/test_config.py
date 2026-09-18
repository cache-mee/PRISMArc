import pytest

from app.config import Settings


def test_settings_defaults_to_verified_bedrock_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``bedrock_model_id`` defaults to the modelId already confirmed working against this
    AWS account/region (see ``app.agent.providers.bedrock_provider``) — no key/token field
    is needed since boto3's own default credential provider chain resolves AWS credentials,
    not this Settings class.
    """
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)

    settings = Settings(_env_file=None)

    assert settings.bedrock_model_id == "global.amazon.nova-2-lite-v1:0"
    assert settings.bedrock_max_tokens == 4096
    assert settings.bedrock_temperature == 0.7
    assert settings.bedrock_top_p == 0.9
    assert settings.aws_region is None


def test_settings_reads_bedrock_model_id_and_region_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``BEDROCK_MODEL_ID``/``AWS_REGION`` env vars override the defaults, per
    pydantic-settings' standard env-var binding (case-insensitive by field name).
    ``AWS_REGION`` (not ``AWS_REGION_NAME``) matches boto3's own native env var and the
    verified Node.js reference's convention.
    """
    monkeypatch.setenv(
        "BEDROCK_MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    )
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    settings = Settings(_env_file=None)

    assert settings.bedrock_model_id == "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    assert settings.aws_region == "us-east-1"


def test_settings_ignores_aws_credential_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """AWS credential env vars are not Settings fields at all — ``extra="ignore"`` lets
    them coexist in ``.env`` for boto3's own default credential chain to read directly,
    without this class raising a pydantic ``extra_forbidden`` validation error.
    """
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAEXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "example-secret")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "example-session-token")

    settings = Settings(_env_file=None)

    assert not hasattr(settings, "aws_access_key_id")
    assert not hasattr(settings, "aws_secret_access_key")
    assert not hasattr(settings, "aws_session_token")
