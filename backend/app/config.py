from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://lenny:change-me-before-sharing@postgres:5432/lenny_growth"
    ai_provider: str = "ollama"
    fallback_provider: str | None = None
    ollama_model: str = "qwen2.5:7b"
    ollama_base_url: str = "http://host.docker.internal:11434"
    anthropic_model: str = "claude-sonnet-4-5"


@lru_cache
def get_settings() -> Settings:
    return Settings()
