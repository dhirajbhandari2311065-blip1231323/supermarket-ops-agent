import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", None)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./supermarket.db")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignores any extra env variables not explicitly defined above
    )


settings = Settings()