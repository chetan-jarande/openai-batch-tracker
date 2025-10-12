from typing import Optional
from openai import OpenAI, AsyncOpenAI
from app.core.config import settings, OpenAIMode
from app.core.logging_config import get_logger


logger = get_logger(__name__)

_openai_client_instance: Optional[OpenAI] = None
_async_openai_client_instance: Optional[AsyncOpenAI] = None


def initialize_openai_client(mode: OpenAIMode = "sync"):
    """ "Initializes the global OpenAI client instance.
    Args:
        mode (str): "sync" for synchronous client, "async" for asynchronous client.
    """
    global _openai_client_instance, _async_openai_client_instance
    _api_key = settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else None

    if not _api_key:
        logger.error("OPENAI_API_KEY is not configured for OpenAI client initialization.")
        raise ValueError("OPENAI_API_KEY is required but not set for OpenAI client.")

    match mode:
        case OpenAIMode.ASYNC:
            _async_openai_client_instance = AsyncOpenAI(
                api_key=_api_key,
                organization=settings.OPENAI_ORG_ID,
                timeout=settings.OPENAI_API_TIMEOUT,
                project=settings.OPENAI_PROJECT_ID,
                webhook_secret=settings.OPENAI_WEBHOOK_SECRET,
            )
        case OpenAIMode.SYNC:
            _openai_client_instance = OpenAI(
                api_key=_api_key,
                organization=settings.OPENAI_ORG_ID,
                timeout=settings.OPENAI_API_TIMEOUT,
                project=settings.OPENAI_PROJECT_ID,
                webhook_secret=settings.OPENAI_WEBHOOK_SECRET,
            )

    logger.info(f"Global {mode.capitalize()} OpenAI client instance initialized successfully.")


def get_openai_client(mode: OpenAIMode) -> OpenAI | AsyncOpenAI:
    """
    Returns the global OpenAI client instance based on the specified OpenAIMode('sync', 'async').
    If the client is not initialized, it initializes it first."""
    match mode:
        case OpenAIMode.ASYNC:
            if _async_openai_client_instance is None:
                initialize_openai_client(mode)
            return _async_openai_client_instance

        case OpenAIMode.SYNC:
            if _openai_client_instance is None:
                initialize_openai_client(mode)
            return _openai_client_instance
        case _:
            raise ValueError(f"Invalid OpenAI mode specified: {mode}. Use 'sync' or 'async'.")


def run_startup_logic():
    """
    Orchestrates all startup tasks.
    """
    logger.info("Executing application startup logic...")
    try:
        # Initialize the OpenAI API client
        initialize_openai_client(settings.OPENAI_MODE)
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
