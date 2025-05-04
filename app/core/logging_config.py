import logging
import logging.handlers # Import handlers
from pathlib import Path
import os
import sys

# Import settings and the RequestIdFilter
from .config import settings
# Assuming RequestIdFilter is defined in middleware.py
from .middleware import RequestIdFilter

# Flag to prevent setup from running multiple times in some scenarios (like Uvicorn reload)
_logging_configured = False

def setup_logging():
    """
    Configures logging for the application programmatically using Text format.

    Sets up console and rotating file handlers based on settings if not already configured.
    Includes RequestIdFilter for correlating logs.
    Lets library loggers inherit from the root logger by default.
    """
    global _logging_configured
    if _logging_configured:
        return # Avoid reconfiguring if already done

    try:
        # --- Determine Log Level ---
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

        # --- Ensure Log Directory Exists ---
        log_file_path_str = settings.LOG_FILE_PATH
        log_file_path = Path(log_file_path_str)
        log_dir = log_file_path.parent
        log_dir.mkdir(parents=True, exist_ok=True)
        # Initial message before full setup - use print as logging might not be ready
        print(f"[INFO] Ensured log directory exists: {log_dir.resolve()}")

        # --- Create Filter ---
        # This filter adds the 'request_id' attribute to log records
        request_id_filter = RequestIdFilter()

        # --- Create Text Formatter (with request_id) ---
        # This format string expects 'request_id' to be present on the log record
        text_format = "%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d (%(request_id)s) - %(message)s"
        text_date_format = "%Y-%m-%d %H:%M:%S"
        text_formatter = logging.Formatter(text_format, datefmt=text_date_format)

        # --- Configure Root Logger ---
        # Get the root logger instance
        root_logger = logging.getLogger()
        # Set the effective level for the root logger
        root_logger.setLevel(log_level)

        # --- Configure Console Handler ---
        # Check if a similar handler already exists to avoid duplicates
        if not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout for h in root_logger.handlers):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(text_formatter) # Use our text formatter
            console_handler.addFilter(request_id_filter) # Add filter to make request_id available
            console_handler.setLevel(log_level) # Set level for this handler
            root_logger.addHandler(console_handler)
            print("[INFO] Console logging handler configured.") # Use print before logging is fully set

        # --- Configure Timed Rotating File Handler ---
        # Check if a similar handler already exists
        # Note: This check might be less reliable if path normalization differs
        if not any(isinstance(h, logging.handlers.TimedRotatingFileHandler) and h.baseFilename == str(log_file_path.resolve()) for h in root_logger.handlers):
            file_handler = logging.handlers.TimedRotatingFileHandler(
                filename=log_file_path, # Use path object or string
                when="D",         # Rotate daily
                interval=1,       # Interval based on 'when' (1 day)
                backupCount=7,    # Keep 7 old log files
                encoding='utf-8',
                delay=False
            )
            file_handler.setFormatter(text_formatter) # Use our text formatter
            file_handler.addFilter(request_id_filter) # Add filter to make request_id available
            file_handler.setLevel(log_level) # Set level for this handler
            root_logger.addHandler(file_handler)
            print(f"[INFO] File logging handler configured for {log_file_path.resolve()}.") # Use print

        # --- Library Logger Behavior ---
        # Explicitly configure uvicorn loggers to use our handlers and prevent propagation
        # This ensures consistent formatting and avoids duplicates from uvicorn's defaults.
        # logging.getLogger("uvicorn").propagate = False
        # logging.getLogger("uvicorn.error").propagate = False
        # logging.getLogger("uvicorn.access").propagate = False
        # for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        #      lib_logger = logging.getLogger(logger_name)
        #      # Ensure handlers are not duplicated if setup_logging is called multiple times
        #      if not lib_logger.hasHandlers():
        #          lib_logger.setLevel(logging.INFO) # Adjust level as needed
        #          lib_logger.addHandler(console_handler)
        #          lib_logger.addHandler(file_handler)

        # --- SQLAlchemy Logger Configuration (Recommendation - Commented Out) ---
        # By default, 'sqlalchemy' logger inherits root settings.
        # For finer control (e.g., quieter logs, prevent duplicates), uncomment:
        #
        # logging.getLogger("sqlalchemy").propagate = False # Prevent passing to root
        # sqlalchemy_logger = logging.getLogger("sqlalchemy")
        # sqlalchemy_logger.setLevel(logging.WARNING) # Example: Set level to WARNING
        # # Add handlers only if they haven't been added before (e.g., by reload)
        # if not sqlalchemy_logger.hasHandlers():
        #      sqlalchemy_logger.addHandler(console_handler)
        #      sqlalchemy_logger.addHandler(file_handler)
        #

        # Use the configured logger for subsequent messages
        logger = logging.getLogger(__name__) # Get logger for this module
        logger.info("Logging configured successfully using simplified programmatic setup.")
        logger.info(f"Root logger level set to: {settings.LOG_LEVEL}")
        logger.info(f"Using log file path: {log_file_path_str} (Resolved: {log_file_path.resolve()})")

        _logging_configured = True # Mark logging as configured

    except Exception as e:
        # Fallback basic config if setup fails
        logging.basicConfig(level=logging.WARNING, force=True) # force=True overrides existing
        logging.critical(f"CRITICAL ERROR: Failed to configure logging programmatically: {e}", exc_info=True)
        logging.warning("Falling back to basic logging configuration.")

# Example usage (optional, for testing):
# if __name__ == "__main__":
#     # Must be run after settings are initialized
#     setup_logging()
#     test_logger = logging.getLogger("my_test_module")
#     test_logger.info("This is an info message.")
#     test_logger.warning("This is a warning message.")
