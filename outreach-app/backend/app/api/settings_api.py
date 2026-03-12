"""Settings API endpoints."""
from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("")
def get_settings():
    """Get current app settings (masks API keys)."""
    def mask(key: str | None) -> str:
        if not key:
            return "not configured"
        if len(key) <= 8:
            return "****"
        return key[:4] + "****" + key[-4:]

    return {
        "database_url": settings.database_url,
        "environment": settings.environment,
        "debug": settings.debug,
        "api_keys": {
            "newsapi": mask(settings.newsapi_key),
            "hunter": mask(settings.hunter_api_key),
            "mediacloud": mask(settings.mediacloud_api_key),
        },
        "api_key_status": {
            "newsapi": bool(settings.newsapi_key),
            "hunter": bool(settings.hunter_api_key),
            "mediacloud": bool(settings.mediacloud_api_key),
        },
    }
