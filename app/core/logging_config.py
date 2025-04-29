import logging
import sys
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
from config import settings

def setup_logging():
    """
    Configures logging for the application.

    Sets up console logging and rotating file logging based on settings.
    Logs will rotate daily, keeping backups.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Ensure the log directory exists
    log_dir = Path(settings.LOG_FILE_PATH).parent
    log_dir.mkdir(parents=True, exist_ok=True) # Create directory if it doesn't exist

    # Define log format
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level) # Set root logger level

    # --- Console Handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    # Avoid adding handler if already present (e.g., during reloads)
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
         root_logger.addHandler(console_handler)

    # --- Timed Rotating File Handler ---
    # Rotates logs daily ('D'), keeps 7 backups
    file_handler = TimedRotatingFileHandler(
        settings.LOG_FILE_PATH,
        when="D",          # Rotate daily
        interval=1,        # Interval based on 'when' (1 day)
        backupCount=7,     # Keep 7 old log files
        encoding='utf-8',
        delay=False
    )
    file_handler.setFormatter(log_formatter)
    # Avoid adding handler if already present
    if not any(isinstance(h, TimedRotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(file_handler)

    # Configure specific loggers if needed (e.g., uvicorn, sqlalchemy)
    # logging.getLogger("uvicorn.error").propagate = False # Prevent duplicate logs from uvicorn
    # logging.getLogger("uvicorn.access").propagate = False
    # You might want to adjust SQLAlchemy logging level separately
    # logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO) # Example: Log SQL queries

    logging.info("Logging configured successfully.")

# Example usage (optional, for testing):
# if __name__ == "__main__":
#     setup_logging()
#     logging.info("This is an info message.")
#     logging.warning("This is a warning message.")
#     logging.error("This is an error message.")
#     try:
#         1 / 0
#     except ZeroDivisionError:
#         logging.exception("Caught an exception.")
