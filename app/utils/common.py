from datetime import datetime, timezone
from pathlib import Path

from app.utils.logging_config import get_logger


logger = get_logger(__name__)


def find_project_root(marker: str = "pyproject.toml") -> Path:
    """
    Finds the project root directory by searching upwards for a marker file.
    This is a robust way to locate the project root, regardless of the current
    file's location or the execution context.

    Args:
        marker: The file or directory name that identifies the project root.

    Returns:
        The Path object for the project root directory.

    Raises:
        FileNotFoundError: If the project root cannot be determined.
    """
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / marker).exists():
            logger.debug(f"Found project root at: {parent}")
            return parent
    raise FileNotFoundError(f"Project root marker '{marker}' not found.")


def format_unix_timestamp(value: int, format_str: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    if value is None:
        return "N/A"
    try:
        dt_object = datetime.fromtimestamp(value, tz=timezone.utc)
        return dt_object.strftime(format_str)
    except (TypeError, ValueError) as e:
        logger.error(f"Error formatting timestamp {value}: {e}")
        return f"Invalid Timestamp: {value}: {str(e)}"
