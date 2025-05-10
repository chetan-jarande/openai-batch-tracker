import logging
from typing import Generator, Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError

from app.core.config import get_settings, Settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Dependency to get database session
def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a SQLAlchemy database session.
    Ensures the session is closed after the request.
    """
    db: Session = SessionLocal()
    try:
        logger.debug(f"Database session {id(db)} opened for request.")
        yield db
    except Exception as e:
        logger.exception(f"Exception in database session {id(db)} during request: {e}")
        db.rollback() # Rollback in case of an unhandled exception within the request cycle using this session
        raise
    finally:
        logger.debug(f"Database session {id(db)} closed after request.")
        db.close()

# Dependency to get application settings
def get_app_settings() -> Settings:
    """
    Dependency that provides the application settings object.
    """
    return get_settings()

# Type alias for dependencies to improve readability in endpoint signatures
DBSession = Annotated[Session, Depends(get_db)]
CurrentSettings = Annotated[Settings, Depends(get_app_settings)]


# Dependency to get OpenAI client
def get_openai_client(settings: CurrentSettings) -> OpenAI:
    """
    Dependency that provides an initialized OpenAI client.
    It uses the API key from the application settings.
    """
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

# Type alias for OpenAI client dependency
OpenAIClient = Annotated[OpenAI, Depends(get_openai_client)]



# # ----------------------***** Testing *****---------------------- #
if __name__ == "__main__":
    # This block is for illustrative purposes and won't run in the app context.
    # It demonstrates how these dependencies might be used or tested conceptually.
    logger.info("Testing dependency functions (conceptual)...")

    # Test get_db (requires database to be running and configured)
    # print("\n--- Testing get_db ---")
    # db_gen = get_db()
    # try:
    #     db_session = next(db_gen)
    #     print(f"Successfully obtained DB session: {type(db_session)}")
    #     # In a real scenario, you would use the session here
    #     # e.g., db_session.query(...)
    # except Exception as e:
    #     print(f"Error obtaining DB session: {e}")
    # finally:
    #     try:
    #         next(db_gen, None) # Ensure finally block in get_db is called
    #         print("DB session context manager exited.")
    #     except Exception as e:
    #         print(f"Error during DB session cleanup: {e}")


    # Test get_app_settings (requires .env or environment variables)
    print("\n--- Testing get_app_settings ---")
    try:
        current_settings = get_app_settings()
        print(f"Successfully obtained app settings. Project: {current_settings.PROJECT_NAME}")
        print(f"OpenAI API Key (masked): {'SET' if current_settings.OPENAI_API_KEY else 'NOT SET'}")
    except Exception as e:
        print(f"Error obtaining app settings: {e}")

    # Test get_openai_client (requires OPENAI_API_KEY in settings)
    # print("\n--- Testing get_openai_client ---")
    # try:
    #     # Simulate settings for testing; in app, it comes from get_app_settings
    #     class MockSettings:
    #         OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_FOR_TEST") # Use a test key if available
    #
    #     if MockSettings.OPENAI_API_KEY:
    #         mock_settings_instance = MockSettings()
    #         openai_client_instance = get_openai_client(mock_settings_instance)
    #         print(f"Successfully obtained OpenAI client: {type(openai_client_instance)}")
    #         # Example: List models (be mindful of API calls)
    #         # models = openai_client_instance.models.list()
    #         # print(f"Found {len(models.data)} models.")
    #     else:
    #         print("Skipping OpenAI client test: OPENAI_API_KEY_FOR_TEST not set.")
    #
    # except HTTPException as he:
    #     print(f"HTTPException from get_openai_client: {he.detail} (Status: {he.status_code})")
    # except Exception as e:
    #     print(f"Error obtaining OpenAI client: {e}")

    logger.info("Dependency functions conceptual test complete.")

