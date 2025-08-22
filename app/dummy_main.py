import logging
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import time
import enum
import random  # For generating varied mock data

# --- Setup Logging (Basic) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Mimic Enums and Schemas (Simplified for Mocking) ---
## Doc: https://help.openai.com/en/articles/9197833-batch-api-faq
## Doc code: https://platform.openai.com/docs/guides/batch#4-check-the-status-of-a-batch
# Status	    Description
# validating	the input file is being validated before the batch can begin
# failed	    the input file has failed the validation process
# in_progress	the input file was successfully validated and the batch is currently being run
# finalizing	the batch has completed and the results are being prepared
# completed	    the batch has been completed and the results are ready
# expired	    the batch was not able to be completed within the 24-hour time window
# cancelling	the batch is being cancelled (may take up to 10 minutes)
# cancelled	    the batch was cancelled


class BatchStatus(enum.StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


class OpenAIError(BaseModel):
    """Represents a single error object within the 'errors' list from OpenAI."""

    code: Optional[str] = None
    message: Optional[str] = None
    param: Optional[str] = None
    line: Optional[int] = None


class RequestCounts(BaseModel):
    """Represents the request_counts object from OpenAI."""

    total: int
    completed: int
    failed: int


class MockBatch(BaseModel):
    """Simplified Pydantic schema for mock batch data."""

    id: int
    openai_batch_id: str
    status: BatchStatus
    endpoint: str
    input_file_id: str
    output_file_id: Optional[str] = None
    error_file_id: Optional[str] = None
    errors: Optional[Dict[str, List[OpenAIError]]] = None  # Match structure
    request_counts: Optional[RequestCounts] = None
    openai_created_at: Optional[int] = None
    expires_at: Optional[int] = None
    completed_at: Optional[int] = None
    failed_at: Optional[int] = None
    cancelled_at: Optional[int] = None
    created_at: datetime  # System timestamp


# --- FastAPI App ---
app = FastAPI(title="Dummy Batch Tracker")

# Assume templates are in a 'templates' subdirectory relative to this script
templates = Jinja2Templates(directory="app/templates")


# --- Jinja2 Filter for Unix Timestamp Formatting ---
def format_unix_timestamp(
    value: Optional[int], format_str: str = "%Y-%m-%d %H:%M:%S %Z"
) -> str:
    """Jinja2 filter to convert Unix timestamp (int) to formatted datetime string."""
    if value is None:
        return "N/A"
    try:
        dt_object = datetime.fromtimestamp(value, tz=timezone.utc)
        return dt_object.strftime(format_str) + " UTC"
    except (TypeError, ValueError):
        return "Invalid Timestamp"


templates.env.filters["unix_ts"] = format_unix_timestamp


# --- Generate Mock Data ---
def create_mock_data(count: int = 15) -> List[MockBatch]:
    """Generates a list of varied mock batch data."""
    mock_batches = []
    now = datetime.now(timezone.utc)
    now_unix = int(time.mktime(now.timetuple()))

    statuses = list(BatchStatus)

    for i in range(1, count + 1):
        status = random.choice(statuses)
        batch_id = f"batch_{'abc' * (i % 3 + 1)}{i:03d}{random.choice(['x', 'y', 'z'])}"
        input_file = f"file_in_{i:03d}{random.randint(100, 999)}"
        created_unix = now_unix - random.randint(
            3600, 86400 * 5
        )  # Created within last 5 days
        expires_unix = created_unix + 24 * 3600  # Expires 24h after creation

        output_file = None
        error_file = None
        errors_data = None
        req_counts = None
        completed_unix = None
        failed_unix = None
        cancelled_unix = None

        total_requests = 100  # Assume 100 total requests for simplicity

        if status == BatchStatus.COMPLETED:
            output_file = f"file_out_{i:03d}{random.randint(100, 999)}"
            completed_unix = created_unix + random.randint(
                600, 18 * 3600
            )  # Completed within 18 hours
            # *** FIX START ***
            # Calculate completed count first
            completed_count = random.randint(95, total_requests)
            # Calculate failed count based on completed count
            failed_count = total_requests - completed_count
            req_counts = RequestCounts(
                total=total_requests, completed=completed_count, failed=failed_count
            )
            # *** FIX END ***

        elif status == BatchStatus.FAILED:
            failed_unix = created_unix + random.randint(600, 18 * 3600)
            if random.random() > 0.5:  # Sometimes have an error file
                error_file = f"file_err_{i:03d}{random.randint(100, 999)}"
            else:  # Sometimes have structured errors
                errors_data = {
                    "data": [
                        OpenAIError(
                            code=str(random.randint(400, 500)),
                            message=f"Mock error on processing line {random.randint(1, 50)}.",
                            param=random.choice([None, "input"]),
                            line=random.randint(1, 50),
                        )
                    ]
                }
            # *** FIX START ***
            # Calculate completed count first
            completed_count = random.randint(0, 80)
            # Calculate failed count based on completed count
            failed_count = total_requests - completed_count
            req_counts = RequestCounts(
                total=total_requests, completed=completed_count, failed=failed_count
            )
            # *** FIX END ***

        elif status == BatchStatus.CANCELLED:
            cancelled_unix = created_unix + random.randint(600, 18 * 3600)

        elif status in [
            BatchStatus.IN_PROGRESS,
            BatchStatus.FINALIZING,
            BatchStatus.VALIDATING,
        ]:
            # *** FIX START ***
            # Calculate completed count first
            completed_count = random.randint(0, 50)
            # Assume a small number of failures even while in progress
            failed_count = random.randint(0, 5)
            # Create RequestCounts object
            req_counts = RequestCounts(
                total=total_requests, completed=completed_count, failed=failed_count
            )
            # *** FIX END ***

        mock_batches.append(
            MockBatch(
                id=i,
                openai_batch_id=batch_id,
                status=status,
                endpoint=random.choice(["/v1/chat/completions", "/v1/embeddings"]),
                input_file_id=input_file,
                output_file_id=output_file,
                error_file_id=error_file,
                errors=errors_data,
                request_counts=req_counts,
                openai_created_at=created_unix,
                expires_at=expires_unix,
                completed_at=completed_unix,
                failed_at=failed_unix,
                cancelled_at=cancelled_unix,
                created_at=datetime.fromtimestamp(
                    created_unix - random.randint(0, 300), tz=timezone.utc
                ),  # System time slightly after OpenAI time
            )
        )
    return mock_batches


# --- Dummy Dashboard Endpoint ---
@app.get("/dummy-dashboard", response_class=HTMLResponse, name="view_dummy_dashboard")
async def read_dummy_dashboard(request: Request):
    """Renders the HTML dashboard with mocked batch data."""
    logger.info("Request received for dummy dashboard view.")
    try:
        mock_data = create_mock_data(25)  # Generate 25 mock entries
        total_count = len(mock_data)
        logger.info(f"Rendering dummy dashboard with {total_count} mock batch records.")

        # Pass request, data, and Enum to the template
        return templates.TemplateResponse(
            "dummy_dashboard.html",  # Use the specific dummy template name
            {
                "request": request,
                "batches": mock_data,  # Pass the generated mock data
                "total_count": total_count,
                "BatchStatus": BatchStatus,  # Pass enum for use in template logic/display
            },
        )
    except Exception as e:
        logger.error(f"Error rendering dummy dashboard: {e}", exc_info=True)
        # Simple error response for dummy app
        return HTMLResponse(
            content=f"<h1>Error</h1><p>Could not render dummy dashboard: {e}</p>",
            status_code=500,
        )


@app.get("/")
async def read_root():
    return {"message": "Dummy Batch Tracker API. Go to /dummy-dashboard to view."}


# --- Run Instructions ---
# Save this file as dummy_main.py
# Create a directory named 'templates' in the same location.
# Save the HTML content below as 'templates/dummy_dashboard.html'.
# Install dependencies: pip install fastapi uvicorn jinja2 pydantic
# Go to the root level of the project directory
# Run the server: uvicorn app.dummy_main:app --reload --port 8001
# Access in browser: http://localhost:8001/dummy-dashboard
