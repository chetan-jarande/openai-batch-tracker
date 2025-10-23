from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from app.utils.logging_config import get_logger
from app.schemas.batch import BatchEndpoint

logger = get_logger(__name__)

# Generic type variable for paginated responses
DataType = TypeVar("DataType")


class Msg(BaseModel):
    """
    Schema for a generic message response.
    """

    message: str = Field(..., description="A message detailing the result of an operation.")
    details: Optional[str] = Field(None, description="Optional additional details.")


class PaginatedResponse(BaseModel, Generic[DataType]):
    """
    Generic schema for paginated API responses.
    """

    count: int = Field(..., description="Total number of items available.")
    limit: int = Field(..., description="Number of items per page (page size).")
    offset: int = Field(..., description="Offset of the current page.")
    # next_page: Optional[str] = Field(None, description="URL for the next page of results, if any.")
    # previous_page: Optional[str] = Field(None, description="URL for the previous page of results, if any.")
    items: List[DataType] = Field(..., description="List of items for the current page.")


# # --- Schemas for Batch Input and output File Records ---


class ChatMessage(BaseModel):
    """Represents a single message in a chat completion request."""

    role: str = Field(..., description="The role of the message author (e.g., 'system', 'user', 'assistant').")
    content: str = Field(..., description="The content of the message.")


class ChatCompletionBody(BaseModel):
    """Represents the 'body' of a chat completion request in a batch file."""

    model: str = Field(..., description="The model to use for the chat completion.")
    messages: list[ChatMessage] = Field(..., description="A list of messages comprising the conversation so far.")


class BatchFileRecordInput(BaseModel):
    """
    Schema for a single record (line) in an OpenAI batch input file (JSONL).
    This represents one individual API request to be processed in the batch.
    Doc: https://platform.openai.com/docs/guides/batch/getting-started
    """

    custom_id: str = Field(..., description="A unique identifier for the request within the batch.")
    method: str = Field(..., description="The HTTP method of the request, typically 'POST'.")
    url: BatchEndpoint = Field(..., description="The API endpoint for the request (e.g., '/v1/chat/completions').")
    body: ChatCompletionBody = Field(..., description="The body of the request, containing model and messages.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "custom_id": "request-1",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "What is 2+2?"},
                    ],
                },
            }
        }
    )


class BatchFileRecordOutput(BaseModel):
    """
    Output of the processed for each record present in the batch file.
    Useful to validate the record structure in `openai-batch-tracker/app/resources/batch_output.jsonl` file.
    """

    id: str = Field(..., description="The unique identifier for the batch record in our system.")
    custom_id: str = Field(
        ..., description="A developer-provided per-request id that will be used to match outputs to inputs."
    )
    error: dict | None = Field(
        ...,
        description="Error details if the batch creation failed.",
        examples=[
            {"code": "batch_expired"},
            {"code": "batch_cancelled"},
            {"code": "request_timeout"},
        ],
    )
    response: dict[str, Any] = Field(..., description="Optional metadata associated with the batch.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "batch_req_wnaDys",
                "custom_id": "request-2",
                "response": {
                    "status_code": 200,
                    "request_id": "req_c187b3",
                    "body": {
                        "id": "chatcmpl-9758Iw",
                        "object": "chat.completion",
                        "created": 1711475054,
                        "model": "gpt-4o-mini",
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": "2 + 2 equals 4."},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 24, "completion_tokens": 15, "total_tokens": 39},
                        "system_fingerprint": None,
                    },
                },
                "error": None,
            }
        }
    )
