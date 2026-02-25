from functools import wraps
from typing import Callable, Any, TypeVar, Coroutine
from fastapi import HTTPException, status
from openai import APIConnectionError, RateLimitError, APIStatusError, NotFoundError as OpenAINotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def handle_openai_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to handle OpenAI API exceptions and convert them to FastAPI HTTPExceptions.
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except OpenAINotFoundError as e:
            logger.warning(f"Resource not found: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Resource not found: {e.message or str(e)}"
            )
        except (APIConnectionError, RateLimitError) as e:
            logger.error(f"OpenAI API connection/rate limit error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"OpenAI API service unavailable: {str(e)}"
            )
        except APIStatusError as e:
            logger.error(f"OpenAI API status error: {e}")
            raise HTTPException(
                status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OpenAI API error: {e.message or str(e)}",
            )
        except HTTPException:
            # Re-raise existing HTTPExceptions (e.g., from custom validation)
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}"
            )

    return wrapper


def async_handle_openai_errors(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Async Decorator to handle OpenAI API exceptions and convert them to FastAPI HTTPExceptions.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except OpenAINotFoundError as e:
            logger.warning(f"Resource not found: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Resource not found: {e.message or str(e)}"
            )
        except (APIConnectionError, RateLimitError) as e:
            logger.error(f"OpenAI API connection/rate limit error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"OpenAI API service unavailable: {str(e)}"
            )
        except APIStatusError as e:
            logger.error(f"OpenAI API status error: {e}")
            raise HTTPException(
                status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OpenAI API error: {e.message or str(e)}",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}"
            )

    return wrapper
