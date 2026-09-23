from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Loaded separately from — and before — pydantic-settings' own ``env_file`` mechanism
# below: that mechanism feeds ``.env`` values into *this* Settings object only, it never
# calls ``os.environ.update()`` (confirmed directly: a key present in ``.env`` is not
# visible via ``os.environ`` afterwards). A library that reads real process env vars
# itself rather than through this class — boto3's own default credential provider chain,
# for AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/AWS_SESSION_TOKEN/AWS_REGION, see
# app.agent.providers.bedrock_provider — would otherwise never see them. A no-op if
# ``.env`` doesn't exist (production/Docker gets real env vars from the platform
# instead; ``.dockerignore`` excludes ``.env`` from the image). Mirrors the working
# Node.js reference's ``import 'dotenv/config'`` (Node's dotenv package does mutate
# ``process.env``, which is why that reference's own code never reads credentials
# itself either).
load_dotenv(".env")


class Settings(BaseSettings):
    # ``extra="ignore"``: pydantic-settings defaults to forbidding any ``.env`` key that
    # isn't a field here, but ``.env`` also carries config for other tools that read the
    # process environment directly rather than through this class — e.g. ``UVICORN_LOOP``,
    # consumed by uvicorn's own CLI (auto_envvar_prefix="UVICORN") to force a Windows-
    # compatible event loop for psycopg, and the AWS credential vars above. Without this,
    # such a key crashes the app at import time with a pydantic ``extra_forbidden``
    # ValidationError.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "salon-app-backend"
    app_env: str = "development"
    debug: bool = False
    database_url: str | None = None
    # Bedrock modelId or cross-region inference-profile id (most current models are only
    # callable through an inference profile — the "global."/"us."/"apac." prefixed ids —
    # not the bare foundation-model id). Confirmed working on this account/region.
    bedrock_model_id: str = "global.amazon.nova-2-lite-v1:0"
    bedrock_max_tokens: int = 4096
    bedrock_temperature: float = 0.7
    bedrock_top_p: float = 0.9
    # Named ``aws_region`` (env ``AWS_REGION``), not ``aws_region_name``: this is boto3's
    # own native env var (and the verified Node.js reference's), not a litellm-specific
    # convention — passing it through explicitly, rather than relying on boto3's own
    # AWS_REGION resolution, keeps region_name visible at the BedrockProvider call site.
    aws_region: str | None = None
    # AWS credentials (AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/AWS_SESSION_TOKEN)
    # are deliberately NOT fields here: app.agent.providers.bedrock_provider hands
    # boto3 only ``region_name`` and lets boto3's own default credential provider
    # chain (env vars, a shared profile, or an IAM role) resolve credentials —
    # this app's code never reads or handles the credential values themselves.


settings = Settings()
