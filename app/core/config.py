from enum import StrEnum
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class Evironments(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PROD = "prod"


class OpenAIMode(StrEnum):
    SYNC = "sync"
    ASYNC = "async"


class Settings(BaseSettings):
    """
    Application settings.

    Uses pydantic-settings to load from environment variables and .env files.
    Doc: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
    """

    PROJECT_NAME: str = "OpenAI Batch Tracker"
    CONF_ENV: Evironments = Field(
        default=Evironments.LOCAL,
        description="Configuration environment",
    )

    # Uvicorn server settings (if running from docker, Docker Compose handles this)
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = Field(
        default=8000,
        description="Port for the FastAPI server",
    )

    # # OpeanAI settings
    # Use SecretStr to prevent accidental exposure of the API key.
    # Doc: https://docs.pydantic.dev/latest/api/types/#pydantic.types.SecretStr
    OPENAI_API_KEY: SecretStr = Field(
        ...,
        validation_alias="OPENAI_API_KEY",
        description="Your OpenAI API key (required for status polling, file retrieval etc.)",
    )
    OPENAI_API_TIMEOUT: float = Field(
        default=10.0,
        description="Timeout for OpenAI API requests in seconds, default is 10 minutes on OpenAI side",
    )
    OPENAI_ORG_ID: str | None = Field(
        default=None,
        description="OpenAI Organization ID (if using organization-specific features)",
    )
    OPENAI_PROJECT_ID: str | None = Field(
        default=None,
        description="OpenAI Project ID (if using project-specific features)",
    )
    OPENAI_WEBHOOK_SECRET: str | None = Field(
        default=None,
        description="Webhook secret to validate incoming webhook requests from OpenAI",
    )
    OPENAI_MODE: OpenAIMode = Field(
        default=OpenAIMode.SYNC,
        description="Mode for OpenAI client: 'sync' for synchronous, 'async' for asynchronous",
    )

    # Model configuration for pydantic-settings
    # This allows loading from a .env file (e.g., for local development)
    # Ensure a .env file is present or environment variables are set.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()  # Cache the settings object for performance
def get_settings() -> Settings:
    """
    Returns the application settings instance.

    The settings are cached using lru_cache to avoid reloading them multiple times.
    """
    logger.info("Loading application settings...")
    try:
        settings = Settings()
        return settings
    except Exception as e:
        logger.exception(f"Error loading settings: {e}")
        raise


# For gloabal access within the application
settings: Settings = get_settings()

if __name__ == "__main__":
    try:
        current_settings = get_settings()
        print("Successfully loaded settings:")
        print(f"  Project Name: {current_settings.PROJECT_NAME}")
        print(f"  OpenAI API Key: {current_settings.OPENAI_API_KEY}")
        print(f"  Log Level: {current_settings.LOG_LEVEL}")
    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
