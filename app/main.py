import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from app.utils.config import settings, Evironments
from app.api import files as files_api
from app.api import batches as batches_api
from app.utils.init_helper import run_startup_logic, run_shutdown_logic
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events using helper functions.
    - Initializes resources on startup (before yield).
    - Cleans up resources on shutdown (after yield).
    """
    logger.info("Application lifespan: Initiating startup sequence...")
    try:
        logger.info(
            f"Application settings loaded successfully for project: {settings.PROJECT_NAME}",
            extra=settings.model_dump(),
        )
        run_startup_logic()
        logger.info("Application lifespan: Startup sequence completed successfully.")
        # This is where the application will run until shutdown.
        # The application runs while the lifespan context manager is active
        yield

    except Exception as e:
        logger.exception(f"Application lifespan: CRITICAL error during startup: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Application failed to initialize critical services: {str(e)}",
        ) from e
    finally:
        # This block executes regardless of whether an exception occurred in the try block or during app execution.
        logger.info("Application lifespan: Initiating shutdown sequence...")
        run_shutdown_logic()
        logger.info("Application lifespan: Shutdown sequence completed.")


templates = Jinja2Templates(directory="app/templates")


# --- FastAPI Application Instance ---
app = FastAPI(
    title="OpenAI Batch Tracker API",
    version="0.1.0",
    description="API for tracking OpenAI Batch API jobs and managing associated files.",
    lifespan=lifespan,
)


# --- Custom Exception Handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_messages = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append(
            {
                "field": field,
                "message": message,
                "type": error["type"],
            }
        )
    logger.warning(f"Request validation error: {exc.errors()} for request: {request.method} {request.url}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation Error", "errors": error_messages},
    )


# --- API Routers ---

app.include_router(files_api.router, prefix="/files", tags=["Files"])

app.include_router(batches_api.router, prefix="/batches", tags=["Batches"])

if settings.CONF_ENV == Evironments.LOCAL:
    from app.api import dummy as dummy_api

    app.include_router(dummy_api.router, prefix="/dummy", tags=["Dummy Endpoints"])
    logger.info("Running in LOCAL environment - included dummy endpoints.")


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    return {
        "message": "Welcome to OpenAI Batch Tracker API!",
        "project_version": app.version,
        "documentation": "/docs",
        "apis": ["/files", "/batches"],
        "environment": settings.CONF_ENV,
    }


# --- Health Check Endpoint ---
@app.get(
    "/status",
    description="Endpoint for Service Availability, including database connectivity.",
    tags=["Health Check"],
)
def service_status_check():
    """
    Provides the operational status of the service, including its
    ability to connect to the database.
    """
    logger.info("Health check endpoint '/status' accessed.")

    response_content = {
        "service_status": "ok",
    }

    return JSONResponse(content=response_content, status_code=status.HTTP_200_OK)


if __name__ == "__main__":
    port = settings.SERVER_PORT
    should_reload = True if settings.CONF_ENV == Evironments.LOCAL else False
    logger.info("For Env: %s, starting app on port %d with reload=%s", settings.CONF_ENV, port, should_reload)

    uvicorn.run(
        app="app.main:app",
        host=settings.SERVER_HOST,
        port=port,
        reload=should_reload,
        workers=5,
    )
