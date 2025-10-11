from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from enum import StrEnum

from openai.types import Batch as OpenAIBatch


class OpenAIError(BaseModel):
    """Represents a single error object within the 'errors' list from OpenAI."""

    code: str = None
    message: str = None
    param: str = None
    line: int = None


# --- Schemas for Usage Details ---
class InputTokensDetails(BaseModel):
    """A detailed breakdown of the input tokens."""

    cached_tokens: int = Field(..., description="The number of tokens that were retrieved from the cache.")


class OutputTokensDetails(BaseModel):
    """A detailed breakdown of the output tokens."""

    reasoning_tokens: int = Field(..., description="The number of reasoning tokens.")


class OpenAIUsage(BaseModel):
    """
    Represents token usage details including input tokens, output tokens,
    a breakdown of output tokens, and the total tokens used.
    Only populated on batches created after September 7, 2025.
    """

    input_tokens: int = Field(..., description="The number of input tokens.")
    input_tokens_details: InputTokensDetails = Field(..., description="A detailed breakdown of the input tokens.")
    output_tokens: int = Field(..., description="The number of output tokens.")
    output_tokens_details: OutputTokensDetails = Field(..., description="A detailed breakdown of the output tokens.")
    total_tokens: int = Field(..., description="The total number of tokens used.")


class RequestCounts(BaseModel):
    """Represents the request_counts object from OpenAI."""

    total: int
    completed: int
    failed: int


class OpenAIBatchStatus(StrEnum):
    """
    Represents the status of an OpenAI Batch.
    ```
    Status      Description
    -------------------------------------------------------------------------------------------
    validating:  The input file is being validated before the batch can begin
    failed:      The input file has failed the validation process
    in_progress: The input file was successfully validated and the batch is currently being run
    finalizing:  The batch has completed and the results are being prepared
    completed:   The batch has been completed and the results are ready
    expired:     The batch was not able to be completed within the 24-hour time window
    cancelling:  The batch is being cancelled (may take up to 10 minutes)
    cancelled:   The batch was cancelled
    -------------------------------------------------------------------------------------------
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


class BatchEndpoint(StrEnum):
    """
    Supported OpenAI batch endpoints.
    Available endpoints for batch processing as per
    [OpenAI documentation](https://platform.openai.com/docs/guides/batch/getting-started#1-prepare-your-batch-file).
    """

    RESPONSES = "/v1/responses"
    CHAT_COMPLETIONS = "/v1/chat/completions"
    EMBEDDINGS = "/v1/embeddings"
    COMPLETIONS = "/v1/completions"
    MODERATIONS = "/v1/moderations"


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
    completion_window: str = Field("24h", description="Time frame within which batch should be processed")
    metadata: dict[str, str] | None = Field(None, description="Optional metadata map (max 16 key-value pairs)")

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class OpenAIBatchResponse(OpenAIBatch):
    """
    Response schema returned by OpenAI when creating a batch.
    """

    id: str = Field(..., description="The unique identifier for the batch.")
    object: str = Field(default="batch")
    endpoint: BatchEndpoint = Field(
        ...,
        description="The API endpoint used by the batch.  batches are also restricted to a maximum of 50,000 embedding inputs across all requests in the batch.",
    )
    errors: Dict[str, List[OpenAIError]] | None = Field(
        None,
        description="Structured errors encountered during processing (adheres to OpenAI spec).",
        examples=[{"data": [], "object": "list"}],
    )
    input_file_id: str = Field(..., description="The ID of the input file for the batch.")
    completion_window: str = Field(
        default="24h",
        description="The time frame within which the batch should be processed.",
    )
    status: OpenAIBatchStatus = Field(..., description="The current status of the batch.")
    output_file_id: str | None = Field(None, description="The ID of the file containing the outputs of the batch.")
    error_file_id: str | None = Field(None, description="The ID of the file containing errors for the batch.")
    created_at: int | None = Field(None, description="Unix timestamp (seconds) for when the batch was created.")
    in_progress_at: int | None = Field(None, description="Unix timestamp for when the batch started processing.")
    expires_at: int | None = Field(None, description="Unix timestamp for when the batch will expire.")
    finalizing_at: int | None = Field(None, description="Unix timestamp for when the batch started finalizing.")
    completed_at: int | None = Field(None, description="Unix timestamp for when the batch was completed.")
    failed_at: int | None = Field(None, description="Unix timestamp for when the batch failed.")
    expired_at: int | None
    cancelling_at: int | None
    cancelled_at: int | None = Field(None, description="Unix timestamp for when the batch was cancelled.")
    request_counts: RequestCounts = Field(
        ..., description="The request counts for different statuses within the batch."
    )
    usage: OpenAIUsage | None = Field(None, description="Usage statistics for the batch, if available.")
    metadata: dict | None = Field(
        None,
        description=(
            "Set of 16 key-value pairs that can be attached to an object. "
            "This can be useful for storing additional information about the object in a structured format, and querying for objects via API or the dashboard. "
            "Keys are strings with a maximum length of 64 characters. Values are strings with a maximum length of 512 characters."
        ),
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "batch_abc123",
                "object": "batch",
                "endpoint": "/v1/chat/completions",
                "errors": None,  # or Error details like {"data": [], "object": "list"}
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
                "request_counts": {"total": 100, "completed": 95, "failed": 5},
                "usage": {
                    "input_tokens": 1500,
                    "input_tokens_details": {"cached_tokens": 1024},
                    "output_tokens": 500,
                    "output_tokens_details": {"reasoning_tokens": 300},
                    "total_tokens": 2000,
                },
                "metadata": {
                    "customer_id": "user_123456789",
                    "batch_description": "Nightly eval job",
                },
            }
        },
    )


class ListBatchesRequestParams(BaseModel):
    """Schema for query parameters when listing batches from OpenAI.
    Link: https://platform.openai.com/docs/api-reference/batch/list"""

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

    model_config = ConfigDict(from_attributes=True)
