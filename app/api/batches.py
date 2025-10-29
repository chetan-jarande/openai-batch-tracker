from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    status,
    Path,
    Depends,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from openai._exceptions import (
    APIError,
    APIConnectionError,
    RateLimitError,
    NotFoundError as OpenAINotFoundError,
)

from app.schemas import batch as batch_schema
from app.utils.common import format_unix_timestamp
from app.utils.deps import OpenAIClient
from app.utils.logging_config import get_logger


logger = get_logger(__name__)

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["unix_ts"] = format_unix_timestamp


# # Docs:
# # About Batches
# # - Guide Doc: https://platform.openai.com/docs/guides/batch
# # - API References: https://platform.openai.com/docs/api-reference/batch
# # About Files:
# # - API References: https://platform.openai.com/docs/api-reference/files


@router.post(
    "/create",
    response_model=batch_schema.OpenAIBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create OpenAI Batch",
    operation_id="create_openai_batch",
    description=(
        "Create a new OpenAI batch of requests.</br>"
        "See the [OpenAI Batch API docs](https://platform.openai.com/docs/api-reference/batch/create) for details."
    ),
)
def create_batch(
    batch: batch_schema.OpenAIBatchCreate,
    openai_client: OpenAIClient,
) -> batch_schema.OpenAIBatchResponse:
    """
    Create a new OpenAI batch.

    Uses the OpenAI Python library to submit a batch job based on the provided input file and parameters.
    """
    try:
        response = openai_client.batches.create(
            input_file_id=batch.input_file_id,
            endpoint=batch.endpoint,
            completion_window=batch.completion_window,
            metadata=batch.metadata or {},
        )
        logger.info(f"OpenAI batch created: {response['id']}")
        return batch_schema.OpenAIBatchResponse(**response)

    except (APIConnectionError, RateLimitError) as e:
        logger.error(f"OpenAI API error while creating batch: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except APIError as e:
        logger.error(f"OpenAI returned error: {e}")
        status_code = getattr(e, "http_status", status.HTTP_500_INTERNAL_SERVER_ERROR)
        raise HTTPException(status_code=status_code, detail=e.error.get("message", str(e)))
    except Exception as e:
        logger.exception("Unexpected error in create_batch")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/{batch_id}",
    response_model=batch_schema.OpenAIBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve OpenAI Batch Status",
    operation_id="get_openai_batch_details",
    description="Fetch details of a specific OpenAI batch.",
)
def retrieve_batch(
    openai_client: OpenAIClient,
    batch_id: str = Path(
        ...,
        description="The ID of the OpenAI batch to retrieve.",
        examples=["batch-abc123"],
        min_length=1,
    ),
) -> batch_schema.OpenAIBatchResponse:
    """
    Retrieve an OpenAI batch by ID.
    """
    try:
        response = openai_client.batches.retrieve(batch_id=batch_id)
        logger.info(f"Retrieved OpenAI batch: {batch_id}")
        return batch_schema.OpenAIBatchResponse(**response)

    except OpenAINotFoundError as e:
        logger.warning(f"Batch not found: {batch_id} - {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (APIConnectionError, RateLimitError) as e:
        logger.error(f"OpenAI API error while retrieving batch {batch_id}: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except APIError as e:
        logger.error(f"OpenAI returned error: {e}")
        status_code = getattr(e, "http_status", status.HTTP_500_INTERNAL_SERVER_ERROR)
        message = getattr(e, "error", {}).get("message", str(e))
        raise HTTPException(status_code=status_code, detail=message)
    except Exception as e:
        logger.exception("Unexpected error in retrieve_batch")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/{batch_id}/cancel",
    response_model=batch_schema.OpenAIBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel OpenAI Batch",
    operation_id="cancel_openai_batch",
    description=(
        "Cancel an in-progress OpenAI batch.</br>"
        "See the [OpenAI Batch API docs](https://platform.openai.com/docs/api-reference/batch/cancel) for details."
    ),
)
def cancel_batch(
    openai_client: OpenAIClient,
    batch_id: str = Path(
        ...,
        description="The ID of the OpenAI batch to cancel.",
        examples=["batch-abc123"],
        min_length=1,
    ),
) -> batch_schema.OpenAIBatchResponse:
    """
    Cancel a running OpenAI batch by ID.
    """
    try:
        response = openai_client.batches.cancel(batch_id=batch_id)
        logger.info(f"Cancelled OpenAI batch: {batch_id}")
        return batch_schema.OpenAIBatchResponse(**response)

    except OpenAINotFoundError as e:
        logger.warning(f"Batch not found or cannot cancel: {batch_id} - {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (APIConnectionError, RateLimitError) as e:
        logger.error(f"OpenAI API error while cancelling batch {batch_id}: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except APIError as e:
        logger.error(f"OpenAI returned error: {e}")
        status_code = getattr(e, "http_status", status.HTTP_500_INTERNAL_SERVER_ERROR)
        message = getattr(e, "error", {}).get("message", str(e))
        raise HTTPException(status_code=status_code, detail=message)
    except Exception as e:
        logger.exception(f"Unexpected error in cancel_batch {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


def get_openai_batch_list(
    openai_client: OpenAIClient,
    data: batch_schema.ListBatchesRequestParams,
) -> dict | batch_schema.ListBatchesResponse:
    """
    List OpenAI batches with optional pagination.
    Defaults to 20 batches if no limit is specified.
    params:
    data: Pydantic model containing 'after' and 'limit' parameters.
    Returns:
        A dictionary representing the paginated list of OpenAI batches.
    """
    try:
        params = data.model_dump()
        response = openai_client.batches.list(after=params.get("after"), limit=params.get("limit", 20))

        return response

    except (APIConnectionError, RateLimitError) as e:
        logger.exception(f"OpenAI API error while listing batches: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except APIError as e:
        logger.exception(f"OpenAI returned error: {e}")
        status_code = getattr(e, "http_status", status.HTTP_500_INTERNAL_SERVER_ERROR)
        message = getattr(e, "error", {}).get("message", str(e))
        raise HTTPException(status_code=status_code, detail=message)
    except Exception as e:
        logger.exception("Unexpected error in list_batches")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/list",
    response_model=batch_schema.ListBatchesResponse,
    status_code=status.HTTP_200_OK,
    summary="List OpenAI Batches",
    operation_id="list_openai_batches",
    description=(
        "Return a paginated list of your organization’s OpenAI batches.</br>"
        "See the [OpenAI Batch API docs](https://platform.openai.com/docs/api-reference/batch/list) for details."
    ),
)
def list_batches(
    openai_client: OpenAIClient,
    params: batch_schema.ListBatchesRequestParams = Depends(),
) -> batch_schema.ListBatchesResponse:
    """
    List OpenAI batches with optional pagination.
    """
    response = get_openai_batch_list(openai_client, params)
    batches = [batch_schema.OpenAIBatchResponse(**item) for item in response.get("data", [])]

    return batch_schema.ListBatchesResponse(
        object=response.get("object", "list"),
        data=batches,
        first_id=response.get("first_id"),
        last_id=response.get("last_id"),
        has_more=response.get("has_more", False),
    )


@router.get(
    "/view/list",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    summary="View OpenAI Batch Dashboard",
    operation_id="view_openai_batches_dashboard",
    description=(
        "Return an HTML dashboard view of your organization’s OpenAI batches.</br>"
        "A paginated list of your organization’s OpenAI batches.</br>"
        "See the [OpenAI Batch API docs](https://platform.openai.com/docs/api-reference/batch/list) for details."
    ),
)
def view_batch_dashboard(
    request: Request,
    openai_client: OpenAIClient,
    params: batch_schema.ListBatchesRequestParams = Depends(),
) -> HTMLResponse:
    """
    Return an HTML dashboard view of OpenAI batches with optional pagination.
    """
    response = get_openai_batch_list(openai_client, params)
    batches = [batch_schema.OpenAIBatchResponse(**item) for item in response.get("data", [])]

    return templates.TemplateResponse(
        request,
        "batches_dashboard.html",
        {
            "batches": batches,
            "total_count": len(batches),
            "params": params,
            "first_id": response.get("first_id"),
            "last_id": response.get("last_id"),
            "has_more": response.get("has_more", False),
        },
    )
