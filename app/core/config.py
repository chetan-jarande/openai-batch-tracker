import os
import logging
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
# from pydantic import PostgresDsn, field_validator, Field, AnyUrl, SecretStr

# Configure logging for early setup issues
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Application settings.

    Uses pydantic-settings to load from environment variables and .env files.
    """
    PROJECT_NAME: str = "OpenAI Batch Tracker"
    API_V1_STR: str = "/api/v1"

    # OpenAI API Key
    OPENAI_API_KEY: str
    # # another way
    # OpenAI Configuration
    # Use SecretStr to prevent accidental exposure of the API key.
    # Mark as Optional for now, but required for features interacting with OpenAI API.
    # OPENAI_API_KEY: Optional[SecretStr] = Field(
    #     default=None,
    #     validation_alias="OPENAI_API_KEY",
    #     description="Your OpenAI API key (required for status polling, file retrieval etc.)"
    #     )

    # Database configuration
    # # Refer the old version from main branch for the PostgresDsn validator and loading the DB config from .env
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    # # TODO: Add the DB validator to ensure the URL is valid
    DATABASE_URL: Optional[str] = None

    # Uvicorn server settings (if running directly, Docker Compose handles this)
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Batch processing settings
    OPENAI_BATCH_API_VERSION: str = "v1" # As per OpenAI docs for batch

    # Model configuration for pydantic-settings
    # This allows loading from a .env file (e.g., for local development)
    # Ensure a .env file is present or environment variables are set.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

    @property
    def sqlalchemy_database_url(self) -> str:
        """
        Constructs the SQLAlchemy database URL from individual components.
        If DATABASE_URL is set directly, it will be used.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

@lru_cache() # Cache the settings object for performance
def get_settings() -> Settings:
    """
    Returns the application settings instance.

    The settings are cached using lru_cache to avoid reloading them multiple times.
    """
    logger.info("Loading application settings...")
    try:
        settings = Settings()
        # Log a portion of the loaded settings for verification (be careful with sensitive data)
        logger.info(f"Settings loaded for project: {settings.PROJECT_NAME}")
        logger.debug(f"Database URL constructed: {settings.sqlalchemy_database_url}") # For debugging
        if not settings.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY is not set in the environment variables or .env file.")
            raise ValueError("OPENAI_API_KEY is required but not set.")
        return settings
    except Exception as e:
        logger.exception(f"Error loading settings: {e}")
        # Re-raise the exception if settings are critical for app startup
        raise

# Initialize settings globally for easy access if needed, though dependency injection is preferred.
settings = get_settings() # Uncomment if global access is frequently needed, but prefer get_settings() via DI.

if __name__ == "__main__":
    # Example of how to use the settings
    # This block will only run when the script is executed directly (e.g., python app/core/config.py)
    try:
        current_settings = get_settings()
        print("Successfully loaded settings:")
        print(f"  Project Name: {current_settings.PROJECT_NAME}")
        print(f"  API V1 Prefix: {current_settings.API_V1_STR}")
        print(f"  OpenAI API Key: {'*' * (len(current_settings.OPENAI_API_KEY) - 4) + current_settings.OPENAI_API_KEY[-4:] if current_settings.OPENAI_API_KEY else 'Not Set'}")
        print(f"  Database URL: {current_settings.sqlalchemy_database_url}")
        print(f"  Log Level: {current_settings.LOG_LEVEL}")
    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

