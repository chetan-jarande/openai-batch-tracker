import logging
from typing import Generator, Optional

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from app.db.base_class import Base
from app.core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()

# Global variables for the engine and sessionmaker
# They will be initialized by functions called at application startup.
engine: Optional[Engine] = None
SessionLocal: Optional[sessionmaker[SQLAlchemySession]] = None


def initialize_db_engine_and_sessionmaker() -> Engine:
    """
    Creates the SQLAlchemy engine (connection pool) and the SessionLocal factory.
    This function should be called once at application startup.
    """
    global engine, SessionLocal  # Declare that we are modifying the global variables

    if engine is not None:
        logger.warning(
            "Database engine is already initialized. Skipping re-initialization."
        )
        return engine

    logger.info("Initializing database engine and SessionLocal...")
    try:
        # Create the SQLAlchemy engine
        # The pool_pre_ping argument helps in handling connections that might have been
        # closed by the database server.
        current_engine = create_engine(
            settings.sqlalchemy_database_url,
            pool_pre_ping=True, # checks connection validity before use
            # echo=True,  # Uncomment for debugging SQL queries
            # connect_args={"check_same_thread": False} # Only for SQLite
        )
        logger.info(
            f"Database engine created for URL: {settings.sqlalchemy_database_url.replace(settings.POSTGRES_PASSWORD, '****') if settings.POSTGRES_PASSWORD else settings.sqlalchemy_database_url}"
        )

        # Assign to global variable
        engine = current_engine

        # Create SessionLocal factory, now that 'engine' is initialized
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("SessionLocal factory configured.")

        return engine
    except Exception as e:
        logger.exception(f"Failed to initialize database engine or SessionLocal: {e}")
        raise


def create_db_tables(db_engine: Engine):
    """
    Creates database tables if they don't already exist.
    Requires SQLAlchemy Base to be imported where models are defined.
    This function should be called once at application startup, after the engine is initialized.

    Args:
        db_engine: The SQLAlchemy engine instance to bind for table creation.
    """
    logger.info("Attempting to create database tables if they don't exist...")
    if not db_engine:
        logger.error("Database engine is not initialized. Cannot create tables.")
        raise RuntimeError(
            "Database engine must be initialized before creating tables."
        )
    try:
        Base.metadata.create_all(bind=db_engine)
        logger.info("Database tables checked/created successfully.")
    except Exception as e:
        logger.exception(f"Error creating database tables: {e}")
        raise e


def get_db() -> Generator[SQLAlchemySession, None, None]:
    """
    Dependency to get a database session.
    Uses the globally initialized SessionLocal factory.
    """
    global SessionLocal  # Access the global SessionLocal

    if SessionLocal is None:
        logger.critical(
            "SessionLocal is not initialized. Database might not be set up correctly."
        )
        # This indicates a programming error or a failed startup.
        raise RuntimeError(
            "SessionLocal has not been initialized. Call initialize_db_engine_and_sessionmaker() first."
        )

    db: Optional[SQLAlchemySession] = None
    try:
        db = SessionLocal()  # Create a new session from the factory
        logger.debug(f"Database session {id(db)} opened for request.")
        yield db
    except Exception as e:
        logger.exception(
            f"Exception during database session {id(db) if db else 'N/A'}: {e}\nrolling back..."
        )
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()
            logger.debug(f"Database session {id(db)} closed.")


def close_db_engine():
    """
    Disposes of the SQLAlchemy engine's connection pool.
    This should be called once at application shutdown.
    """
    global engine  # Access the global engine

    logger.info("Attempting to close database engine (dispose connection pool)...")
    if engine:
        try:
            engine.dispose()
            logger.info("Database engine's connection pool disposed successfully.")
            engine = None  # Clear the global engine variable
        except Exception as e:
            logger.exception(f"Error disposing database engine: {e}")
    else:
        logger.warning(
            "Database engine was not initialized or already disposed. No action taken."
        )


def check_db_connection() -> bool:
    """
    Checks if a connection to the database can be established using the global engine.
    """
    global engine
    if not engine:
        logger.warning("Cannot check DB connection: Engine not initialized.")
        return False
    try:
        with engine.connect() as connection:  # type: ignore
            logger.info("Successfully connected to the database via global engine.")
            return True
    except Exception as e:
        logger.error(f"Failed to connect to the database via global engine: {e}")
        return False


# if __name__ == "__main__":
#     # This block allows testing the database session and engine lifecycle.
#     # To run: python -m app.db.session
#     logging.basicConfig(level=logging.INFO) # Ensure logger is configured for direct run
#     print("Testing database session module...")

#     local_engine: Optional[Engine] = None
#     try:
#         print("\n1. Initializing engine and SessionLocal...")
#         local_engine = initialize_db_engine_and_sessionmaker()
#         assert local_engine is not None, "Engine initialization failed"
#         assert SessionLocal is not None, "SessionLocal initialization failed"
#         print("Engine and SessionLocal initialized.")

#         print("\n2. Checking DB connection...")
#         if check_db_connection():
#             print("DB connection successful.")

#             print("\n3. Creating tables (if not exist)...")
#             # For this test, ensure your models are loaded by importing Base correctly
#             create_db_tables(local_engine) # Pass the initialized engine
#             print("Tables checked/created.")

#             print("\n4. Getting a DB session...")
#             db_gen = get_db()
#             try:
#                 session = next(db_gen)
#                 print(f"Session obtained: {type(session)}")
#                 # Perform a simple query if desired, e.g., session.execute(text("SELECT 1"))
#                 print("Session usage example successful.")
#             except Exception as e:
#                 print(f"Error using session: {e}")
#             finally:
#                 # Ensure the generator's finally block is called
#                 try:
#                     next(db_gen, None)
#                 except Exception: pass # Ignore errors during this test cleanup
#                 print("Session context exited.")
#         else:
#             print("DB connection failed. Further tests might not be meaningful.")

#     except Exception as e:
#         print(f"An error occurred during the test: {e}")
#     finally:
#         print("\n5. Closing DB engine...")
#         close_db_engine() # This will dispose the global 'engine'
#         print("DB engine closure attempted.")
#         # Verify engine is None after closure
#         # print(f"Global engine after close_db_engine: {engine}")

#     print("\nDatabase session module test complete.")
