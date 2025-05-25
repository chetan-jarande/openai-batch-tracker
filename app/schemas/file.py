import logging
from enum import Enum
from datetime import datetime
from typing import Optional, List, Literal
from openai.types import (
    FileListParams,
    FileObject as OpenAIFileObject,
)
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.common import PaginatedResponse  # For paginated list response

logger = logging.getLogger(__name__)


# --- Schemas for OpenAI File Object (for responses) ---
class OpenAIFileObjectSchema(OpenAIFileObject):
    """
    Pydantic schema representing an OpenAI File object, as returned by their API.
    Based on: https://platform.openai.com/docs/api-reference/files/object
    """
    # Parent should suffice the OpenAI FileObject requirements here
    # this class is created to add more thing on top of what is there already under OpenAI's FileObject class
    pass

    # id: str = Field(
    #     description="The file identifier, which can be referenced in other API endpoints."
    # )
    # bytes: int = Field(description="The size of the file, in bytes.")
    # created_at: int = Field(
    #     description="The Unix timestamp (in seconds) for when the file was created."
    # )
    # filename: str = Field(description="The name of the file.")
    # object: Literal["file"] = Field(
    #     description="The object type, which is always 'file'."
    # )
    # purpose: str = Field(
    #     description="The intended purpose of the file. Supported values are 'fine-tune', 'fine-tune-results', 'assistants', and 'assistants_output'."
    # )
    # status: Optional[str] = Field(
    #     None,
    #     description="Deprecated. The current status of the file, which can be 'uploaded', 'processed', 'error'.",
    # )
    # status_details: Optional[str] = Field(
    #     None,
    #     description="Deprecated. For details on why a fine-tune training file failed processing, see the `error` field on the fine-tune object.",
    # )

    # model_config = ConfigDict(from_attributes=True)


# --- Base Schemas for our internal representation ---
class FileBase(BaseModel):
    """
    Base schema for file attributes for our internal database records.
    Common fields shared across create and read schemas.
    Reflects the structure of an OpenAI File object but adapted for our DB.
    """

    openai_file_id: str = Field(
        ...,
        description="The unique identifier for the file on OpenAI's servers.",
        examples=["file-abc123xyz789"],
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
        description="The intended purpose of the file (e.g., 'batch', 'fine-tune', 'assistants').",
        examples=["batch"],
    )
    status: Optional[str] = Field(
        None,
        description="The current status of the file processing on OpenAI (e.g., 'uploaded', 'processed', 'error').",
        examples=["uploaded"],
    )
    status_details: Optional[str] = Field(
        None,
        description="Additional details about the file's status, especially in case of errors.",
        examples=["File processing failed due to invalid format."],
    )
    openai_created_at: Optional[int] = Field(
        None,
        description="Unix timestamp of when the file was created on OpenAI's servers.",
        examples=[1677652286],
    )


# --- Schemas for API Requests ---
class FileCreate(FileBase):
    """
    Schema for creating a new file record in our database.
    This is typically used after a file has been successfully uploaded to OpenAI.
    """

    pass


class FileUploadRequest(BaseModel):
    """
    Schema for the request body parameters when uploading a file through our API.
    The actual file will be sent as a separate `UploadFile` form field.
    Doc: https://platform.openai.com/docs/api-reference/files/create
    """

    filename: Optional[str] = Field(
        None,
        description="Optional: suggested filename. If not provided, uses the uploaded file's name (default fallback).",
    )
    purpose: str = Field(
        "batch",
        description="The purpose of the file. Defaults to 'batch'.",
        examples=[
            "batch", # Used in the Batch API
            "assistants", # Used in the Assistants API
            "fine-tune", # Used for fine-tuning
            "vision", # Images used for vision fine-tuning
            "user_data", # Flexible file type for any purpose
            "evals", # Used for eval data sets
        ],
    )


class OpenAIFileListRequestParams(BaseModel):
    """
    Pydantic model for query parameters when listing files from OpenAI.
    Based on: https://platform.openai.com/docs/api-reference/files/list
    """
    # TODO: Check if we can leverage OpenAI's FileListParams directly here by inheriting this class from it.
    purpose: Optional[str] = Field(
        None, description="Only return files with the given purpose."
    )
    limit: int = Field(
        50,  # Default value for OpenAI Files list is 10000
        description="A limit on the number of objects to be returned. Limit can range between 1 and 10000, and the default is 50.",
        ge=1,
        le=10000,
    )
    after: Optional[str] = Field(
        None,
        description=(
            "Identifier for the last file from the previous pagination request.<br/>"
            "A cursor for use in pagination. `after` is an object ID that defines your place in the list.<br/>"
            "For instance, if you make a list request and receive 100 objects, ending with obj_foo, "
            "your subsequent call can include after=obj_foo in order to fetch the next page of the list."
        ),
    )
    order: Literal["asc", "desc"] = Field(
        "desc",  # Default value as per OpenAI docs
        description="Sort order by the 'created_at' timestamp of the objects. 'asc' for ascending order and 'desc' for descending order.",
    )


# --- Schemas for API Responses (Public Facing for our DB records) ---
class FilePublic(FileBase):
    """
    Schema for representing a file from our database when returned by the API (public view).
    This includes our internal database ID and audit timestamps.
    """
    # TODO: Make sure This id should be same as the OpenAI file ID
    id: int = Field( # This is our internal auto-incrementing primary key
        ..., description="Internal database ID of the file record."
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the file record was created in our database."
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the file record was last updated in our database.",
    )
    model_config = ConfigDict(from_attributes=True)


class PaginatedFilePublicResponse(PaginatedResponse[FilePublic]):
    """
    Paginated response for listing files from our database.
    """

    pass


# --- Schemas for Database Interaction (Internal) ---
class FileInDBBase(FileBase):
    """
    Schema for file data as it's stored in the database, including internal ID.
    This is an intermediate base for ORM model interaction.
    """

    id: int = Field(..., description="Internal database ID.")
    created_at: datetime = Field(
        ..., description="Timestamp of creation in our database."
    )
    updated_at: datetime = Field(
        ..., description="Timestamp of last update in our database."
    )
    model_config = ConfigDict(from_attributes=True)


class FileUpdate(BaseModel):
    """
    Schema for updating an existing file record in our database.
    Allows partial updates, so all fields are optional.
    """

    openai_file_id: Optional[str] = None
    filename: Optional[str] = None
    bytes_size: Optional[int] = Field(None, ge=0)
    purpose: Optional[str] = None
    status: Optional[str] = None
    status_details: Optional[str] = None
    openai_created_at: Optional[int] = None
    model_config = ConfigDict(extra="forbid") # Forbid extra fields during update



# --- Enum for File Content Actions ---
class FileContentAction(str, Enum):
    """
    Defines the possible actions to perform with the retrieved file content
    when NOT downloading it as a file.
    """
    GET_JSON = "get_json"
    GET_TEXT = "get_text"
    GET_BYTES = "get_bytes"

# --- Pydantic Model for File Content Request Parameters ---
class FileContentRequestParams(BaseModel):
    """
    Parameters to control how file content retrieved from OpenAI is processed and returned.
    """
    action: FileContentAction = Field(
        default=FileContentAction.GET_BYTES,
        description=(
            "Action to perform if `download_as` is not provided. "
            "`get_json` attempts to parse and return content as JSON. "
            "`get_text` returns content as a UTF-8 decoded string. "
            "`get_bytes` returns the raw binary content in the response body."
        )
    )
    download_as: Optional[str] = Field(
        default=None,
        description=(
            "If provided, the file content will be streamed as a download with this filename. "
            "The 'action' parameter is ignored when 'download_as' is specified."
        )
    )




# --- Example Usage ---
# # Testing the schemas
if __name__ == "__main__":
    logger.info("Testing file schemas...")

    # Test OpenAIFileObjectSchema
    openai_file_data = {
        "id": "file-Example123",
        "bytes": 1024,
        "created_at": 1677652286,
        "filename": "example.jsonl",
        "object": "file",
        "purpose": "fine-tune",
        "status": "processed",
    }
    try:
        parsed_openai_file = OpenAIFileObjectSchema(**openai_file_data)
        logger.info(
            f"OpenAIFileObjectSchema valid: {parsed_openai_file.model_dump_json(indent=2)}"
        )
    except Exception as e:
        logger.error(f"OpenAIFileObjectSchema validation error: {e}")

    # Test FileUploadRequest
    upload_req_data = {"purpose": "assistants", "filename": "test.txt"}
    try:
        upload_req = FileUploadRequest(**upload_req_data)
        logger.info(f"FileUploadRequest valid: {upload_req.model_dump_json(indent=2)}")
        upload_req_default_purpose = FileUploadRequest(
            filename="test.txt"
        )  # Purpose defaults to "batch"
        logger.info(
            f"FileUploadRequest (default purpose) valid: {upload_req_default_purpose.model_dump_json(indent=2)}"
        )

    except Exception as e:
        logger.error(f"FileUploadRequest validation error: {e}")

    # Test OpenAIFileListRequestParams
    list_params_data = {"limit": 10, "purpose": "batch"}
    try:
        list_params = OpenAIFileListRequestParams(**list_params_data)
        logger.info(
            f"OpenAIFileListRequestParams valid: {list_params.model_dump_json(indent=2)}"
        )
        default_list_params = OpenAIFileListRequestParams()  # Test with defaults
        logger.info(
            f"OpenAIFileListRequestParams (defaults) valid: {default_list_params.model_dump_json(indent=2)}"
        )
    except Exception as e:
        logger.error(f"OpenAIFileListRequestParams validation error: {e}")

    # Test FileCreate schema
    file_create_data = {
        "openai_file_id": "file-123",
        "filename": "batch_data.jsonl",
        "bytes_size": 2048,
        "purpose": "batch",
        "status": "uploaded",
        "openai_created_at": 1677652300,
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
        "updated_at": datetime.now(),
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
