import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables from a .env file if it exists
# Useful for local development
load_dotenv()

class Settings(BaseSettings):
    """
    Application configuration settings.
    Reads environment variables, case-insensitive.
    """
    # Database Configuration
    # Example: postgresql://user:password@hostname:port/database_name
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/batch_tracker_db")

    # Application Metadata
    PROJECT_NAME: str = "OpenAI Batch Job Tracker"
    API_V1_STR: str = "/api/v1"

    # Logging Configuration
    LOG_FILE_PATH: str = os.getenv("LOG_FILE_PATH", "logs/app.log") # Path relative to project root
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        # Makes BaseSettings case-insensitive for environment variables
        case_sensitive = False
        # Specifies the .env file name if you want to use a specific one
        # env_file = ".env"


@lru_cache() # Cache the settings object for performance
def get_settings() -> Settings:
    """
    Returns the application settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()

# Instantiate settings for easy import elsewhere
settings = get_settings()

# Example usage (optional, for testing):
# if __name__ == "__main__":
#     print(f"Database URL: {settings.DATABASE_URL}")
#     print(f"Log File Path: {settings.LOG_FILE_PATH}")
