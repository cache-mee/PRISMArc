from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_REPO_ROOT_ENV, extra="ignore")

    rds_host: str
    rds_port: int = 5432
    rds_user: str
    rds_password: str
    rds_db: str

    app_env: str = "development"
    debug: bool = False
    backend_port: int = 8000

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.rds_user}:{self.rds_password}"
            f"@{self.rds_host}:{self.rds_port}/{self.rds_db}"
        )


settings = Settings()
