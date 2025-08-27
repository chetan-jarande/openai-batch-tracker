import logging
from typing import List, Optional, Annotated, Any, AsyncGenerator
from pathlib import Path

from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,  # TODO: Check if this is needed
)
from fastapi.responses import (
    Response,
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
)

from openai._exceptions import (
    APIError,
    APIConnectionError,
    RateLimitError,
    NotFoundError as OpenAINotFoundError,
)
from openai import OpenAI, AsyncOpenAI

from openai import HttpxBinaryResponseContent
from openai.types import Batch as OpenAIBatch
from app.utils.deps import OpenAIClient
from app.schemas import batch as batch_schema

logger = logging.getLogger(__name__)

router = APIRouter()


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
    description="Create a new OpenAI batch of requests.",
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
    summary="Retrieve OpenAI Batch Status",
    description="Fetch details of a specific OpenAI batch.",
)
def retrieve_batch(
    batch_id: str,
    openai_client: OpenAIClient,
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
    summary="Cancel OpenAI Batch",
    description="Cancel an in-progress OpenAI batch.",
)
def cancel_batch(
    batch_id: str,
    openai_client: OpenAIClient,
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
        logger.exception("Unexpected error in cancel_batch")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/list-batches",
    response_model=batch_schema.ListBatchesResponse,
    summary="List OpenAI Batches",
    description="Return a paginated list of your organization’s OpenAI batches.",
)
def list_batches(
    params: batch_schema.ListBatchesRequestParams,
    openai_client: OpenAIClient,
) -> batch_schema.ListBatchesResponse:
    """
    List OpenAI batches with optional pagination.
    """
    try:
        response = openai_client.batches.list(after=params.after, limit=params.limit)
        # Convert each raw batch into our response model
        batches = [batch_schema.OpenAIBatchResponse(**item) for item in response.get("data", [])]
        return batch_schema.ListBatchesResponse(
            object=response.get("object", "list"),
            data=batches,
            first_id=response.get("first_id"),
            last_id=response.get("last_id"),
            has_more=response.get("has_more", False),
        )

    except (APIConnectionError, RateLimitError) as e:
        logger.error(f"OpenAI API error while listing batches: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except APIError as e:
        logger.error(f"OpenAI returned error: {e}")
        status_code = getattr(e, "http_status", status.HTTP_500_INTERNAL_SERVER_ERROR)
        message = getattr(e, "error", {}).get("message", str(e))
        raise HTTPException(status_code=status_code, detail=message)
    except Exception as e:
        logger.exception("Unexpected error in list_batches")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
