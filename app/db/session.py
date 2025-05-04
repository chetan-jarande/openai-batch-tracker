from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import logging
import time

from app.core.config import settings # Import settings from config.py

logger = logging.getLogger(__name__)

# Create the SQLAlchemy engine using the database URL from settings
# pool_pre_ping=True checks connection validity before use
# connect_args can be used for specific driver options if needed
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    # connect_args={"check_same_thread": False} # Needed only for SQLite
)

# Create a configured "Session" class
# autocommit=False ensures transactions are handled explicitly
# autoflush=False prevents premature flushes, usually desired
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our ORM models
Base = declarative_base()

def get_db():
    """
    Dependency function to get a database session.

    Yields a SQLAlchemy session for use in API endpoints.
    Ensures the session is always closed, rolling back on exceptions.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback() # Rollback in case of errors
        raise
    finally:
        db.close() # Always close the session

def init_db():
    """
    Initializes the database by creating tables defined in models.

    Should be called once at application startup.
    Includes a retry mechanism for database availability during startup.
    """
    max_retries = 5
    retry_delay = 5 # seconds
    for attempt in range(max_retries):
        try:
            logger.info("Attempting to connect to the database...")
            # Try connecting to the database
            with engine.connect() as connection:
                logger.info("Database connection successful.")
            # Create all tables defined that inherit from Base
            logger.info("Creating database tables...")
            # Import models here to ensure they are registered with Base
            from . import models # noqa - required to register models
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully (if they didn't exist).")
            return # Exit if successful
        except OperationalError as e:
            logger.warning(f"Database connection failed (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Could not connect to the database after multiple retries.")
                raise
        except Exception as e:
            logger.exception("An unexpected error occurred during database initialization.")
            raise

# Example usage (optional, for testing connection):
# if __name__ == "__main__":
#     from app.core.logging_config import setup_logging
#     setup_logging()
#     try:
#         # Test database connection
#         with engine.connect() as connection:
#             print("Successfully connected to the database.")
#         # Initialize DB (creates tables if they don't exist)
#         init_db()
#     except Exception as e:
#         print(f"Database connection or initialization failed: {e}")

