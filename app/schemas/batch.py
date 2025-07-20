from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from openai.types import (
    Batch as OpenAIBatch,
)

# Import the status enum from the model to ensure consistency
from app.db.models import BatchStatus


# --- Helper Schema for OpenAI Error Object ---
class OpenAIError(BaseModel):
    """Represents a single error object within the 'errors' list from OpenAI."""

    code: Optional[str] = None
    message: Optional[str] = None
    param: Optional[str] = None
    line: Optional[int] = None


# --- Helper Schema for OpenAI Request Counts ---
class RequestCounts(BaseModel):
    """Represents the request_counts object from OpenAI."""

    total: int
    completed: int
    failed: int


# --- Base Schema ---
# Contains common fields, mapping closely to the OpenAI Batch object structure
class BatchBase(BaseModel):
    """Base Pydantic schema for Batch Request data, aligned with OpenAI API."""

    openai_batch_id: str = Field(
        ..., description="The unique ID of the batch object (e.g., batch_abc123)."
    )
    object_type: str = Field(
        default="batch", description="The object type, typically 'batch'."
    )
    endpoint: str = Field(..., description="The API endpoint used by the batch.")
    input_file_id: str = Field(
        ..., description="The ID of the input file for the batch."
    )
    completion_window: str = Field(
        default="24h",
        description="The time frame within which the batch should be processed.",
    )
    status: BatchStatus = Field(
        ..., description="The current status of the batch job."
    )  # Now required, maps to OpenAI status

    # Optional fields that appear based on status/outcome
    output_file_id: Optional[str] = Field(
        None, description="The ID of the file containing the outputs of the batch."
    )
    error_file_id: Optional[str] = Field(
        None, description="The ID of the file containing errors for the batch."
    )
    errors: Optional[Dict[str, List[OpenAIError]]] = Field(
        None,
        description="Structured errors encountered during processing (adheres to OpenAI spec).",
    )  # Updated structure
    request_counts: Optional[RequestCounts] = Field(
        None, description="Counts for requests within the batch."
    )

    # Timestamps (Unix epoch seconds)
    openai_created_at: Optional[int] = Field(
        None, description="Unix timestamp (seconds) for when the batch was created."
    )
    in_progress_at: Optional[int] = Field(
        None, description="Unix timestamp for when the batch started processing."
    )
    expires_at: Optional[int] = Field(
        None, description="Unix timestamp for when the batch will expire."
    )
    finalizing_at: Optional[int] = Field(
        None, description="Unix timestamp for when the batch started finalizing."
    )
    completed_at: Optional[int] = Field(
        None, description="Unix timestamp for when the batch was completed."
    )
    failed_at: Optional[int] = Field(
        None, description="Unix timestamp for when the batch failed."
    )
    cancelled_at: Optional[int] = Field(
        None, description="Unix timestamp for when the batch was cancelled."
    )

    # Metadata
    metadata_: Optional[Dict[str, Any]] = Field(
        None,
        alias="metadata",
        description="Set of key-value pairs attached to the object.",
    )

    # Pydantic V2 configuration
    model_config = ConfigDict(
        populate_by_name=True,  # Allows using 'metadata' alias
        from_attributes=True,  # Allow creating from ORM model
    )


# --- Schema for Creating a Batch Record ---
# Fields required when initially registering a batch known to us
class BatchEndpoint(str, Enum):
    """Supported OpenAI batch endpoints."""

    RESPONSES = "/v1/responses"
    CHAT_COMPLETIONS = "/v1/chat/completions"
    EMBEDDINGS = "/v1/embeddings"
    COMPLETIONS = "/v1/completions"


class OpenAIBatchCreate(BaseModel):
    """
    Schema for creating a new OpenAI batch.
    - Doc: https://platform.openai.com/docs/api-reference/batch/create
    """

    input_file_id: str = Field(
        ...,
        description=(
            "ID of the OpenAI file containing batch requests"
            "<br>The ID of an uploaded file that contains requests for the new batch.</br>"
            "See upload file for how to upload a file. Your input file must be formatted as a JSONL file, and must be uploaded with the purpose batch."
            "<br>The file can contain up to 50,000 requests, and can be up to 200 MB in size.</br>"
        ),
    )
    endpoint: BatchEndpoint = Field(
        ...,
        description=(
            "API endpoint for the batch, e.g., /v1/chat/completions."
            "<br>The endpoint to be used for all requests in the batch.</br>"
        ),
    )
    completion_window: str = Field(
        "24h", description="Time frame within which batch should be processed"
    )
    metadata: dict[str, str] | None = Field(
        None, description="Optional metadata map (max 16 key-value pairs)"
    )
    # TODO:  Use the config dict methods here
    class Config:
        schema_extra = {
            "example": {
                "input_file_id": "file-abc123",
                "endpoint": "/v1/chat/completions",
                "completion_window": "24h",
                "metadata": {
                    "customer_id": "user_123456789",
                    "batch_description": "Nightly eval job",
                },
            }
        }


class OpenAIBatchStatus(str, Enum):
    """
    Represents the status of an OpenAI Batch.
    ```
    Status      Description
    ------------------------------------------------------------------------------------------
    validating:  the input file is being validated before the batch can begin
    failed:      the input file has failed the validation process
    in_progress: the input file was successfully validated and the batch is currently being run
    finalizing:  the batch has completed and the results are being prepared
    completed:   the batch has been completed and the results are ready
    expired:     the batch was not able to be completed within the 24-hour time window
    cancelling:  the batch is being cancelled (may take up to 10 minutes)
    cancelled:   the batch was cancelled
    ```
    Doc: https://platform.openai.com/docs/guides/batch#4-check-the-status-of-a-batch
    """

    VALIDATING = "validating"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"

class OpenAIBatchResponse(OpenAIBatch):
    """
    Response schema returned by OpenAI when creating a batch.
    """

    id: str
    object: str
    endpoint: str
    errors: list | None
    input_file_id: str
    completion_window: str
    status: OpenAIBatchStatus
    output_file_id: str | None
    error_file_id: str | None
    created_at: int
    in_progress_at: int | None
    expires_at: int | None
    finalizing_at: int | None
    completed_at: int | None
    failed_at: int | None
    expired_at: int | None
    cancelling_at: int | None
    cancelled_at: int | None
    request_counts: dict
    metadata: dict | None = Field(
        None,
        description=(
            "Set of 16 key-value pairs that can be attached to an object. "
            "This can be useful for storing additional information about the object in a structured format, and querying for objects via API or the dashboard. "
            "Keys are strings with a maximum length of 64 characters. Values are strings with a maximum length of 512 characters."
        ),
    )

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "batch_abc123",
                "object": "batch",
                "endpoint": "/v1/chat/completions",
                "errors": None,
                "input_file_id": "file-abc123",
                "completion_window": "24h",
                "status": "validating",
                "output_file_id": None,
                "error_file_id": None,
                "created_at": 1711471533,
                "in_progress_at": None,
                "expires_at": None,
                "finalizing_at": None,
                "completed_at": None,
                "failed_at": None,
                "expired_at": None,
                "cancelling_at": None,
                "cancelled_at": None,
                "request_counts": {"total": 0, "completed": 0, "failed": 0},
                "metadata": {
                    "customer_id": "user_123456789",
                    "batch_description": "Nightly eval job",
                },
            }
        }


# --- Schema for Creating a Batch Record in Our DB ---
class BatchCreateInDB(BaseModel):
    """Schema used for creating a new BatchRequest record in our database."""

    # Typically, you get these details *after* creating the batch via OpenAI API
    openai_batch_id: str = Field(
        ..., description="The unique ID returned by OpenAI Batch API."
    )
    input_file_id: str = Field(
        ..., description="OpenAI File ID provided during creation."
    )
    endpoint: BatchEndpoint = Field(
        ..., description="The OpenAI API endpoint targetted."
    )
    completion_window: str = Field(
        default="24h", description="Completion window requested."
    )
    status: BatchStatus = Field(
        default=BatchStatus.PENDING,
        description="Initial status (can be updated once OpenAI confirms).",
    )  # Default to internal 'pending'
    metadata_: Optional[Dict[str, Any]] = Field(
        None, alias="metadata", description="Optional user-defined metadata."
    )
    openai_created_at: Optional[int] = Field(
        None, description="Unix timestamp from OpenAI creation response."
    )  # Can be set on creation

    model_config = ConfigDict(populate_by_name=True)


# --- Schema for Updating a Batch Record ---
# Fields likely to change based on polling OpenAI API
class BatchUpdateInDB(BaseModel):
    """Schema used for updating an existing BatchRequest record, typically from OpenAI API polling."""

    # Make fields optional for partial updates based on fetched data
    status: Optional[BatchStatus] = Field(
        None, description="Updated status from OpenAI."
    )
    output_file_id: Optional[str] = Field(
        None, description="Updated output file ID from OpenAI."
    )
    error_file_id: Optional[str] = Field(
        None, description="Updated error file ID from OpenAI."
    )
    errors: Optional[Dict[str, List[OpenAIError]]] = Field(
        None, description="Updated structured errors from OpenAI."
    )
    request_counts: Optional[RequestCounts] = Field(
        None, description="Updated request counts from OpenAI."
    )

    # Timestamps that might get populated as the batch progresses
    in_progress_at: Optional[int] = Field(
        None, description="Updated 'in_progress_at' timestamp."
    )
    expires_at: Optional[int] = Field(
        None, description="Updated 'expires_at' timestamp."
    )  # Usually static after creation
    finalizing_at: Optional[int] = Field(
        None, description="Updated 'finalizing_at' timestamp."
    )
    completed_at: Optional[int] = Field(
        None, description="Updated 'completed_at' timestamp."
    )
    failed_at: Optional[int] = Field(None, description="Updated 'failed_at' timestamp.")
    cancelled_at: Optional[int] = Field(
        None, description="Updated 'cancelled_at' timestamp."
    )

    # Metadata could potentially be updated via OpenAI API, though less common
    metadata_: Optional[Dict[str, Any]] = Field(
        None, alias="metadata", description="Updated metadata."
    )

    # Pydantic V2 configuration
    model_config = ConfigDict(
        extra="ignore",  # Ignore extra fields not defined in schema
        populate_by_name=True,  # Allow using 'metadata' alias
    )


# --- Schema for Reading/Returning Batch Data ---
# Includes internal DB fields along with OpenAI fields
# TODO: remove this if not in used for primary functions
# This will be removed as the DB utils will be removed
class Batch(BatchBase):
    """Schema used for returning BatchRequest data from the API, including internal DB fields."""

    id: int = Field(..., description="Internal database ID of the batch record.")
    created_at: datetime = Field(
        ..., description="Timestamp when the record was created in *this* system."
    )
    updated_at: datetime = Field(
        ..., description="Timestamp when the record was last updated in *this* system."
    )

    # Inherits all fields from BatchBase
    # Ensure model_config includes from_attributes=True if not inherited implicitly
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


# # --- Schema for Paginated Batch List Response ---
# class BatchListResponse(BaseModel):
#     """Schema for returning a list of batches with pagination info."""

#     total: int = Field(..., description="Total number of batch records available.")
#     batches: List[Batch] = Field(
#         ..., description="List of batch records for the current page."
#     )


class ListBatchesRequestParams(BaseModel):
    after: Optional[str] = Field(
        None,
        description="A cursor for use in pagination. `after` is an object ID that defines your place in the list.",
    )
    limit: Optional[int] = Field(
        20,
        ge=1,
        le=100,
        description="A limit on the number of objects to be returned. Limit can range between 1 and 100, and the default is 20.",
    )


class ListBatchesResponse(BaseModel):
    """Schema for paginated list of batches."""

    object: str
    data: List[OpenAIBatchResponse]
    first_id: Optional[str]
    last_id: Optional[str]
    has_more: bool

    class Config:
        orm_mode = True
