from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
import enum

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
    openai_batch_id: str = Field(..., description="The unique ID of the batch object (e.g., batch_abc123).")
    object_type: str = Field(default="batch", description="The object type, typically 'batch'.")
    endpoint: str = Field(..., description="The API endpoint used by the batch.")
    input_file_id: str = Field(..., description="The ID of the input file for the batch.")
    completion_window: str = Field(default="24h", description="The time frame within which the batch should be processed.")
    status: BatchStatus = Field(..., description="The current status of the batch job.") # Now required, maps to OpenAI status

    # Optional fields that appear based on status/outcome
    output_file_id: Optional[str] = Field(None, description="The ID of the file containing the outputs of the batch.")
    error_file_id: Optional[str] = Field(None, description="The ID of the file containing errors for the batch.")
    errors: Optional[Dict[str, List[OpenAIError]]] = Field(None, description="Structured errors encountered during processing (adheres to OpenAI spec).") # Updated structure
    request_counts: Optional[RequestCounts] = Field(None, description="Counts for requests within the batch.")

    # Timestamps (Unix epoch seconds)
    openai_created_at: Optional[int] = Field(None, description="Unix timestamp (seconds) for when the batch was created.")
    in_progress_at: Optional[int] = Field(None, description="Unix timestamp for when the batch started processing.")
    expires_at: Optional[int] = Field(None, description="Unix timestamp for when the batch will expire.")
    finalizing_at: Optional[int] = Field(None, description="Unix timestamp for when the batch started finalizing.")
    completed_at: Optional[int] = Field(None, description="Unix timestamp for when the batch was completed.")
    failed_at: Optional[int] = Field(None, description="Unix timestamp for when the batch failed.")
    cancelled_at: Optional[int] = Field(None, description="Unix timestamp for when the batch was cancelled.")

    # Metadata
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata", description="Set of key-value pairs attached to the object.")

    # Pydantic V2 configuration
    model_config = ConfigDict(
        populate_by_name=True, # Allows using 'metadata' alias
        from_attributes=True,  # Allow creating from ORM model
    )

# --- Schema for Creating a Batch Record ---
# Fields required when initially registering a batch known to us
class BatchCreate(BaseModel):
    """Schema used for creating a new BatchRequest record in our database."""
    # Typically, you get these details *after* creating the batch via OpenAI API
    openai_batch_id: str = Field(..., description="The unique ID returned by OpenAI Batch API.")
    input_file_id: str = Field(..., description="OpenAI File ID provided during creation.")
    endpoint: str = Field(..., description="The OpenAI API endpoint targetted.")
    completion_window: str = Field(default="24h", description="Completion window requested.")
    status: BatchStatus = Field(default=BatchStatus.PENDING, description="Initial status (can be updated once OpenAI confirms).") # Default to internal 'pending'
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata", description="Optional user-defined metadata.")
    openai_created_at: Optional[int] = Field(None, description="Unix timestamp from OpenAI creation response.") # Can be set on creation

    model_config = ConfigDict(populate_by_name=True)


# --- Schema for Updating a Batch Record ---
# Fields likely to change based on polling OpenAI API
class BatchUpdate(BaseModel):
    """Schema used for updating an existing BatchRequest record, typically from OpenAI API polling."""
    # Make fields optional for partial updates based on fetched data
    status: Optional[BatchStatus] = Field(None, description="Updated status from OpenAI.")
    output_file_id: Optional[str] = Field(None, description="Updated output file ID from OpenAI.")
    error_file_id: Optional[str] = Field(None, description="Updated error file ID from OpenAI.")
    errors: Optional[Dict[str, List[OpenAIError]]] = Field(None, description="Updated structured errors from OpenAI.")
    request_counts: Optional[RequestCounts] = Field(None, description="Updated request counts from OpenAI.")

    # Timestamps that might get populated as the batch progresses
    in_progress_at: Optional[int] = Field(None, description="Updated 'in_progress_at' timestamp.")
    expires_at: Optional[int] = Field(None, description="Updated 'expires_at' timestamp.") # Usually static after creation
    finalizing_at: Optional[int] = Field(None, description="Updated 'finalizing_at' timestamp.")
    completed_at: Optional[int] = Field(None, description="Updated 'completed_at' timestamp.")
    failed_at: Optional[int] = Field(None, description="Updated 'failed_at' timestamp.")
    cancelled_at: Optional[int] = Field(None, description="Updated 'cancelled_at' timestamp.")

    # Metadata could potentially be updated via OpenAI API, though less common
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata", description="Updated metadata.")

    # Pydantic V2 configuration
    model_config = ConfigDict(
        extra='ignore',        # Ignore extra fields not defined in schema
        populate_by_name=True, # Allow using 'metadata' alias
    )


# --- Schema for Reading/Returning Batch Data ---
# Includes internal DB fields along with OpenAI fields
class Batch(BatchBase):
    """Schema used for returning BatchRequest data from the API, including internal DB fields."""
    id: int = Field(..., description="Internal database ID of the batch record.")
    created_at: datetime = Field(..., description="Timestamp when the record was created in *this* system.")
    updated_at: datetime = Field(..., description="Timestamp when the record was last updated in *this* system.")

    # Inherits all fields from BatchBase
    # Ensure model_config includes from_attributes=True if not inherited implicitly
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

# --- Schema for Paginated Batch List Response ---
class BatchListResponse(BaseModel):
    """Schema for returning a list of batches with pagination info."""
    total: int = Field(..., description="Total number of batch records available.")
    batches: List[Batch] = Field(..., description="List of batch records for the current page.")
