"""Application settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    brightdata_api_token: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"
    database_url: str = "sqlite:///./backend/sentinelscrape.db"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    scheduler_interval_minutes: int = 30
    competitor_sources_json: str = "[]"
    slack_webhook_url: str = ""
    discord_webhook_url: str = ""
    app_env: str = "development"
    operations_api_token: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=str(REPO_ROOT / ".env"), extra="ignore")


settings = Settings()


def normalize_database_url(database_url: str) -> str:
    """Resolve local SQLite URLs from the repository root, independent of cwd."""

    prefix = "sqlite:///./"
    if database_url.startswith(prefix):
        database_path = (REPO_ROOT / database_url.removeprefix(prefix)).resolve()
        return f"sqlite:///{database_path.as_posix()}"
    return database_url


settings.database_url = normalize_database_url(settings.database_url)


def cors_origin_list() -> list[str]:
    return [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
