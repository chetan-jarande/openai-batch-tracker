from enum import StrEnum
from typing import Literal
from openai.types import FileObject as OpenAIFileObject
from pydantic import BaseModel, Field, ConfigDict

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class OpenAIFilePurpose(StrEnum):
    """
    Enum representing valid purposes for OpenAI files.
    Based on: https://platform.openai.com/docs/api-reference/files/create
    """

    ASSISTANTS = "assistants"  # Used in the Assistants API
    BATCH = "batch"  # Used in the Batch API
    FINE_TUNE = "fine-tune"  # Used for fine-tuning
    VISION = "vision"  # Images used for vision fine-tuning
    USER_DATA = "user_data"  # Flexible file type for any purpose
    EVALS = "evals"  # Used for eval data sets


# --- Schemas for OpenAI File Object (for responses) ---
class OpenAIFileObjectSchema(OpenAIFileObject):
    """
    Pydantic schema representing an OpenAI File object, as returned by their API.
    Based on: https://platform.openai.com/docs/api-reference/files/object
    """

    id: str = Field(description="The file identifier, which can be referenced in the API endpoints.")
    bytes: int = Field(description="The size of the file, in bytes.")
    created_at: int = Field(description="The Unix timestamp (in seconds) for when the file was created.")
    filename: str = Field(description="The name of the file.", examples=["mydata.jsonl"])
    object: Literal["file"] = Field(default="file", description="The object type, which is always 'file'.")
    purpose: OpenAIFilePurpose = Field(
        description="The intended purpose of the file. Docs https://platform.openai.com/docs/api-reference/files/object#files/object-purpose."
    )
    expires_at: int | None = Field(None, description="The Unix timestamp (in seconds) for when the file will expire.")

    status: Literal["uploaded", "processed", "error"] | None = Field(
        None,
        description="Deprecated: The current status of the file, which can be either 'uploaded', 'processed', or 'error'.",
    )
    status_details: str | None = Field(
        None,
        description="Deprecated: For details on why a fine-tuning training file failed validation, see the 'error' field on fine_tuning.job.",
    )

    model_config = ConfigDict(from_attributes=True)


class FileUploadRequest(BaseModel):
    """
    Schema for the request body parameters when uploading a file through our API.
    The actual file will be sent as a separate `UploadFile` form field.
    Doc: https://platform.openai.com/docs/api-reference/files/create
    """

    purpose: OpenAIFilePurpose = Field(
        default=OpenAIFilePurpose.BATCH,
        description="The purpose of the file. Defaults to 'batch'. Check docs for valid purposes.",
        examples=[
            OpenAIFilePurpose.BATCH,
            OpenAIFilePurpose.ASSISTANTS,
            OpenAIFilePurpose.FINE_TUNE,
            OpenAIFilePurpose.VISION,
            OpenAIFilePurpose.USER_DATA,
            OpenAIFilePurpose.EVALS,
        ],
    )


class OpenAIFileListRequestParams(BaseModel):
    """
    Pydantic model for query parameters when listing files from OpenAI.
    Inspired from openai.types.FileListParams.
    Based on: https://platform.openai.com/docs/api-reference/files/list
    """

    purpose: OpenAIFilePurpose | None = Field(
        None,
        description="Only return files with the given purpose.",
        examples=[
            OpenAIFilePurpose.BATCH,
            OpenAIFilePurpose.FINE_TUNE,
            OpenAIFilePurpose.ASSISTANTS,
        ],
    )
    limit: int = Field(
        50,  # Default value for OpenAI Files list is 10000
        description="A limit on the number of objects to be returned. Limit can range between 1 and 10000, and the default is 50.",
        ge=1,
        le=10000,
    )
    after: str | None = Field(
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
    model_config = ConfigDict(extra="forbid")  # Forbid extra fields not defined here


# --- Enum for File Content Actions ---
class FileContentAction(StrEnum):
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
        ),
        examples=[FileContentAction.GET_BYTES, FileContentAction.GET_JSON, FileContentAction.GET_TEXT],
    )
    download_as: str | None = Field(
        default=None,
        description=(
            "If provided, the file content will be streamed as a download with this filename. "
            "The 'action' parameter is ignored when 'download_as' is specified."
        ),
    )


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
        logger.info(f"OpenAIFileObjectSchema valid: {parsed_openai_file.model_dump_json(indent=2)}")
    except Exception as e:
        logger.error(f"OpenAIFileObjectSchema validation error: {e}")

    # Test FileUploadRequest
    upload_req_data = {"purpose": "assistants", "filename": "test.txt"}
    try:
        upload_req = FileUploadRequest(**upload_req_data)
        logger.info(f"FileUploadRequest valid: {upload_req.model_dump_json(indent=2)}")
        upload_req_default_purpose = FileUploadRequest(filename="test.txt")  # Purpose defaults to "batch"
        logger.info(
            f"FileUploadRequest (default purpose) valid: {upload_req_default_purpose.model_dump_json(indent=2)}"
        )

    except Exception as e:
        logger.error(f"FileUploadRequest validation error: {e}")

    # Test OpenAIFileListRequestParams
    list_params_data = {"limit": 10, "purpose": "batch"}
    try:
        list_params = OpenAIFileListRequestParams(**list_params_data)
        logger.info(f"OpenAIFileListRequestParams valid: {list_params.model_dump_json(indent=2)}")
        default_list_params = OpenAIFileListRequestParams()  # Test with defaults
        logger.info(f"OpenAIFileListRequestParams (defaults) valid: {default_list_params.model_dump_json(indent=2)}")
    except Exception as e:
        logger.error(f"OpenAIFileListRequestParams validation error: {e}")

    logger.info("File schemas test complete.")
