import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="[%(asctime)s] %(levelname)s <%(module)s:%(funcName)s:%(lineno)d> %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    return logger


if __name__ == "__main__":
    # This block allows testing the logging configuration independently.
    # To run: python -m app.utils.logging_config
    # (Ensure .env is set up or environment variables are available for get_settings())

    # # TODO:
    # Add the file roatation handler to log to a file
    # File should be rotated daily and keep 7 days of logs
    # set log format: text_format = "%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d (%(request_id)s) - %(message)s"

    # Get a logger instance for this test module
    test_logger = get_logger(__name__)

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
