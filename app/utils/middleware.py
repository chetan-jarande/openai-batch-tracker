import logging
import time
import uuid
import contextvars  # For managing request context across async tasks
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logging_config import get_logger


logger = get_logger(__name__)

# Context variable to store the request ID. Default is None.
# This makes the request_id accessible within the scope of a request, even across async calls.
request_id_context = contextvars.ContextVar("request_id", default="NotAvailable")


class RequestIdFilter(logging.Filter):
    """
    Logging filter that injects the current request ID, if available, into log records.
    """

    def filter(self, record):
        """Attaches the request_id from contextvars to the log record."""
        record.request_id = request_id_context.get()
        return True


class RequestContextLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject a unique request ID into logs and response headers.

    - Generates a unique UUID for each incoming request.
    - Stores the request ID in a context variable (`request_id_context`).
    - Adds the request ID to the response headers (`X-Request-ID`).
    - Logs basic request/response information including duration.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Processes the request, adds request ID, logs, and handles exceptions.
        """
        # Generate a unique request ID
        request_id = str(uuid.uuid4())

        # Set the request ID in the context variable.
        # The token is used to reset the context variable later.
        token = request_id_context.set(request_id)

        start_time = time.perf_counter()  # Use perf_counter for more accurate timing

        # Log basic request start info (request_id is now available via filter)
        logger.info(f"Request started: {request.method} {request.url.path}")

        response = None
        try:
            # Proceed with the request handling
            response = await call_next(request)
            # Calculate processing time
            process_time = time.perf_counter() - start_time
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            # Log basic response info
            logger.info(
                f"Request finished: {request.method} {request.url.path} "
                f"status_code={response.status_code} duration={process_time:.4f}s"
            )

        except Exception as e:
            process_time = time.perf_counter() - start_time
            # Log the exception details (request_id will be included by the filter)
            logger.exception(f"Request failed: {request.method} {request.url.path} duration={process_time:.4f}s")
            # Re-raise the exception so FastAPI's default exception handling can take over
            # Or return a generic error response:
            # response = Response("Internal Server Error", status_code=500)
            # response.headers["X-Request-ID"] = request_id
            raise e  # Re-raising is usually preferred

        finally:
            # Reset the context variable to its previous state or default
            request_id_context.reset(token)

        return response
