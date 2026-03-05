"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings from environment variables."""

    # Database
    database_url: str = "sqlite:///./outreach.db"

    # API keys (set in .env)
    mediacloud_api_key: str | None = None
    newsapi_key: str | None = None
    hunter_api_key: str | None = None

    # App
    debug: bool = False
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
