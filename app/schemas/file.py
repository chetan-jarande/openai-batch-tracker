import logging
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.common import PaginatedResponse # For paginated list response

logger = logging.getLogger(__name__)

# --- Base Schemas ---
class FileBase(BaseModel):
    """
    Base schema for file attributes.
    Common fields shared across create and read schemas.

    Doc: https://platform.openai.com/docs/api-reference/files
    """
    openai_file_id: str = Field(
        ...,
        description="The unique identifier for the file on OpenAI's servers.",
        examples=["file-abc123xyz789"]
    )
    filename: str = Field(
        ...,
        description="The name of the file.",
        examples=["my_batch_input.jsonl"]
    )
    bytes_size: int = Field(
        ...,
        description="Size of the file in bytes.",
        ge=0, # Must be greater than or equal to 0
        examples=[10240] # 10KB
    )
    purpose: str = Field(
        ...,
        description="The intended purpose of the file (e.g., 'batch', 'fine-tune').",
        examples=["batch"]
    )
    status: Optional[str] = Field(
        None,
        description="The current status of the file processing on OpenAI (e.g., 'uploaded', 'processed', 'error').",
        examples=["uploaded"]
    )
    status_details: Optional[str] = Field(
        None,
        description="Additional details about the file's status, especially in case of errors.",
        examples=["File processing failed due to invalid format."]
    )
    openai_created_at: Optional[int] = Field(
        None,
        description="Unix timestamp of when the file was created on OpenAI's servers.",
        examples=[1677652286]
    )

# --- Schemas for API Requests ---
class FileCreate(FileBase):
    """
    Schema for creating a new file record in our database.
    This is typically used after a file has been successfully uploaded to OpenAI.
    """
    # All fields are inherited from FileBase and are required.
    # No additional fields needed here for now, as FileBase covers the essentials.
    pass

class FileUploadRequest(BaseModel):
    """
    Schema for the request body when uploading a file through our API.
    The actual file will be sent as `UploadFile`.
    This schema can carry additional metadata if needed, but for now,
    the primary input is the file itself.
    The 'purpose' is hardcoded to 'batch' in the endpoint.

    Doc: https://platform.openai.com/docs/api-reference/files/create
    """
    # filename: Optional[str] = Field(None, description="Optional: suggested filename. If not provided, uses the uploaded file's name.")
    # We might not need any fields here if FastAPI's UploadFile is sufficient
    # and purpose is handled directly in the endpoint.
    pass


# --- Schemas for API Responses (Public Facing) ---
class FilePublic(FileBase):
    """
    Schema for representing a file when returned by the API (public view).
    This includes our internal database ID and audit timestamps.
    """
    # TODO: Make sure This id should be same as the OpenAI file ID
    id: int = Field(..., description="Internal database ID of the file record.")
    ## TODO: Make sure This id should be set when we get success from the OpenAI API
    created_at: datetime = Field(..., description="Timestamp when the file record was created in our database.")
    updated_at: datetime = Field(..., description="Timestamp when the file record was last updated in our database.")

    # Pydantic V2 configuration for ORM mode
    model_config = ConfigDict(from_attributes=True)


class PaginatedFilePublicResponse(PaginatedResponse[FilePublic]):
    """
    Paginated response for listing files.
    Doc: https://platform.openai.com/docs/api-reference/files/list
    """
    # TODO:  make sure the file listing get the the necessary parameters mentioned in the doc
    pass


# --- Schemas for Database Interaction (Internal) ---
class FileInDBBase(FileBase):
    """
    Schema for file data as it's stored in the database, including internal ID.
    This is an intermediate base for ORM model interaction.
    """
    id: int = Field(..., description="Internal database ID.")
    created_at: datetime = Field(..., description="Timestamp of creation in our database.")
    updated_at: datetime = Field(..., description="Timestamp of last update in our database.")

    # Pydantic V2 configuration for ORM mode
    model_config = ConfigDict(from_attributes=True)


class FileUpdate(BaseModel):
    """
    Schema for updating an existing file record.
    Allows partial updates, so all fields are optional.
    """
    openai_file_id: Optional[str] = None
    filename: Optional[str] = None
    bytes_size: Optional[int] = Field(None, ge=0)
    purpose: Optional[str] = None
    status: Optional[str] = None
    status_details: Optional[str] = None
    openai_created_at: Optional[int] = None

    model_config = ConfigDict(extra='forbid') # Forbid extra fields during update


# # Testing the schemas
if __name__ == "__main__":
    logger.info("Testing file schemas...")

    # Test FileCreate schema
    file_create_data = {
        "openai_file_id": "file-123",
        "filename": "batch_data.jsonl",
        "bytes_size": 2048,
        "purpose": "batch",
        "status": "uploaded",
        "openai_created_at": 1677652300
    }
    try:
        created_file = FileCreate(**file_create_data)
        logger.info(f"FileCreate valid: {created_file.model_dump_json(indent=2)}")
    except Exception as e:
        logger.error(f"FileCreate validation error: {e}")

    # Test FilePublic schema (simulating data from DB)
    file_public_data = {
        "id": 1,
        "openai_file_id": "file-456",
        "filename": "another_batch.jsonl",
        "bytes_size": 4096,
        "purpose": "batch",
        "status": "processed",
        "openai_created_at": 1677652400,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    try:
        public_file = FilePublic(**file_public_data)
        logger.info(f"FilePublic valid: {public_file.model_dump_json(indent=2)}")
    except Exception as e:
        logger.error(f"FilePublic validation error: {e}")

    # Test FileUpdate schema
    file_update_data = {"status": "error", "status_details": "Processing failed."}
    try:
        update_file = FileUpdate(**file_update_data)
        logger.info(f"FileUpdate valid: {update_file.model_dump_json(indent=2)}")
    except Exception as e:
        logger.error(f"FileUpdate validation error: {e}")

    # Test PaginatedFilePublicResponse
    paginated_files_data = {
        "count": 1,
        "limit": 10,
        "offset": 0,
        "items": [file_public_data] # Re-use the public_file_data for an item
    }
    try:
        paginated_response = PaginatedFilePublicResponse(**paginated_files_data)
        logger.info(f"PaginatedFilePublicResponse valid: {paginated_response.model_dump_json(indent=2)}")
    except Exception as e:
        logger.error(f"PaginatedFilePublicResponse validation error: {e}")

    logger.info("File schemas test complete.")
