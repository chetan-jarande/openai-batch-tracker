import os
import logging
from pydantic_settings import BaseSettings
# Assuming pydantic[postgres] is installed for PostgresDsn
from pydantic import PostgresDsn, field_validator, Field, AnyUrl, SecretStr
from dotenv import load_dotenv
from functools import lru_cache
from pathlib import Path
from typing import Optional # Import Optional

# Load environment variables from a .env file if it exists
# Useful for local development
load_dotenv()

# --- Nested Database Settings ---
class DatabaseSettings(BaseSettings):
    """Configuration specific to the database connection."""
    # Use PostgresDsn for built-in validation of the connection string.
    # The default value is provided as a string, which Pydantic validates
    # at runtime if the environment variable is not set.
    # Static type checkers (like Pylance) might flag the default string
    # as incompatible with PostgresDsn, but this is expected and handled
    # correctly by Pydantic during settings initialization.
    URL: PostgresDsn = Field(  # type: ignore[assignment]
        default="postgresql://user:password@db:5432/batch_tracker_db",
        validation_alias="DATABASE_URL", # Read from DATABASE_URL env var
        description="The connection string for the PostgreSQL database."
    )
    ECHO_SQL: bool = Field(default=False, validation_alias="DATABASE_ECHO_SQL") # Example: control SQL echoing

    # Add validator inspired by Pydantic docs to ensure DB name is present
    @field_validator('URL')
    @classmethod
    def check_db_name(cls, v: AnyUrl | None) -> AnyUrl | None:
        """Ensures the database name path component is present in the DSN."""
        # The input 'v' is already validated as PostgresDsn format by Pydantic
        # before this validator runs (if it's a valid DSN structure).
        # We check the 'path' attribute which holds the database name part.
        if v and (not v.path or len(v.path) <= 1): # Check if path is None, empty or just '/'
             raise ValueError('Database name must be provided in the DATABASE_URL path (e.g., postgresql://.../my_database)')
        return v

    class Config:
        case_sensitive = False
        # Ensure .env file is loaded if specified (pydantic-settings v2 behavior)
        # env_file = '.env' # Uncomment if needed explicitly


class Settings(BaseSettings):
    """Main application configuration settings."""
    # Nested database configuration
    database: DatabaseSettings = DatabaseSettings()

    # Application Metadata
    PROJECT_NAME: str = "OpenAI Batch Job Tracker"
    API_V1_STR: str = "/api/v1"

    # OpenAI Configuration
    # Use SecretStr to prevent accidental exposure of the API key.
    # Mark as Optional for now, but required for features interacting with OpenAI API.
    OPENAI_API_KEY: Optional[SecretStr] = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
        description="Your OpenAI API key (required for status polling, file retrieval etc.)"
        )

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    # Log file path (can be relative to the execution directory or absolute)
    LOG_FILE_PATH: str = Field(default="logs/app.log", validation_alias="LOG_FILE_PATH")

    # Validator for LOG_LEVEL
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Validates and standardizes the log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        level = value.upper()
        if level not in valid_levels:
            raise ValueError(f"Invalid LOG_LEVEL: '{value}'. Must be one of {valid_levels}")
        return level

    class Config:
        # Makes BaseSettings case-insensitive for environment variables
        case_sensitive = False
        # Specifies the .env file name if you want to use a specific one
        # env_file = ".env"
        # Allow population by field name in addition to alias
        populate_by_name = True


@lru_cache() # Cache the settings object for performance
def get_settings() -> Settings:
    """
    Returns the application settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    # This will raise a validation error during startup if required settings
    # (like DATABASE_URL) are invalid or missing the database name part.
    return Settings()

# Instantiate settings for easy import elsewhere
settings = get_settings()


# Example usage (optional, for testing):
# if __name__ == "__main__":
#     try:
#         # Accessing settings here will trigger validation
#         print(f"Project Name: {settings.PROJECT_NAME}")
#         print(f"Database URL: {settings.database.URL}")
#         print(f"Database Echo SQL: {settings.database.ECHO_SQL}")
#         print(f"Log Level: {settings.LOG_LEVEL}")
#         print(f"Log File Path (Config): {settings.LOG_FILE_PATH}")
#         # Accessing the secret value requires .get_secret_value()
#         if settings.OPENAI_API_KEY:
#              print(f"OpenAI Key Loaded: Yes (Value hidden)")
#              # print(f"Actual Key (DO NOT DO THIS IN REAL CODE): {settings.OPENAI_API_KEY.get_secret_value()}")
#         else:
#              print("OpenAI Key Loaded: No")
#     except Exception as e:
#         print(f"Error loading settings: {e}")

