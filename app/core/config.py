from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WHISPER_", env_file=".env", extra="ignore")

    data_dir: Path = Field(default=Path("./data"))
    model_name: str = Field(default="large-v3-turbo")
    device: str = Field(default="cpu")
    compute_type: str = Field(default="int8")
    log_level: str = Field(default="INFO")
    api_key: str | None = Field(default=None)


@lru_cache
def get_settings() -> Settings:
    return Settings()
