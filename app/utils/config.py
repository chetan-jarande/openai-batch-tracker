from enum import StrEnum
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class Environments(StrEnum):
    DEV = "dev"
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
    CONF_ENV: Environments = Field(
        default=Environments.DEV,
        description="Configuration environment",
    )
    PORTFOLIO_URL: str = Field(
        default="https://your-portfolio-url.com",
        description="Portfolio URL to be displayed on the homepage",
    )

    # Uvicorn server settings (if running from docker, Docker Compose handles this)
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = Field(
        default=8000,
        description="Port for the FastAPI server",
    )

    # # MCP settings
    FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER: bool = Field(
        default=True,
        description="Enable the new OpenAPI parser in FastMCP, Doc: https://gofastmcp.com/integrations/fastapi",
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

    # Redis settings for session management in production
    REDIS_HOST: str = Field(
        default="redis",
        description="Redis host for session storage",
    )
    REDIS_PORT: int = Field(
        default=6379,
        description="Redis port for session storage",
    )
    REDIS_DB: int = Field(
        default=0,
        description="Redis database for session storage",
    )
    REDIS_USERNAME: str | None = None
    REDIS_PASSWORD: str | None = None
    REDIS_TLS: bool = False

    @property
    def REDIS_URL(self) -> str:
        auth = ""
        if self.REDIS_PASSWORD:
            if self.REDIS_USERNAME:
                auth = f"{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}@"
            else:
                auth = f":{self.REDIS_PASSWORD}@"
        scheme = "rediss" if self.REDIS_TLS else "redis"
        return f"{scheme}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

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

MCP_SERVER_URL = f"http://localhost:{settings.SERVER_PORT}/mcp"

REDIS_URL = settings.REDIS_URL


if __name__ == "__main__":
    try:
        current_settings = get_settings()
        logger.info("Successfully loaded settings:")
        logger.info(f"  Project Name: {current_settings.PROJECT_NAME}")
        # Log only a part of the key to avoid exposing secrets
        api_key_display = (
            f"{current_settings.OPENAI_API_KEY.get_secret_value()[:4]}..."
            if current_settings.OPENAI_API_KEY
            else "Not set"
        )
        logger.info(f"  OpenAI API Key: {api_key_display}")
    except ValueError as ve:
        logger.error(f"Configuration Error: {ve}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
