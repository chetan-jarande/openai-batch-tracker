from typing import Any, List
import asyncio
from openai.types import FileDeleted
from fastapi import (
    APIRouter,
    Request,
    HTTPException,
    status,
    UploadFile,
    File as FastApiFile,
    Depends,
    Path,
)
from fastapi.responses import (
    Response,
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
    HTMLResponse,
)
from fastapi.templating import Jinja2Templates

from openai import HttpxBinaryResponseContent

from app.schemas import file as file_schema
from app.utils.common import format_unix_timestamp
from app.utils.deps import OpenAIClient, AsyncOpenAIClient
from app.utils.logging_config import get_logger
from app.utils.error_handlers import handle_openai_errors, async_handle_openai_errors


logger = get_logger(__name__)

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["unix_ts"] = format_unix_timestamp


# support for multiple files in this endpoint.
# - doc: https://fastapi.tiangolo.com/tutorial/request-files/#multiple-file-uploads-with-additional-metadata
@router.post(
    "/upload",
    response_model=List[file_schema.OpenAIFileObjectSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Upload File(s) to OpenAI",
    operation_id="upload_openai_file",
    description="Uploads one or more files to OpenAI<br/>More details in Doc: https://platform.openai.com/docs/api-reference/files/create",
)
@async_handle_openai_errors
async def upload_file_to_openai(
    client: AsyncOpenAIClient,
    files: List[UploadFile] = FastApiFile(..., description="The batch input file(s) to upload (e.g., .jsonl files)."),
    request_params: file_schema.FileUploadRequest = Depends(),
) -> List[file_schema.OpenAIFileObjectSchema]:
    """
    Handles file uploads to OpenAI.
    1.  Receives one or more files via `UploadFile`.
    2.  Checks for duplicate filenames in OpenAI (optional but recommended).
    3.  Uploads the files to OpenAI using the `openai` client, with given purpose.
    Doc:
        - OpenAI Files: https://platform.openai.com/docs/api-reference/files/create
        - FAST API UploadFile with params:
            - https://fastapi.tiangolo.com/tutorial/request-files/#uploadfile-with-additional-metadata
            - https://fastapi.tiangolo.com/tutorial/request-forms-and-files/
    Args:
        request_params: Pydantic model for form fields like 'purpose'.
        client: Async OpenAI API client dependency.
        files: The list of files to be uploaded, provided by FastAPI's `UploadFile`.

    Returns:
        A list of `OpenAIFileObjectSchema` schema objects representing the stored file records.

    Raises:
        HTTPException:
            - 409 (Conflict): If a file with the same name already exists.
            - 400 (Bad Request): If the file upload to OpenAI fails for client-side reasons.
            - 500 (Internal Server Error): For OpenAI API errors.

    """
    purpose = request_params.purpose
    logger.info(f"Attempting to upload {len(files)} files with purpose: {purpose}")

    # Check for existing files with the same purpose to avoid duplicates
    existing_files_page = await client.files.list(purpose=purpose)
    # Create a set of existing filenames for quick lookup
    existing_filenames = {f.filename for f in existing_files_page.data}

    # Check if any of the files to be uploaded already exist
    for file in files:
        if file.filename in existing_filenames:
            logger.warning(f"File '{file.filename}' already exists in OpenAI with purpose '{purpose}'.")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File '{file.filename}' already exists in OpenAI with purpose '{purpose}'. Please rename or delete the existing file.",
            )

    uploaded_files = []

    async def upload_single_file(file: UploadFile) -> file_schema.OpenAIFileObjectSchema:
        logger.info(f"Uploading file: {file.filename}, content type: {file.content_type}")
        try:
            content = await file.read()
            uploaded_openai_file = await client.files.create(
                file=(file.filename, content, file.content_type),
                purpose=purpose,
            )
            logger.info(f"File '{file.filename}' uploaded successfully to OpenAI. File ID: {uploaded_openai_file.id}")
            return file_schema.OpenAIFileObjectSchema.model_validate(uploaded_openai_file)
        finally:
            await file.close()

    # Upload files in parallel
    uploaded_files = await asyncio.gather(*(upload_single_file(file) for file in files))

    return uploaded_files


@handle_openai_errors
def get_openai_files_list(
    client: OpenAIClient,
    data: file_schema.OpenAIFileListRequestParams,
) -> list[file_schema.OpenAIFileObjectSchema]:
    """
    Retrieves a list of files directly from the OpenAI account associated with the API key.
    Args:
        client:
            OpenAI API client dependency.
        data:
            Pydantic model for query parameters (e.g., `limit`, `offset`).
        Returns:
            A list of file objects from OpenAI, serialized as dictionaries.
    """
    # The `model_dump(exclude_none=True)` ensures only provided params are sent
    params = data.model_dump(exclude_none=True)
    logger.info(f"Listing files from OpenAI with params: {params}")
    openai_files_list_page = client.files.list(**params)

    # Validate and convert each FileObject from OpenAI to our Pydantic schema
    # The OpenAI SDK's FileObject should be compatible if our schema is correct.
    # The OpenAI SDK v1.x returns a SyncPage[FileObject] which can be iterated.
    # Each item in `openai_files_list.data` is a `FileObject`.

    response_data = [file_schema.OpenAIFileObjectSchema(**file_obj) for file_obj in openai_files_list_page.data]
    file_count = len(response_data)
    logger.info(f"Retrieved {file_count} files from OpenAI.")

    return response_data


@router.get(
    "/list",
    response_model=list[file_schema.OpenAIFileObjectSchema],
    status_code=status.HTTP_200_OK,
    summary="List Files from OpenAI Account for OpenAI API Key",
    operation_id="list_openai_files",
    description=(
        "Retrieves a list of files directly from the user's OpenAI account. Supports pagination.</br>"
        "See the [OpenAI List File API docs](https://platform.openai.com/docs/api-reference/files/list) for details."
    ),
)
def list_files_from_openai(
    client: OpenAIClient,
    params: file_schema.OpenAIFileListRequestParams = Depends(),
) -> list[file_schema.OpenAIFileObjectSchema]:
    """
    Lists files directly from the OpenAI account associated with the API key.
    Query parameters are now encapsulated in the `params` model.

    Args:
        client: OpenAI API client dependency.
        params: Pydantic model for query parameters (e.g., `limit`, `offset`).

    Returns:
        A list of file objects from OpenAI, serialized as dictionaries.

    Raises:
        HTTPException: For OpenAI API errors.

    Note:
        The response is a list of dictionaries directly from the OpenAI client's `FileObject.model_dump()`.
    """
    return get_openai_files_list(client, params)


@router.get(
    "/view/list",
    response_class=HTMLResponse,
    summary="View Files Dashboard",
    operation_id="view_openai_files_dashboard",
)
def view_files_dashboard(
    request: Request,
    client: OpenAIClient,
    params: file_schema.OpenAIFileListRequestParams = Depends(),
) -> HTMLResponse:
    """
    Renders the files dashboard HTML page.
    """
    response_data = get_openai_files_list(client, params)
    logger.debug("View mode enabled. Rendering files_dashboard.html")
    return templates.TemplateResponse(
        request,
        "files_dashboard.html",
        {
            "files": response_data,
            "total_count": len(response_data),
            "params": params,
        },
    )


@router.get(
    "/{openai_file_id}",
    response_model=file_schema.OpenAIFileObjectSchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve File Details from OpenAI",
    operation_id="get_openai_file_details",
    description=(
        "Retrieves details of a specific file from OpenAI using its OpenAI File ID.</br>"
        "See the [OpenAI Retrieve File API docs](https://platform.openai.com/docs/api-reference/files/retrieve) for details."
    ),
)
@handle_openai_errors
def retrieve_file_from_openai(
    client: OpenAIClient,
    openai_file_id: str = Path(
        ...,
        description="The OpenAI File ID of the file to retrieve.",
        examples=["file-abc123"],
        min_length=1,
    ),
) -> file_schema.OpenAIFileObjectSchema:
    """
    Retrieves a specific file record from OpenAI by its OpenAI File ID.

    Args:
        openai_file_id: The OpenAI File ID of the file to retrieve.
        client: OpenAI API client dependency.

    Returns:
        A `OpenAIFileObjectSchema` schema object if the file is found.

    Raises:
        HTTPException: 404 (Not Found) if the file record does not exist in the OpenAI.
                       500 (Internal Server Error) for other OpenAI errors.
    """
    logger.info(f"Retrieving file record from OpenAI for ID: {openai_file_id}")
    openai_file = client.files.retrieve(file_id=openai_file_id)
    if not openai_file:
        logger.warning(f"File record with OpenAI File ID '{openai_file_id}' not found in OpenAI.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with OpenAI ID '{openai_file_id}' not found.",
        )
    logger.info(f"File record found for OpenAI File ID: {openai_file_id}")
    return file_schema.OpenAIFileObjectSchema.model_validate(openai_file)


@router.delete(
    "/{openai_file_id}",
    response_model=FileDeleted,
    status_code=status.HTTP_200_OK,
    summary="Delete File from OpenAI",
    operation_id="delete_openai_file",
    description=(
        "Deletes a file from OpenAI's servers</br>"
        "See the [OpenAI Delete File API docs](https://platform.openai.com/docs/api-reference/files/delete) for details."
    ),
)
@handle_openai_errors
def delete_openai_file(
    client: OpenAIClient,
    openai_file_id: str = Path(
        ...,
        description="The OpenAI File ID of the file to delete.",
        examples=["file-abc123"],
        min_length=1,
    ),
) -> FileDeleted:
    """
    Deletes a file from both OpenAI and the local database.

    1.  Attempts to delete the file from OpenAI using its `openai_file_id`.
    2.  If successful (or if the file is already not found on OpenAI),

    Args:
        openai_file_id: The OpenAI File ID of the file to delete.
        client: OpenAI API client dependency.

    Returns:
        A FileDeleted schema object indicating the result of the operation.

    Raises:
        HTTPException:
            - 500 (Internal Server Error): For OpenAI API errors or database errors.
            - 503 (Service Unavailable): If OpenAI API is unavailable.
    """
    logger.info(f"Attempting to delete file with OpenAI ID: {openai_file_id}")

    openai_delete_response = client.files.delete(file_id=openai_file_id)
    if openai_delete_response.deleted:
        logger.info(f"File {openai_file_id} successfully deleted from OpenAI.")
    else:
        # This case might not happen if delete always raises error or returns deleted=True
        logger.warning(
            f"OpenAI reported file {openai_file_id} as not deleted, but no error raised. Response: {openai_delete_response}"
        )
    return JSONResponse(openai_delete_response.model_dump(), status_code=status.HTTP_200_OK)


# Retrieve file content
# # Doc from Batches -> https://platform.openai.com/docs/guides/batch#5-retrieve-the-results
@router.get(
    "content/v1/{openai_file_id}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve File Details from OpenAI",
    operation_id="get_openai_file_content_v1",
    deprecated=True,
    description=(
        "Retrieves details of a specific file from OpenAI using its OpenAI File ID. returns the file content as JSON.</br>"
        "See the [OpenAI Retrieve File Content API docs](https://platform.openai.com/docs/api-reference/files/retrieve-contents) for details."
    ),
)
@handle_openai_errors
def retrieve_file_content_from_openai_v1(
    client: OpenAIClient,
    openai_file_id: str = Path(
        ...,
        description="The OpenAI File ID of the file to retrieve.",
        examples=["file-abc123"],
        min_length=1,
    ),
) -> dict[str, Any]:
    """
    Retrieves a specific file record from OpenAI by its OpenAI File ID.

    Args:
        openai_file_id: The OpenAI File ID of the file to retrieve.
        client: OpenAI API client dependency.

    Returns:
        A dictionary representing the file content if the file is found.

    Raises:
        HTTPException: 404 (Not Found) if the file record does not exist in the OpenAI.
                       500 (Internal Server Error) for other OpenAI errors.
    """
    logger.info(f"Retrieving file record from OpenAI for ID: {openai_file_id}")
    content: HttpxBinaryResponseContent = client.files.content(file_id=openai_file_id)
    if not content:
        logger.warning(f"The File with OpenAI File ID '{openai_file_id}' not found in OpenAI nor it has any content.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with OpenAI ID '{openai_file_id}' not found.",
        )
    logger.info(f"File record found for OpenAI File ID: {openai_file_id}")
    return content.json()


@router.get(
    "/content/v2/{openai_file_id}",
    summary="Retrieve File Content or Trigger Download from OpenAI",
    status_code=status.HTTP_200_OK,
    operation_id="get_openai_file_content_v2",
    description=(
        "Retrieves file content from OpenAI. If 'download_as' is specified, triggers a file download.</br>"
        "Otherwise, returns content based on 'action' (JSON, text, bytes).</br>"
        "See the [OpenAI Retrieve File Content API docs](https://platform.openai.com/docs/api-reference/files/retrieve-contents) for details."
    ),
)
@async_handle_openai_errors
async def retrieve_file_content_from_openai_v2(
    client: AsyncOpenAIClient,
    params: file_schema.FileContentRequestParams = Depends(),
    openai_file_id: str = Path(
        ...,
        description="The OpenAI File ID of the file to retrieve.",
        examples=["file-abc123"],
        min_length=1,
    ),
) -> Any:
    """
    Retrieves file content from OpenAI.
    If `params.download_as` is provided, streams the file as a download using true streaming.
    Otherwise, returns content based on `params.action` by fetching the full content.
    """
    logger.info(f"Retrieving content for OpenAI File ID: {openai_file_id} with params: {params.model_dump()}")

    if params.download_as:
        logger.info(f"Action: Download file as '{params.download_as}' using with_streaming_response.")

        # Use with_streaming_response for true streaming from OpenAI
        # We define the generator to handle the async context manager properly during streaming
        async def stream_generator():
            try:
                # The context manager is entered when the generator starts iterating
                async with client.with_streaming_response.files.content(file_id=openai_file_id) as response:
                    async for chunk in response.iter_bytes():
                        yield chunk
            except Exception as e:
                logger.error(f"Error during file streaming for {openai_file_id}: {e}")
                # We can't raise HTTP exception here easily once streaming started,
                # but we can log it. The stream will close.

        download_filename = params.download_as if params.download_as.strip() else f"{openai_file_id}_content.dat"
        headers = {"Content-Disposition": f'attachment; filename="{download_filename}"'}
        return StreamingResponse(
            stream_generator(),
            media_type="application/octet-stream",
            headers=headers,
        )

    else:  # Not downloading, use existing logic for GET_JSON, GET_TEXT, GET_BYTES
        logger.info(f"Action: {params.action}, fetching full content.")

        response = await client.files.content(file_id=openai_file_id)

        match params.action:
            case file_schema.FileContentAction.GET_JSON:
                # client.files.content returns AsyncBinaryAPIResponse which has .json() method
                return response.json()

            case file_schema.FileContentAction.GET_TEXT:
                return PlainTextResponse(content=response.text)

            case file_schema.FileContentAction.GET_BYTES:
                return Response(content=response.content, media_type="application/octet-stream")

            case _:
                logger.error(f"Invalid action specified: {params.action} when not downloading.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid action specified.",
                )
