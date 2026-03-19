"""Application configuration."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings from environment variables."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
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
    serper_api_key: str | None = None  # Serper.dev (LinkedIn post search via Google)

    # LLM
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # App
    debug: bool = False
    environment: str = "development"


settings = Settings()
