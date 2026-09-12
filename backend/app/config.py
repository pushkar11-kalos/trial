"""
Central application settings, loaded from environment variables / .env.

Nothing here requires a paid API key. OCR_PROVIDER defaults to "mock" so the
whole application is fully functional offline / without credentials.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "MetraCheck"
    ENV: str = "development"

    # Falls back to a local SQLite file if no DATABASE_URL is provided, so the
    # backend can be run standalone (e.g. for tests) with zero configuration.
    DATABASE_URL: str = "sqlite:///./metracheck.db"

    JWT_SECRET_KEY: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 12

    ALLOWED_ORIGINS: str = "http://localhost:3000"

    OCR_PROVIDER: str = "mock"  # "mock" | "tesseract" | "gemini"

    # Google Gemini Vision API settings (used when OCR_PROVIDER="gemini")
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    STORAGE_BACKEND: str = "local"  # "local" | (future) "s3"
    STORAGE_ROOT: str = "./storage/uploads"
    DEMO_ASSETS_ROOT: str = "./storage/demo_assets"
    MAX_UPLOAD_MB: int = 10

    OCR_REVIEW_CONFIDENCE_THRESHOLD: int = 75

    RULE_PACK_NAME: str = "PC Rules 2011 + Amendments — Demo v1"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
