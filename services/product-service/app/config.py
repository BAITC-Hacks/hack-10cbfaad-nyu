from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    product_service_port: int = 8001
    product_database_url: str = (
        "postgresql+psycopg://product:product@postgres:5432/product_db"
    )
    internal_service_token: str = "change-me"
    ekt_api_base_url: str = "https://ekt.kz/api"
    ekt_api_username: str = ""
    ekt_api_password: str = ""
    ekt_http_timeout_seconds: float = Field(default=5.0, gt=0)
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()

