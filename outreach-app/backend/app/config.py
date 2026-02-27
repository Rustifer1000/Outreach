"""Application configuration."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings from environment variables."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
    )

    # Database
    database_url: str = "sqlite:///./outreach.db"

    # API keys (set in .env)
    mediacloud_api_key: str | None = None
    newsapi_key: str | None = None
    hunter_api_key: str | None = None
    anthropic_api_key: str | None = None
    listennotes_api_key: str | None = None  # Podcast search (Listen Notes)
    youtube_api_key: str | None = None  # YouTube Data API v3
    serpapi_key: str | None = None  # SerpApi (speech/presentation search)

    # App
    debug: bool = False
    environment: str = "development"


settings = Settings()
