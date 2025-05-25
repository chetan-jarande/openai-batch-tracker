import logging
import sys

from app.core.config import get_settings

def setup_logging() -> None:
    """
    Configures the application's logging.

    Uses settings from the application configuration (e.g., LOG_LEVEL, LOG_FORMAT).
    This setup ensures consistent logging throughout the application.
    """
    settings = get_settings()

    # Get the root logger
    root_logger = logging.getLogger()

    # Set the overall logging level for the root logger
    # This acts as a filter; handlers can have their own levels but not higher than this.
    try:
        log_level_int = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        root_logger.setLevel(log_level_int)
    except AttributeError:
        root_logger.setLevel(logging.INFO)
        logging.warning(f"Invalid LOG_LEVEL '{settings.LOG_LEVEL}'. Defaulting to INFO.")

    # Remove any existing handlers to avoid duplicate logs if this function is called multiple times
    # or if other libraries (like Uvicorn) have already configured the root logger.
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]: # Iterate over a copy
            root_logger.removeHandler(handler)
            handler.close() # Close the handler to release resources

    # Create a stream handler to output logs to stdout (or stderr)
    stream_handler = logging.StreamHandler(sys.stdout) # Or sys.stderr for errors

    # Set the logging level for this specific handler
    stream_handler.setLevel(log_level_int)

    # Create a formatter and set it for the handler
    formatter = logging.Formatter(settings.LOG_FORMAT)
    stream_handler.setFormatter(formatter)

    # Add the handler to the root logger
    root_logger.addHandler(stream_handler)

    # Configure logging for specific libraries if needed (e.g., reduce verbosity)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING) # Quieten Uvicorn access logs if too noisy
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO) # Or WARNING to reduce SQLAlchemy engine logs

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {settings.LOG_LEVEL}, format: '{settings.LOG_FORMAT}'")

if __name__ == "__main__":
    # This block allows testing the logging configuration independently.
    # To run: python -m app.core.logging_config
    # (Ensure .env is set up or environment variables are available for get_settings())

    # First, call setup_logging to apply our configuration
    setup_logging()
    # # TODO:
    # Add the file roatation handler to log to a file
        # File should be rotated daily and keep 7 days of logs
    # set log format: text_format = "%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d (%(request_id)s) - %(message)s"

    # Get a logger instance for this test module
    test_logger = logging.getLogger("test_logging_config")

    # Log messages at different levels to verify
    test_logger.debug("This is a debug message (should not appear if LOG_LEVEL is INFO or higher).")
    test_logger.info("This is an info message.")
    test_logger.warning("This is a warning message.")
    test_logger.error("This is an error message.")
    test_logger.critical("This is a critical message.")

    try:
        1 / 0
    except ZeroDivisionError:
        test_logger.exception("An exception occurred (exception info will be logged).")

    print("Logging test complete. Check the console output.")

