import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException # Added HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware # Optional: For CORS
from app.core.config import get_settings, Settings
from app.api.api_v1 import api_router_v1
from app.utils.init_helper import run_startup_logic, run_shutdown_logic


try:
    logger = logging.getLogger(__name__)
    settings: Settings = get_settings()
except Exception as e:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"Critical error during logging setup: {e}", exc_info=True)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events using helper functions.
    - Initializes resources on startup (before yield).
    - Cleans up resources on shutdown (after yield).
    """
    logger.info("Application lifespan: Initiating startup sequence...")
    try:
        # Run all startup tasks
        run_startup_logic() # Assuming it might become async in the future
        logger.info("Application lifespan: Startup sequence completed successfully.")
        # This is where the application will run until shutdown.
        # The application runs while the lifespan context manager is active
        yield

    except Exception as e:
        logger.exception(f"Application lifespan: CRITICAL error during startup: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Application failed to initialize critical services: {str(e)}"
        ) from e
    finally:
        # This block executes regardless of whether an exception occurred in the try block or during app execution.
        logger.info("Application lifespan: Initiating shutdown sequence...")
        run_shutdown_logic()
        logger.info("Application lifespan: Shutdown sequence completed.")


# --- FastAPI Application Instance ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    # docs_url=f"{settings.API_V1_STR}/docs",
    # redoc_url=f"{settings.API_V1_STR}/redoc",
    version="0.1.0",
    description="API for tracking OpenAI Batch API jobs and managing associated files.",
    lifespan=lifespan
)

# --- Middleware ---
# Example: CORS (Cross-Origin Resource Sharing)
# origins = [
#     "http://localhost",
#     "http://localhost:3000",
# ]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# logger.info(f"CORS middleware configured for origins: {origins}")


# --- Custom Exception Handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_messages = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append({ "field": field, "message": message, "type": error["type"]})
    logger.warning(f"Request validation error: {exc.errors()} for request: {request.method} {request.url}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation Error", "errors": error_messages},
    )


# --- API Routers ---
app.include_router(api_router_v1, prefix=settings.API_V1_STR)
logger.info(f"Included API v1 router with global prefix: '{settings.API_V1_STR}'.")

# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    logger.info("Root endpoint '/' accessed.")
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "status": "API is running",
        "documentation_v1": f"{settings.API_V1_STR}/docs",
        "project_version": app.version
    }


@app.get(
    "/status",
    description="Endpoint for checking if service is working or not",
    tags=["health-check"],
)
async def status_check():
    return {"message": "Service is running in the background."}



# --- Main execution (for Uvicorn) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting application directly using Uvicorn (for development/debugging)...")
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=True
    )
