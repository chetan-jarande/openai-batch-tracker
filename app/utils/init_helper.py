import logging
from app.core.logging_config import setup_logging
from app.db.base_class import Base
from app.db.session import engine
from app.core.config import get_settings, Settings

logger = logging.getLogger(__name__)


def initialize_database():
    """
    Initializes the database by creating tables if they don't exist.
    This is typically for development; production should use migrations.
    """
    logger.info("Attempting to initialize database (create tables)...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables checked/created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
        # Depending on the application, this might be a critical error.
        # Consider re-raising or handling as appropriate for your application's needs.
        raise e  # Re-raise to allow lifespan manager to catch and handle


def cleanup_database_resources():
    """
    Disposes of the SQLAlchemy engine's connection pool.
    This ensures connections are gracefully closed on application shutdown.
    """
    logger.info("Performing database resource cleanup (disposing engine)...")
    if engine:
        try:
            engine.dispose()
            logger.info("SQLAlchemy engine's connection pool disposed successfully.")
        except Exception as e:
            logger.error(f"Error disposing SQLAlchemy engine: {e}", exc_info=True)
    else:
        logger.warning("SQLAlchemy engine not available for disposal.")
    logger.info("Database resource cleanup finished.")


def run_startup_logic():
    """
    Orchestrates all startup tasks.
    """
    logger.info("Executing application startup logic...")
    try:
        # 1. Initialize logging
        setup_logging()
        # 2. Load application settings
        settings: Settings = get_settings()
        logger.info(f"Application settings loaded successfully for project: {settings.PROJECT_NAME}")
        # 3. Initialize the database (create tables skip if they exist)
        initialize_database()
        # 4. TODO: Initialize the OpenAI API client

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
    cleanup_database_resources()
    logger.info("All shutdown tasks completed.")


# if __name__ == "__main__":
#     # This block is for illustrative purposes.
#     # You might add basic tests for your init/cleanup functions here.
#     logging.basicConfig(level=logging.INFO)
#     logger.info("Testing init_helper.py functions...")
#     try:
#         # Note: initialize_database() will try to connect to a DB.
#         # Ensure DB is accessible if running this directly for a real test.
#         # For a simple print test, you might comment out the actual DB operation.
#         logger.info("Simulating startup...")
#         initialize_database()
#         logger.info("Simulated startup complete.")
#     except Exception as e:
#         logger.error(f"Error during direct test of init_helper: {e}")
#     finally:
#         logger.info("Simulating shutdown...")
#         cleanup_database_resources()
#         logger.info("Simulated shutdown complete.")
