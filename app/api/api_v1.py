import logging
from fastapi import APIRouter
from app.api import files as files_api
# TODO: Uncomment the following import when batches API is implemented
# from app.api import batches as batches_api

logger = logging.getLogger(__name__)

# Create the main router for API v1
# All routes defined in the included routers will be prefixed by settings.API_V1_STR (e.g., /api/v1)
# when this router is included in the main FastAPI application.
api_router_v1 = APIRouter()

# Include the files router
# All routes from files_api.router will be prefixed with /files
# e.g., /api/v1/files/upload, /api/v1/files/
api_router_v1.include_router(
    files_api.router,
    prefix="/files",
    tags=["Files"],
    # dependencies=[Depends(get_current_active_user)] # Example: Add common dependencies for this group
)
logger.info("Included Files API router into API v1 router with prefix '/files'.")

# Include the batches router
# All routes from batches_api.router will be prefixed with /batches
# e.g., /api/v1/batches/, /api/v1/batches/{openai_batch_id}
# TODO: Uncomment and implement the batches API
# api_router_v1.include_router(
#     batches_api.router,
#     prefix="/batches",
#     tags=["Batches"],
# )
# logger.info("Included Batches API router into API v1 router with prefix '/batches'.")


if __name__ == "__main__":
    # This block is for illustrative purposes and won't run in the app context.
    # It demonstrates the structure of the included routes conceptually.
    logger.info("API v1 router configured with the following route groups:")
    for route in api_router_v1.routes:
        # Note: This inspection is basic. FastAPI's internal structure for routes is more complex.
        # For APIRoute instances, we can get more details.
        if hasattr(route, "path") and hasattr(route, "name") and hasattr(route, "methods"):
             logger.info(f"  - Route: Path='{route.path}', Name='{route.name}', Methods={route.methods}")
        elif hasattr(route, "prefix") and hasattr(route, "tags"): # For included routers (less detail here)
             logger.info(f"  - Included Router: Prefix='{route.prefix}', Tags={route.tags}")
        else:
             logger.info(f"  - Other route/component: {type(route)}")

    logger.info("To see full route details, run the FastAPI application and check /docs or /redoc.")

