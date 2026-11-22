"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

QUEUE_NAME = "scraper_jobs"
WORKER_POLL_INTERVAL = 5
JOB_TIMEOUT_SECONDS = 120

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Runtime settings loaded from `.env` or process environment."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    supabase_url: str
    supabase_anon_key: str
    cf_account_id: str
    cf_browser_api_token: str
    internal_secret: str
    port: int


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
