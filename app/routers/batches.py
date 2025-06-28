from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime, timezone # Import datetime for timestamp conversion

from app.db.session import get_db # Dependency to get DB session
from app.schemas import batch as batch_schemas # Pydantic schemas
from app.db.crud import batch as batch_crud # CRUD operations
from app.core.config import settings # For API prefix
from app.db.models.models import BatchStatus # Import Enum for template context

logger = logging.getLogger(__name__)

# TODO: remove this as dashboard is now in the main app
# This router handles batch-related endpoints, including the HTML dashboard and API endpoints
# APIRouter for batch-related endpoints
router = APIRouter()

# Configure Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# --- Jinja2 Filter for Unix Timestamp Formatting ---
def format_unix_timestamp(value: Optional[int], format_str: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """Jinja2 filter to convert Unix timestamp (int) to formatted datetime string."""
    if value is None:
        return "N/A"
    try:
        # Assume timestamp is in seconds
        dt_object = datetime.fromtimestamp(value, tz=timezone.utc)
        # Format, potentially converting to local timezone if needed, but UTC is safer for consistency
        return dt_object.strftime(format_str) + " UTC"
    except (TypeError, ValueError):
        return "Invalid Timestamp"

# Add the custom filter to the Jinja2 environment
templates.env.filters['unix_ts'] = format_unix_timestamp


# === HTML Dashboard Endpoint ===

@router.get("/dashboard", response_class=HTMLResponse, name="view_dashboard", tags=["Dashboard"])
async def read_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Renders the HTML dashboard displaying batch requests.

    Fetches batch data from the database and passes it to the Jinja2 template.
    Includes BatchStatus enum and timestamp formatting filter in the context.
    """
    logger.info("Request received for dashboard view.")
    try:
        # Fetch batches (consider adding pagination in the future)
        batches_orm = batch_crud.get_batches(db, limit=1000) # Get ORM objects
        total_count = batch_crud.count_batches(db) # Get total count separately if needed
        logger.info(f"Rendering dashboard with {len(batches_orm)} batch records (Total: {total_count}).")

        # Convert ORM objects to Pydantic models to ensure correct structure for template
        # This also helps if you add computed properties to your Pydantic models later
        batches_data = [batch_schemas.Batch.model_validate(b) for b in batches_orm]

        # Pass request, data, Enum, and potentially helper functions/filters to the template
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "batches": batches_data, # Pass Pydantic models
                "total_count": total_count,
                "BatchStatus": BatchStatus # Pass enum for use in template logic/display
                # The 'unix_ts' filter is added globally above
            }
        )
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while loading the dashboard."
        )


# === API Endpoints for Batch Management ===
# These endpoints now use the updated schemas implicitly via type hints

@router.post(
    "/",
    response_model=batch_schemas.Batch, # Returns the full Batch schema
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Batch Request",
    tags=["Batch API"]
)
def create_batch_endpoint(
    batch_in: batch_schemas.OpenAIBatchCreate, # Uses the updated OpenAIBatchCreate schema
    db: Session = Depends(get_db)
):
    """
    Registers a new OpenAI batch job in the tracking system.

    Expects data conforming to the `OpenAIBatchCreate` schema.
    Checks if a batch with the same OpenAI ID already exists.
    """
    logger.info(f"Received request to create batch record for OpenAI ID: {batch_in.openai_batch_id}")
    existing_batch = batch_crud.get_batch_by_openai_id(db, openai_batch_id=batch_in.openai_batch_id)
    if existing_batch:
        logger.warning(f"Batch with OpenAI ID {batch_in.openai_batch_id} already exists (DB ID: {existing_batch.id}).")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Batch with OpenAI ID '{batch_in.openai_batch_id}' already exists.",
        )
    try:
        created_batch_orm = batch_crud.create_batch(db=db, batch=batch_in)
        logger.info(f"Successfully registered batch with DB ID: {created_batch_orm.id}")
        # Return the Pydantic model representation
        return batch_schemas.Batch.model_validate(created_batch_orm)
    except Exception as e:
        logger.error(f"API Error: Failed to create batch for OpenAI ID {batch_in.openai_batch_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create batch record in the database.",
        )


@router.get(
    "/",
    response_model=batch_schemas.BatchListResponse, # Uses the updated Batch schema within the list
    summary="List Batch Requests",
    tags=["Batch API"]
)
def list_batches_endpoint(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return")
):
    """
    Retrieves a list of tracked batch jobs with pagination.
    """
    logger.info(f"Received request to list batches with skip={skip}, limit={limit}")
    try:
        batches_orm = batch_crud.get_batches(db, skip=skip, limit=limit)
        total_count = batch_crud.count_batches(db)
        # Convert ORM objects to Pydantic models for the response
        batches_data = [batch_schemas.Batch.model_validate(b) for b in batches_orm]
        logger.info(f"Returning {len(batches_data)} batch records out of total {total_count}.")
        return batch_schemas.BatchListResponse(total=total_count, batches=batches_data)
    except Exception as e:
        logger.error(f"API Error: Failed to list batches: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve batch records."
        )


@router.get(
    "/{openai_batch_id}",
    response_model=batch_schemas.Batch, # Uses the updated Batch schema
    summary="Get Batch Request by OpenAI ID",
    tags=["Batch API"]
)
def get_batch_endpoint(
    openai_batch_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves details of a specific batch job using its OpenAI Batch ID.
    """
    logger.info(f"Received request to get batch details for OpenAI ID: {openai_batch_id}")
    db_batch_orm = batch_crud.get_batch_by_openai_id(db, openai_batch_id=openai_batch_id)
    if db_batch_orm is None:
        logger.warning(f"Batch with OpenAI ID {openai_batch_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch with OpenAI ID '{openai_batch_id}' not found."
        )
    logger.info(f"Returning details for batch with OpenAI ID: {openai_batch_id} (DB ID: {db_batch_orm.id})")
    # Return the Pydantic model representation
    return batch_schemas.Batch.model_validate(db_batch_orm)


@router.patch(
    "/{openai_batch_id}",
    response_model=batch_schemas.Batch, # Uses the updated Batch schema
    summary="Update Batch Request Status/Details",
    tags=["Batch API"]
)
def update_batch_endpoint(
    openai_batch_id: str,
    batch_in: batch_schemas.BatchUpdate, # Uses the updated BatchUpdate schema
    db: Session = Depends(get_db)
):
    """
    Updates the status or other details of a specific batch job based on OpenAI ID.
    Expects data conforming to the `BatchUpdate` schema (partial updates allowed).
    """
    logger.info(f"Received request to update batch OpenAI ID: {openai_batch_id}")
    db_batch_orm = batch_crud.get_batch_by_openai_id(db, openai_batch_id=openai_batch_id)
    if db_batch_orm is None:
        logger.warning(f"Update failed: Batch with OpenAI ID {openai_batch_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch with OpenAI ID '{openai_batch_id}' not found."
        )

    # Check if there's anything to update by dumping the input schema
    if not batch_in.model_dump(exclude_unset=True):
         logger.info(f"No update data provided for batch OpenAI ID: {openai_batch_id}. Returning current data.")
         # Return current data as Pydantic model
         return batch_schemas.Batch.model_validate(db_batch_orm)

    try:
        updated_batch_orm = batch_crud.update_batch(db=db, db_batch=db_batch_orm, batch_update=batch_in)
        logger.info(f"Successfully updated batch OpenAI ID: {openai_batch_id} (DB ID: {updated_batch_orm.id})")
        # Return the updated Pydantic model representation
        return batch_schemas.Batch.model_validate(updated_batch_orm)
    except Exception as e:
        logger.error(f"API Error: Failed to update batch OpenAI ID {openai_batch_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update batch record."
        )

# (Placeholder for /refresh endpoint remains the same)
