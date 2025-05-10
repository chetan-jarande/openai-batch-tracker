import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Create the SQLAlchemy engine
# The pool_pre_ping argument helps in handling connections that might have been
# closed by the database server.
# pool_pre_ping=True checks connection validity before use
# connect_args can be used for specific driver options if needed
try:
    engine = create_engine(
        settings.sqlalchemy_database_url,
        pool_pre_ping=True,
        # echo=True,  # Uncomment for debugging SQL queries
        # connect_args={"check_same_thread": False}, # Needed only for SQLite
    )
    logger.info(f"Database engine created for URL: {settings.sqlalchemy_database_url.replace(settings.POSTGRES_PASSWORD, '****') if settings.POSTGRES_PASSWORD else settings.sqlalchemy_database_url}")
except Exception as e:
    logger.exception(f"Failed to create database engine: {e}")
    # Depending on the application's needs, you might want to exit or handle this critical failure.
    raise

# Create a configured "SessionLocal" class
# This class will then be used to create individual database sessions.
# - autocommit=False: Changes are not committed automatically. You need to call session.commit().
# - autoflush=False: Changes are not flushed to the DB automatically before queries.
#                    This can be useful to manage the state of objects more explicitly.
# - bind=engine: Associates this session configuration with our database engine.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[SQLAlchemySession, None, None]:
    """
    Dependency to get a database session.

    This function is a generator that yields a database session.
    It ensures that the session is always closed after the request is finished,
    even if an error occurs.

    Usage:
        @app.get("/")
        def read_root(db: SQLAlchemySession = Depends(get_db)):
            # use db session here
            ...
    """
    db: Optional[SQLAlchemySession] = None
    try:
        db = SessionLocal()
        logger.debug(f"Database session {id(db)} opened.")
        yield db
    except Exception as e:
        logger.exception(f"Exception during database session {id(db) if db else 'N/A'}: {e}")
        if db:
            db.rollback() # Rollback in case of error
        raise # Re-raise the exception to be handled by FastAPI error handlers
    finally:
        if db:
            db.close()
            logger.debug(f"Database session {id(db)} closed.")



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


# Optional: Function to test database connection
def check_db_connection():
    """
    Checks if a connection to the database can be established.
    """
    try:
        with engine.connect() as connection:
            logger.info("Successfully connected to the database.")
            return True
    except Exception as e:
        logger.error(f"Failed to connect to the database: {e}")
        logger.error(f"Database URL used: {settings.sqlalchemy_database_url.replace(settings.POSTGRES_PASSWORD, '****') if settings.POSTGRES_PASSWORD else settings.sqlalchemy_database_url}")
        return False

if __name__ == "__main__":
    # This block allows testing the database connection independently.
    # To run: python -m app.db.session
    # (Ensure .env is set up or environment variables are available)
    print("Checking database connection...")
    if check_db_connection():
        print("Database connection successful.")
        # Example of using a session
        print("Attempting to create a session...")
        db_gen = get_db()
        try:
            session = next(db_gen)
            print(f"Session created: {session}")
            # You could perform a simple query here if models were defined and tables created
            # e.g., session.execute(text("SELECT 1")).scalar_one()
            print("Session usage example successful.")
        except StopIteration:
            print("Could not get DB session from generator.")
        except Exception as e:
            print(f"Error during session test: {e}")
        finally:
            if 'session' in locals() and session:
                try:
                    next(db_gen, None) # To trigger the finally block in get_db
                except Exception:
                    pass # Ignore errors during cleanup for this test
    else:
        print("Database connection failed. Please check your configuration and database server.")

