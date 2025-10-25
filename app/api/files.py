from typing import Any, AsyncGenerator
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

from openai._exceptions import (
    APIConnectionError,
    RateLimitError,
    APIStatusError,
    NotFoundError as OpenAINotFoundError,
)
from openai._streaming import (
    Stream as OpenAIStream,
)
from openai import HttpxBinaryResponseContent

from app.schemas import file as file_schema
from app.utils.common import format_unix_timestamp
from app.utils.deps import OpenAIClient
from app.utils.logging_config import get_logger


logger = get_logger(__name__)

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["unix_ts"] = format_unix_timestamp


# TODO:
# Future scope:
# - Provide support for multiple files in this endpoint.
#   - doc: https://fastapi.tiangolo.com/tutorial/request-files/#multiple-file-uploads-with-additional-metadata


@router.post(
    "/upload",
    response_model=file_schema.OpenAIFileObjectSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Upload File to OpenAI",
    operation_id="upload_openai_file",
    description="Uploads a file to OpenAI<br/>More details in Doc: https://platform.openai.com/docs/api-reference/files/create",
)
def upload_file_to_openai(
    client: OpenAIClient,
    file: UploadFile = FastApiFile(..., description="The batch input file to upload (e.g., a .jsonl file)."),
    request_params: file_schema.FileUploadRequest = Depends(),
) -> file_schema.OpenAIFileObjectSchema:
    """
    Handles file uploads to OpenAI.
    1.  Receives a file via `UploadFile`.
    2.  Uploads the file to OpenAI using the `openai` client, with given purpose.
    Doc:
        - OpenAI Files: https://platform.openai.com/docs/api-reference/files/create
        - FAST API UploadFile with params:
            - https://fastapi.tiangolo.com/tutorial/request-files/#uploadfile-with-additional-metadata
            - https://fastapi.tiangolo.com/tutorial/request-forms-and-files/
    Args:
        request_params: Pydantic model for form fields like 'purpose' and 'filename'.
        client: OpenAI API client dependency.
        file: The file to be uploaded, provided by FastAPI's `UploadFile`.

    Returns:
        A `OpenAIFileObjectSchema` schema object representing the stored file record.

    Raises:
        HTTPException:
            - 400 (Bad Request): If the file upload to OpenAI fails for client-side reasons.
            - 500 (Internal Server Error): For OpenAI API errors.

    """
    # Use the filename from request_params if provided, otherwise from the uploaded file
    purpose = request_params.purpose

    logger.info(f"Attempting to upload file: {file.filename}, content type: {file.content_type}, purpose: {purpose}")

    # TODO: Check if a file with the same name (and potentially content) already exists in OpenAI
    # This is an optional check. For now, we proceed directly to upload.

    try:
        # The `file.file` attribute is a file-like object.
        # OpenAI SDK's `client.files.create` expects a file tuple: (filename, file_object, content_type)
        # or a file-like object directly for the `file` parameter.
        uploaded_openai_file = client.files.create(
            file=(file.filename, file.file, file.content_type),  # Pass as a tuple
            # OR
            # file=open(file.filename, "rb")
            purpose=purpose,
        )
        logger.info(f"File '{file.filename}' uploaded successfully to OpenAI. File ID: {uploaded_openai_file.id}")
        return JSONResponse(
            uploaded_openai_file,
            status_code=status.HTTP_201_CREATED,
        )
    except (APIConnectionError, RateLimitError) as e:
        logger.error(f"OpenAI API error during file upload for '{file.filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OpenAI API is currently unavailable or rate limit exceeded: {str(e)}",
        )
    except APIStatusError as e:
        logger.error(f"OpenAI API status error during file upload for '{file.filename}': {e}")
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenAI API error: {e.message or str(e)}",
        )
    except Exception as e:
        logger.exception(f"Unexpected error during file upload of '{file.filename}' to OpenAI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while uploading the file to OpenAI: {str(e)}",
        )
    finally:
        file.file.close()


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

    try:
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

    except (APIConnectionError, RateLimitError) as e:
        logger.error(f"OpenAI API error during listing files: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OpenAI API is currently unavailable or rate limit exceeded: {str(e)}",
        )
    except APIStatusError as e:
        logger.error(f"OpenAI API status error during listing files: {e}")
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenAI API error: {e.message or str(e)}",
        )
    except Exception as e:
        logger.exception(f"Unexpected error listing files from OpenAI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while listing files from OpenAI: {str(e)}",
        )


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
    try:
        openai_file = client.files.retrieve(file_id=openai_file_id)
        if not openai_file:
            logger.warning(f"File record with OpenAI File ID '{openai_file_id}' not found in OpenAI.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with OpenAI ID '{openai_file_id}' not found.",
            )
        logger.info(f"File record found for OpenAI File ID: {openai_file_id}")
        return file_schema.OpenAIFileObjectSchema.model_validate(openai_file)
    except Exception as e:
        logger.exception(f"Error retrieving file {openai_file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve file {openai_file_id} from the OpenAI. Details: {str(e)}",
        )


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

    try:
        openai_delete_response = client.files.delete(file_id=openai_file_id)
        if openai_delete_response.deleted:
            logger.info(f"File {openai_file_id} successfully deleted from OpenAI.")
        else:
            # This case might not happen if delete always raises error or returns deleted=True
            logger.warning(
                f"OpenAI reported file {openai_file_id} as not deleted, but no error raised. Response: {openai_delete_response}"
            )
        return JSONResponse(openai_delete_response.model_dump(), status_code=status.HTTP_200_OK)

    except OpenAINotFoundError:
        logger.warning(f"File {openai_file_id} not found on OpenAI. It might have been already deleted.")
    except (APIConnectionError, RateLimitError) as e:
        logger.error(f"OpenAI API error deleting file {openai_file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OpenAI API error while deleting file: {str(e)}",
        )
    except APIStatusError as e:
        logger.error(f"OpenAI API status error deleting file {openai_file_id}: {e}")
        # If it's a 404, we can treat it like OpenAINotFoundError
        if e.status_code == 404:
            logger.warning(f"File {openai_file_id} not found on OpenAI (APIStatusError 404).")
        else:
            raise HTTPException(
                status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OpenAI API error: {str(e)}",
            )
    except Exception as e:
        logger.exception(f"Unexpected error deleting file {openai_file_id} from OpenAI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while deleting the file from OpenAI: {str(e)}",
        )


# Retrieve file content
# # Doc from Batches -> https://platform.openai.com/docs/guides/batch#5-retrieve-the-results
# TODO: Replace this API with v2 API versions
@router.get(
    "content/v1/{openai_file_id}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve File Details from OpenAI",
    operation_id="get_openai_file_content_v1",
    description=(
        "Retrieves details of a specific file from OpenAI using its OpenAI File ID. returns the file content as JSON.</br>"
        "See the [OpenAI Retrieve File Content API docs](https://platform.openai.com/docs/api-reference/files/retrieve-contents) for details."
    ),
)
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
    try:
        content: HttpxBinaryResponseContent = client.files.content(file_id=openai_file_id)
        # TODO: Future scope:
        # since it returns the file content, we need to check what type of content it is, based on investigation we found out that
        # it returns `HttpxBinaryResponseContent`, but that class has the property of writing content into a given file as well.
        # using client.files.content(file_id=openai_file_id).write_to_file(file: str | PathLike[str])
        #   - here we need to use the  pathlib.Path type of values as inputs
        # it also have other methods like:
        #    - json(), content(), text(), bytes(), etc
        # create a datamodel to accept this pathlike input, methods in which they need there data to be return back to client
        if not content:
            logger.warning(
                f"The File with OpenAI File ID '{openai_file_id}' not found in OpenAI nor it has any content."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with OpenAI ID '{openai_file_id}' not found.",
            )
        logger.info(f"File record found for OpenAI File ID: {openai_file_id}")
        return content.json()
    except Exception as e:
        logger.exception(f"Error retrieving file {openai_file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve file {openai_file_id} from the OpenAI.",
        )


# TODO:
# Future scope:
# - Minimize the code duplication in exceptions handling
# - Add support for downloading file content as a stream using async openAI client
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
async def retrieve_file_content_from_openai_v2(
    client: OpenAIClient,
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

        openai_sdk_stream: OpenAIStream[bytes] | None = None
        try:
            # Use with_streaming_response for true streaming from OpenAI
            openai_sdk_stream = client.with_streaming_response.files.content(file_id=openai_file_id)

            async def file_content_generator() -> AsyncGenerator[bytes, None]:
                try:
                    async for chunk in openai_sdk_stream:  # Iterate directly over the OpenAIStream
                        yield chunk
                finally:
                    if openai_sdk_stream:  # Ensure stream exists before trying to close
                        await openai_sdk_stream.close()
                        logger.debug(f"OpenAI SDK stream for download {openai_file_id} closed by generator.")

            download_filename = params.download_as if params.download_as.strip() else f"{openai_file_id}_content.dat"
            headers = {"Content-Disposition": f'attachment; filename="{download_filename}"'}
            return StreamingResponse(
                file_content_generator(),
                media_type="application/octet-stream",
                headers=headers,
            )

        except OpenAINotFoundError:
            logger.warning(f"File with OpenAI File ID '{openai_file_id}' not found on OpenAI for download.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with OpenAI ID '{openai_file_id}' not found on OpenAI.",
            )
        except (APIConnectionError, RateLimitError) as e:
            logger.error(f"OpenAI API error setting up download stream for {openai_file_id}: {e}")
            if openai_sdk_stream:
                await openai_sdk_stream.close()  # Attempt to close if stream was obtained
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"OpenAI API error: {str(e)}",
            )
        except APIStatusError as e:
            logger.error(f"OpenAI API status error setting up download stream for {openai_file_id}: {e}")
            if openai_sdk_stream:
                await openai_sdk_stream.close()
            raise HTTPException(
                status_code=e.status_code or 500,
                detail=f"OpenAI API error: {e.message or str(e)}",
            )
        except Exception as e:
            logger.exception(f"Error setting up stream for download for file {openai_file_id}: {e}")
            if openai_sdk_stream:
                await openai_sdk_stream.close()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error preparing file for download: {str(e)}",
            )

    else:  # Not downloading, use existing logic for GET_JSON, GET_TEXT, GET_BYTES
        logger.info(f"Action: {params.action}, fetching full content.")
        binary_response_obj: HttpxBinaryResponseContent | None = None
        try:
            binary_response_obj = client.files.content(file_id=openai_file_id)

            if params.action == file_schema.FileContentAction.GET_JSON:
                try:
                    json_content = binary_response_obj.json()
                    logger.info(f"Returning JSON content for file {openai_file_id}.")
                    return json_content
                except Exception as e_json:
                    logger.exception(f"Error parsing JSON content for file {openai_file_id}: {e_json}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to parse file content as JSON: {str(e_json)}",
                    )

            elif params.action == file_schema.FileContentAction.GET_TEXT:
                try:
                    text_content = binary_response_obj.text
                    logger.info(f"Returning text content for file {openai_file_id}.")
                    return PlainTextResponse(content=text_content)
                except Exception as e_text:
                    logger.exception(f"Error decoding text content for file {openai_file_id}: {e_text}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to decode file content as text: {str(e_text)}",
                    )

            elif params.action == file_schema.FileContentAction.GET_BYTES:
                try:
                    byte_content = binary_response_obj.content
                    logger.info(f"Returning byte content for file {openai_file_id}.")
                    return Response(content=byte_content, media_type="application/octet-stream")
                except Exception as e_bytes:
                    logger.exception(f"Error getting byte content for file {openai_file_id}: {e_bytes}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to get file content as bytes: {str(e_bytes)}",
                    )

            else:  # Should be caught by Pydantic if action is invalid
                logger.error(f"Invalid action specified: {params.action} when not downloading.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid action specified.",
                )

        except OpenAINotFoundError:
            logger.warning(
                f"File with OpenAI File ID '{openai_file_id}' not found on OpenAI for action {params.action}."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with OpenAI ID '{openai_file_id}' not found on OpenAI.",
            )
        except (APIConnectionError, RateLimitError) as e:
            logger.error(
                f"OpenAI API error retrieving content for file {openai_file_id} (action: {params.action}): {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"OpenAI API error: {str(e)}",
            )
        except APIStatusError as e:
            logger.error(
                f"OpenAI API status error retrieving content for file {openai_file_id} (action: {params.action}): {e}"
            )
            raise HTTPException(
                status_code=e.status_code or 500,
                detail=f"OpenAI API error: {e.message or str(e)}",
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error retrieving content for file {openai_file_id} (action: {params.action}): {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred: {str(e)}",
            )
        finally:
            if binary_response_obj and hasattr(binary_response_obj, "aclose"):
                try:
                    await binary_response_obj.aclose()
                    logger.debug(f"OpenAI HttpxBinaryResponseContent for {openai_file_id} closed asynchronously.")
                except Exception as e_close:
                    logger.warning(f"Error closing HttpxBinaryResponseContent for {openai_file_id}: {e_close}")
