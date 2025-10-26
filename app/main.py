import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.api import batches as batches_api
from app.api import docs as docs_api
from app.api import files as files_api
from app.mcp.server import create_mcp_server, create_mcp_app, McpAppModes
from app.utils.config import settings, Environments
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
        await run_shutdown_logic()
        logger.info("Application lifespan: Shutdown sequence completed.")


templates = Jinja2Templates(directory="app/templates")


# --- FastAPI Application Instance ---
app = FastAPI(
    title="OpenAI Batch Tracker API",
    version="0.1.0",
    description="API for tracking OpenAI Batch API jobs and managing associated files.",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


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
app.include_router(docs_api.router, prefix="/docs-viewer", tags=["Documentation"])

if settings.CONF_ENV == Environments.DEV:
    from app.api import dummy as dummy_api

    app.include_router(dummy_api.router, prefix="/dummy", tags=["Dummy Endpoints"])
    logger.info("Running in DEV environment - included dummy endpoints.")


# --- Root Endpoint ---
@app.get("/", response_class=HTMLResponse, tags=["Root"])
async def read_root(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"portfolio_url": settings.PORTFOLIO_URL},
    )


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


# --- MCP Integration ---
mcp_server = create_mcp_server(app)
mode = (
    McpAppModes.EVENT_STORE  # Use Redis-backed event store for production
    if settings.CONF_ENV == Environments.PROD
    else McpAppModes.STATEFUL  # Dev uses in-memory session management
)
mcp_app = create_mcp_app(mcp_server, mode=mode)


@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    """Combined lifespan for FastAPI and MCP apps.
    Last In, First Out" (LIFO) execution order.
    - Doc: https://gofastmcp.com/integrations/fastapi#combining-lifespans"""
    async with lifespan(app):
        # Run the Startup logic of the FASTAPI app

        # Using the default lifespan of the MCP app
        async with mcp_app.lifespan(app):
            # Run the Startup logic of the MCP app
            # Now the Main application runs here
            yield
            # Run the Shutdown logic of the MCP app

        # Runs the Shutdown logic of the FASTAPI app


combined_app = FastAPI(
    title="OpenAI Batch Tracker API with MCP",
    routes=[
        *mcp_app.routes,
        *app.routes,
    ],
    summary="Model Context Protocol & API",
    description="MCP & APIs for tracking OpenAI Batch API jobs and managing associated files.",
    version=app.version,
    lifespan=combined_lifespan,
)

combined_app.mount("/mcp", mcp_app)


# Doc: https://gofastmcp.com/integrations/fastapi#offering-an-llm-friendly-api
# Now you have:
# - Regular API: http://localhost:8000/
# - LLM-friendly MCP: http://localhost:8000/mcp/
# Both served from the same FastAPI application!

if __name__ == "__main__":
    port = settings.SERVER_PORT
    should_reload = settings.CONF_ENV == Environments.DEV
    logger.info("For Env: %s, starting app on port %d with reload=%s", settings.CONF_ENV, port, should_reload)

    uvicorn.run(
        app="app.main:combined_app",
        host=settings.SERVER_HOST,
        port=port,
        reload=should_reload,
        workers=1 if should_reload else 5,
    )
