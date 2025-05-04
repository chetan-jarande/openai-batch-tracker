import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware # If needed for frontend interaction
from contextlib import asynccontextmanager

from core.config import settings
from core.logging_config import setup_logging
from db.session import init_db # Import the DB initializer
from routers import batches # Import the batches router
from openai import OpenAI

# Setup logging as early as possible
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application lifespan events.

    Handles startup and shutdown logic, such as initializing the database.
    """
    logger.info("Application startup sequence initiated...")
    # --- Startup ---
    try:
        logger.info("Initializing database...")
        init_db() # Create database tables if they don't exist
        logger.info("Database initialization complete.")
    except Exception as e:
        logger.critical(f"Failed to initialize database during startup: {e}", exc_info=True)
        # Depending on the severity, you might want to prevent the app from starting fully
        # For now, we log critical and continue, but the app might not function correctly.
        pass # Or raise an exception to stop startup

    logger.info("Application startup complete.")
    yield # Application runs after this point
    # --- Shutdown ---
    logger.info("Application shutdown sequence initiated...")
    # Add any cleanup logic here (e.g., closing connections if not handled by context managers)
    logger.info("Application shutdown complete.")


# Initialize FastAPI app with lifespan context manager
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json", # Customize OpenAPI schema URL
    version="0.1.0", # Set your app version
    lifespan=lifespan # Use the lifespan manager for startup/shutdown
)

# --- Middleware ---
# Add CORS middleware if your dashboard/frontend is served from a different origin
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"], # Or specify allowed origins: ["http://localhost:3000"]
#     allow_credentials=True,
#     allow_methods=["*"], # Or restrict methods: ["GET", "POST"]
#     allow_headers=["*"], # Or specify allowed headers
# )

# --- Routers ---
# Include the router for batch endpoints, prefixing them
app.include_router(batches.router, prefix="/batches", tags=["Batch API", "Dashboard"])
# Note: The dashboard route is defined within batches.router but accessed via /batches/dashboard

# --- Root Endpoint ---
@app.get("/", summary="Root Endpoint", tags=["General"])
async def read_root():
    """Provides a simple welcome message."""
    logger.info("Root endpoint accessed.")
    return {"message": f"Welcome to the {settings.PROJECT_NAME}!"}

# --- Custom Exception Handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles Pydantic validation errors for clearer client feedback."""
    logger.warning(f"Request validation error: {exc.errors()}", exc_info=False) # Log details without full stack trace for validation errors
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )

# Add more custom exception handlers if needed (e.g., for specific database errors)

# --- Run Instructions (for local development without Docker) ---
# If you run this file directly (e.g., `python app/main.py`),
# it won't start the server correctly with Uvicorn's features like hot-reloading.
# Use: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
# The Dockerfile will handle running Uvicorn correctly in the container.
