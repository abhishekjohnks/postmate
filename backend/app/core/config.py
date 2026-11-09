from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    app_name: str = "PostMate"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "postmate_db"
    postgres_user: str = "postgres"
    postgres_password: str
    jwt_secret: str = Field(min_length=32)
    encryption_key: str
    cors_origins: list[str] = ["http://localhost:5173"]
    storage_dir: Path = Path("storage")
    token_minutes: int = Field(default=30, ge=5, le=120)
    enable_scheduler: bool = True
    app_timezone: str = "Asia/Kolkata"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_url(self) -> URL:
        return URL.create("postgresql+psycopg", username=self.postgres_user,
                          password=self.postgres_password, host=self.postgres_host,
                          port=self.postgres_port, database=self.postgres_db)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def today():
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()
