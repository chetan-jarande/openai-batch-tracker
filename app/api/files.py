import logging
from typing import List, Optional, Annotated

from fastapi import (
    APIRouter,
    HTTPException,
    status,
    UploadFile,
    File as FastApiFile,
    Query,
    Depends, # TODO: Check if this is needed
)
from openai._exceptions import (
    APIConnectionError,
    RateLimitError,
    APIStatusError,
    NotFoundError as OpenAINotFoundError,
)
from sqlalchemy.exc import SQLAlchemyError

from app.utils.deps import DBSession, OpenAIClientDep
from app.db.models.file import File as DBFileModel
from app.schemas import file as file_schema
from app.schemas import common as common_schema
from app.db.crud.file import create_db_file_record, get_db_file_by_openai_id

logger = logging.getLogger(__name__)

router = APIRouter()

# TODO:
# Future scope:
# - Provide support for multiple files in this endpoint.
#   - doc: https://fastapi.tiangolo.com/tutorial/request-files/#multiple-file-uploads-with-additional-metadata

@router.post(
    "/upload",
    response_model=file_schema.FilePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Upload File to OpenAI and Store Metadata",
    description="Uploads a file to OpenAI and stores its metadata in the local database.",
)
def upload_file_to_openai(
    # The request model for form fields (filename, purpose)
    request_params: file_schema.FileUploadRequest, # = Depends(),  # Use Depends for form data model
    db: DBSession,
    client: OpenAIClientDep,
    file: UploadFile = FastApiFile(
        ...,
        description="The batch input file to upload (e.g., a .jsonl file)."
    ),
) -> file_schema.FilePublic:
    """
    Handles file uploads to OpenAI.
    1.  Receives a file via `UploadFile`.
    2.  Uploads the file to OpenAI using the `openai` client, with given purpose.
    3.  If successful, creates a record of the file in the local PostgreSQL database.
    Doc:
        - OpenAI Files: https://platform.openai.com/docs/api-reference/files/create
        - FAST API UploadFile with params:
            - https://fastapi.tiangolo.com/tutorial/request-files/#uploadfile-with-additional-metadata
            - https://fastapi.tiangolo.com/tutorial/request-forms-and-files/
    Args:
        request_params: Pydantic model for form fields like 'purpose' and 'filename'.
        db: Database session dependency.
        client: OpenAI API client dependency.
        file: The file to be uploaded, provided by FastAPI's `UploadFile`.

    Returns:
        A `FilePublic` schema object representing the stored file record.

    Raises:
        HTTPException:
            - 400 (Bad Request): If the file upload to OpenAI fails for client-side reasons.
            - 409 (Conflict): If a file with the same OpenAI ID already exists in the DB.
            - 500 (Internal Server Error): For OpenAI API errors or database errors.

    """
    # Use the filename from request_params if provided, otherwise from the uploaded file
    effective_filename = request_params.filename or file.filename
    effective_purpose = (
        request_params.purpose
    )  # Purpose from request, defaults to "batch" in schema

    logger.info(
        f"Attempting to upload file: {effective_filename}, content type: {file.content_type}, purpose: {effective_purpose}"
    )

    # TODO: Check if a file with the same name (and potentially content) already exists in OpenAI
    # This is an optional check. For now, we proceed directly to upload.

    try:
        # The `file.file` attribute is a file-like object.
        # OpenAI SDK's `client.files.create` expects a file tuple: (filename, file_object, content_type)
        # or a file-like object directly for the `file` parameter.
        # The `purpose` is hardcoded to "batch" as per requirements.
        uploaded_openai_file = client.files.create(
            file=(
                effective_filename,
                file.file,
                file.content_type
            ),  # Pass as a tuple
            purpose=effective_purpose,
        )
        logger.info(
            f"File '{effective_filename}' uploaded successfully to OpenAI. File ID: {uploaded_openai_file.id}"
        )

    except (APIConnectionError, RateLimitError) as e:
        logger.error(
            f"OpenAI API error during file upload for '{effective_filename}': {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OpenAI API is currently unavailable or rate limit exceeded: {str(e)}",
        )
    except APIStatusError as e:
        logger.error(
            f"OpenAI API status error during file upload for '{effective_filename}': {e}"
        )
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenAI API error: {e.message or str(e)}",
        )
    except Exception as e:
        logger.exception(
            f"Unexpected error during file upload of '{effective_filename}' to OpenAI: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while uploading the file to OpenAI: {str(e)}",
        )
    finally:
        file.file.close()

    file_create_data = file_schema.FileCreate(
        openai_file_id=uploaded_openai_file.id,
        filename=uploaded_openai_file.filename,  # Use filename returned by OpenAI
        bytes_size=uploaded_openai_file.bytes,
        purpose=uploaded_openai_file.purpose,
        status=uploaded_openai_file.status,
        status_details=uploaded_openai_file.status_details,
        openai_created_at=uploaded_openai_file.created_at,
    )

    # Create file record in the database
    db_file_record = create_db_file_record(db, file_create_data)

    return file_schema.FilePublic.model_validate(db_file_record)


@router.get(
    "/openai/list",
    response_model=List[
        file_schema.OpenAIFileObjectSchema
    ],
    summary="List Files from OpenAI Account",
    description="Retrieves a list of files directly from the user's OpenAI account. Supports pagination.",
)
def list_files_from_openai(
    params: file_schema.OpenAIFileListRequestParams,
    client: OpenAIClientDep,
) -> List[file_schema.OpenAIFileObjectSchema]:
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
        Future scope: Sync these files to the local DB.
    """
    logger.info(
        f"Listing files from OpenAI with params: {params.model_dump()}"
    )
    try:
        # Pass parameters from the Pydantic model to the OpenAI client
        # The `model_dump(exclude_none=True)` ensures only provided params are sent
        openai_files_list_page = client.files.list(
            **params.model_dump(exclude_none=True)
        )

        # Validate and convert each FileObject from OpenAI to our Pydantic schema
        # The OpenAI SDK's FileObject should be compatible if our schema is correct.
        # The OpenAI SDK v1.x returns a SyncPage[FileObject] which can be iterated.
        # Each item in `openai_files_list.data` is a `FileObject`.

        response_data = [
            # file_obj.model_dump()  # Directly dump the data if no validation is needed
            file_schema.OpenAIFileObjectSchema.model_validate(file_obj)
            for file_obj in openai_files_list_page.data
        ]
        logger.info(f"Retrieved {len(response_data)} files from OpenAI.")
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


# TODO: create a pydantic model for the OpenAI FileObject
@router.get(
    "/",
    response_model=file_schema.PaginatedFilePublicResponse,
    summary="List Files from Local Database",
    description="Retrieves a paginated list of file records stored in the local database.",
)
def list_files_from_db(
    db: DBSession,
    skip: Annotated[
        int, Query(description="Number of records to skip (for pagination).", ge=0)
    ] = 0,
    limit: Annotated[
        int, Query(description="Maximum number of records to return.", ge=1, le=200)
    ] = 100,
    purpose: Annotated[
        Optional[str], Query(description="Filter by file purpose.")
    ] = None,
    status: Annotated[
        Optional[str], Query(description="Filter by file status.")
    ] = None,
    filename_contains: Annotated[
        Optional[str],
        Query(
            description="Filter by filenames containing this string (case-insensitive)."
        ),
    ] = None,
) -> file_schema.PaginatedFilePublicResponse:
    """
    Retrieves a paginated list of file records from the application's database.

    Args:
        db: Database session dependency.
        skip: Offset for pagination.
        limit: Page size for pagination.
        purpose: Optional filter for file purpose.
        status: Optional filter for file status.
        filename_contains: Optional filter for filename substring match.

    Returns:
        A `PaginatedFilePublicResponse` object containing the list of files and pagination details.
    """
    logger.info(
        f"Listing files from DB with params: skip={skip}, limit={limit}, purpose='{purpose}', status='{status}', filename_contains='{filename_contains}'"
    )
    try:
        query = db.query(DBFileModel)

        if purpose:
            query = query.filter(DBFileModel.purpose == purpose)
        if status:
            query = query.filter(DBFileModel.status == status)
        if filename_contains:
            query = query.filter(
                DBFileModel.filename.ilike(f"%{filename_contains}%")
            )  # Case-insensitive search

        total_count = query.count()
        db_files = (
            query.order_by(DBFileModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        logger.info(
            f"Retrieved {len(db_files)} file records from DB (total matching: {total_count})."
        )

        return file_schema.PaginatedFilePublicResponse(
            count=total_count,
            limit=limit,
            offset=skip,
            items=[
                file_schema.FilePublic.model_validate(db_file) for db_file in db_files
            ],
        )
    except SQLAlchemyError as e:
        logger.exception(f"Database error listing files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve files from the database.",
        )


@router.get(
    "/{openai_file_id}",
    response_model=file_schema.FilePublic,
    summary="Retrieve File Details from Local Database",
    description="Retrieves details of a specific file record from the local database using its OpenAI File ID.",
)
def retrieve_file_from_db(openai_file_id: str, db: DBSession) -> file_schema.FilePublic:
    """
    Retrieves a specific file record from the database by its OpenAI File ID.

    Args:
        openai_file_id: The OpenAI File ID of the file to retrieve.
        db: Database session dependency.

    Returns:
        A `FilePublic` schema object if the file is found.

    Raises:
        HTTPException: 404 (Not Found) if the file record does not exist in the database.
                       500 (Internal Server Error) for other database errors.
    """
    logger.info(f"Retrieving file record from DB for OpenAI File ID: {openai_file_id}")
    try:
        db_file = get_db_file_by_openai_id(db, openai_file_id)
        if not db_file:
            logger.warning(
                f"File record with OpenAI File ID '{openai_file_id}' not found in DB."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with OpenAI ID '{openai_file_id}' not found in the local database.",
            )
        logger.info(f"File record found in DB for OpenAI File ID: {openai_file_id}")
        return file_schema.FilePublic.model_validate(db_file)
    except SQLAlchemyError as e:
        logger.exception(f"Database error retrieving file {openai_file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve file {openai_file_id} from the database.",
        )


@router.delete(
    "/{openai_file_id}",
    response_model=common_schema.Msg,
    summary="Delete File from OpenAI and Local Database",
    description="Deletes a file from OpenAI's servers and then removes its record from the local database.",
)
def delete_openai_file_and_record(
    openai_file_id: str,
    db: DBSession,
    client: OpenAIClientDep,
) -> common_schema.Msg:
    """
    Deletes a file from both OpenAI and the local database.

    1.  Attempts to delete the file from OpenAI using its `openai_file_id`.
    2.  If successful (or if the file is already not found on OpenAI),
        deletes the corresponding record from the local database.

    Args:
        openai_file_id: The OpenAI File ID of the file to delete.
        db: Database session dependency.
        client: OpenAI API client dependency.

    Returns:
        A `Msg` schema object indicating the result of the operation.

    Raises:
        HTTPException:
            - 404 (Not Found): If the file record is not found in the local DB (and couldn't be deleted from OpenAI).
            - 500 (Internal Server Error): For OpenAI API errors or database errors.
            - 503 (Service Unavailable): If OpenAI API is unavailable.
    """
    logger.info(f"Attempting to delete file with OpenAI ID: {openai_file_id}")

    # Step 1: Attempt to delete from OpenAI
    try:
        openai_delete_response = client.files.delete(file_id=openai_file_id)
        if openai_delete_response.deleted:
            logger.info(f"File {openai_file_id} successfully deleted from OpenAI.")
        else:
            # This case might not happen if delete always raises error or returns deleted=True
            logger.warning(
                f"OpenAI reported file {openai_file_id} as not deleted, but no error raised. Response: {openai_delete_response}"
            )
            # We might still proceed to delete from DB if that's the desired behavior.

    except OpenAINotFoundError:
        logger.warning(
            f"File {openai_file_id} not found on OpenAI. It might have been already deleted."
        )
        # Proceed to delete from DB if it exists there.
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
            logger.warning(
                f"File {openai_file_id} not found on OpenAI (APIStatusError 404)."
            )
        else:
            raise HTTPException(
                status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OpenAI API error: {e.message or str(e)}",
            )
    except Exception as e:
        logger.exception(
            f"Unexpected error deleting file {openai_file_id} from OpenAI: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while deleting the file from OpenAI: {str(e)}",
        )

    # Step 2: Delete from local database
    db_file = get_db_file_by_openai_id(db, openai_file_id)
    if not db_file:
        # If it wasn't found on OpenAI and also not in DB, it's effectively gone.
        logger.warning(
            f"File record for OpenAI ID {openai_file_id} not found in local DB. Nothing to delete from DB."
        )
        # Depending on strictness, you could return 404 here if it was expected to be in DB.
        # However, if OpenAI deletion was the primary goal and it's gone, this might be OK.
        # For consistency, if the intent is to delete something that should exist, a 404 is appropriate.
        # But if client.files.delete succeeded or confirmed not found, we might just say it's done.
        # Let's assume if it's not in DB, it's fine if OpenAI also confirmed it's gone.
        return common_schema.Msg(
            message=f"File {openai_file_id} not found in local DB; confirmed deleted or not found on OpenAI."
        )

    try:
        db.delete(db_file)
        db.commit()
        logger.info(
            f"File record for OpenAI ID {openai_file_id} (DB ID: {db_file.id}) deleted successfully from local database."
        )
        return common_schema.Msg(
            message=f"File {openai_file_id} and its DB record deleted successfully."
        )
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(
            f"Database error deleting file record for OpenAI ID {openai_file_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete file record {openai_file_id} from the database after OpenAI deletion.",
        )
