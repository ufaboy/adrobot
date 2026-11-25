from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    cors_origins: list[str] = ["http://localhost:5173"]

    keitaro_api_url: str = "https://keitaro-for-tests.etolegko.com/admin_api"
    keitaro_api_key: SecretStr = SecretStr("")
    google_url: str = "https://google.com"
    default_domain_id: int | None = None
    default_group_id: int | None = None
    default_traffic_source_id: int | None = None
    offers_cache_ttl_minutes: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
