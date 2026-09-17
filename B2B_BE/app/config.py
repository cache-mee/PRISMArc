from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "salon-app-backend"
    app_env: str = "development"
    debug: bool = False
    database_url: str | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5-20251001"


settings = Settings()
