from functools import lru_cache
from typing import List, Optional

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    project_name: str = "Rentware Events"
    database_url: AnyUrl = Field(..., alias="DATABASE_URL")
    test_database_url: Optional[AnyUrl] = Field(None, alias="TEST_DATABASE_URL")

    secret_key: str = Field(..., alias="SECRET_KEY")
    algorithm: str = Field("HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_minutes: int = Field(60 * 24 * 30, alias="REFRESH_TOKEN_EXPIRE_MINUTES")

    allowed_origins: List[str] = Field(default_factory=list, alias="ALLOWED_ORIGINS")

    admin_email: str = Field("admin@example.com", alias="ADMIN_EMAIL")
    admin_password: str = Field("admin", alias="ADMIN_PASSWORD")
    operator_email: str = Field("operator@example.com", alias="OPERATOR_EMAIL")
    operator_password: str = Field("operator", alias="OPERATOR_PASSWORD")
    client_email: str = Field("client@example.com", alias="CLIENT_EMAIL")
    client_password: str = Field("client", alias="CLIENT_PASSWORD")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
