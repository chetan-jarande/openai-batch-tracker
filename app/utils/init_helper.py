import logging
import os
from typing import Optional
from functools import lru_cache
from openai import OpenAI, AsyncOpenAI
from fastapi import HTTPException, status
from app.core.logging_config import setup_logging
from app.core.config import get_settings, Settings


logger = logging.getLogger(__name__)

_openai_client_instance: Optional[OpenAI] = None


def get_global_openai_client() -> OpenAI:
    if _openai_client_instance is None:
        logger.error("Global OpenAI client accessed before initialization!")
        raise RuntimeError("OpenAI client has not been initialized.")
    return _openai_client_instance


@lru_cache()
def get_openai_client() -> OpenAI:
    """
    Dependency that provides an initialized OpenAI client.
    It uses the API key from the application settings.
    """
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI API key is not configured. Please set the OPENAI_API_KEY environment variable.",
        )
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # You could add a simple test call here if needed, e.g., client.models.list()
        # but it might slow down requests. Best to rely on OpenAI's exceptions.
        logger.info("OpenAI client initialized successfully.")
        return client
    except Exception as e:
        logger.exception(f"Failed to initialize OpenAI client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not initialize OpenAI client: {str(e)}",
        )


def initialize_openai():
    global _openai_client_instance
    settings = get_settings()
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if api_key is None or api_key == "":
        logger.error(
            "OPENAI_API_KEY is not configured for OpenAI client initialization."
        )
        raise ValueError("OPENAI_API_KEY is required but not set for OpenAI client.")
    _openai_client_instance = OpenAI(api_key=settings.OPENAI_API_KEY)
    logger.info("Global OpenAI client instance initialized.")


def run_startup_logic():
    """
    Orchestrates all startup tasks.
    """
    logger.info("Executing application startup logic...")
    try:
        # Initialize logging
        setup_logging()
        # Load application settings
        settings: Settings = get_settings()
        logger.info(
            f"Application settings loaded successfully for project: {settings.PROJECT_NAME}"
        )
        # Initialize the OpenAI API client
        initialize_openai()
        logger.info("OpenAI client initialized successfully.")
        # Any other startup tasks can be added here

        logger.info("All startup tasks completed.")
    except Exception as e:
        logger.critical(
            f"CRITICAL: Failed to execute application startup logic. Application cannot start. Error: {e}",
            exc_info=True,
        )
        raise e


def run_shutdown_logic():
    """
    Orchestrates all shutdown tasks.
    """
    logger.info("Executing application shutdown logic...")
    # Add any shutdown tasks here
    logger.info("All shutdown tasks completed.")
