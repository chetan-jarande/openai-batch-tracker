import random
import time
from typing import List, Optional, Dict
from functools import partial
from random import choice, randint

from app.schemas.batch import (
    OpenAIBatchResponse,
    OpenAIBatchStatus,
    OpenAIError,
    RequestCounts,
    BatchEndpoint,
    OpenAIUsage,
)
from app.schemas.file import OpenAIFileObjectSchema, OpenAIFilePurpose

# --- Data Sets for Mocking ---
BATCH_ID_PREFIXES = ["batch_abc", "batch_def", "batch_xyz"]
FILE_ID_PREFIXES = ["file_in", "file_out", "file_err"]
ERROR_CODES = ["400", "429", "500", "503"]
ERROR_MESSAGES = [
    "Invalid request",
    "Rate limit exceeded",
    "Internal server error",
    "Service unavailable",
]
METADATA_KEYS = ["customer_id", "batch_description", "priority", "region"]
METADATA_VALUES = ["user_123", "nightly_job", "high", "us-east-1"]
ERROR_PARAMS = ["model", "prompt", "max_tokens", "temperature", "n"]


# --- Partial Functions for Random Data Generation ---
def generate_random_string(prefixes: List[str], suffix_len: int = 6) -> str:
    """Generates a random string with a given prefix."""
    return f"{choice(prefixes)}_{''.join(random.choices('0123456789abcdef', k=suffix_len))}"


get_random_batch_id = partial(generate_random_string, prefixes=BATCH_ID_PREFIXES)
get_random_file_id = partial(generate_random_string, prefixes=FILE_ID_PREFIXES)
get_random_status = partial(choice, list(OpenAIBatchStatus))
get_random_endpoint = partial(choice, list(BatchEndpoint))
get_random_error_code = partial(choice, ERROR_CODES)
get_random_error_message = partial(choice, ERROR_MESSAGES)
get_random_error_param = partial(choice, ERROR_PARAMS)
get_random_file_purpose = partial(
    choice,
    [
        OpenAIFilePurpose.BATCH,
        OpenAIFilePurpose.FINE_TUNE,
        OpenAIFilePurpose.ASSISTANTS,
    ],
)
get_random_file_status = partial(choice, ["uploaded", "processed", "error"])


def get_random_metadata():
    return {choice(METADATA_KEYS): choice(METADATA_VALUES) for _ in range(randint(1, 4))}


def create_mock_error() -> Optional[Dict]:
    """Creates a mock error object, with a chance of being None."""
    if random.random() > 0.7:
        return None
    return {
        "data": [
            OpenAIError(
                code=get_random_error_code(),
                message=get_random_error_message(),
                param=get_random_error_param(),
                line=randint(1, 100),
            )
        ]
    }


def _get_batch_usage() -> OpenAIUsage:
    prompt_tokens = randint(1000, 5000)
    completion_tokens = randint(1000, 5000)
    total_tokens = prompt_tokens + completion_tokens
    return OpenAIUsage(
        input_tokens=prompt_tokens,
        input_tokens_details={"cached_tokens": randint(400, 800)},
        output_tokens=completion_tokens,
        output_tokens_details={"reasoning_tokens": randint(200, 400)},
        total_tokens=total_tokens,
    )


def create_mock_request_counts(status: OpenAIBatchStatus) -> RequestCounts:
    """Creates mock request counts based on the batch status."""
    total = 100
    if status == OpenAIBatchStatus.COMPLETED:
        completed = randint(95, 100)
        failed = total - completed
    elif status == OpenAIBatchStatus.FAILED:
        completed = randint(0, 80)
        failed = total - completed
    elif status in [OpenAIBatchStatus.IN_PROGRESS, OpenAIBatchStatus.FINALIZING]:
        completed = randint(0, 50)
        failed = randint(0, 5)
    else:
        completed = 0
        failed = 0
    return RequestCounts(total=total, completed=completed, failed=failed)


def create_mock_batches(count: int = 15) -> List[OpenAIBatchResponse]:
    """Generates a list of varied mock batch data using partials."""
    mock_batches = []
    now_unix = int(time.time())

    for _ in range(count):
        status = get_random_status()
        created_unix = now_unix - randint(3600, 86400 * 5)

        completed_at = None
        failed_at = None
        cancelled_at = None

        if status == OpenAIBatchStatus.COMPLETED:
            completed_at = created_unix + randint(600, 18 * 3600)
        elif status == OpenAIBatchStatus.FAILED:
            failed_at = created_unix + randint(600, 18 * 3600)
        elif status == OpenAIBatchStatus.CANCELLED:
            cancelled_at = created_unix + randint(600, 18 * 3600)

        mock_batches.append(
            OpenAIBatchResponse(
                id=get_random_batch_id(),
                object="batch",
                endpoint=get_random_endpoint(),
                errors=create_mock_error(),
                input_file_id=get_random_file_id(),
                completion_window="24h",
                status=status,
                output_file_id=get_random_file_id() if status == OpenAIBatchStatus.COMPLETED else None,
                error_file_id=get_random_file_id() if status == OpenAIBatchStatus.FAILED else None,
                created_at=created_unix,
                in_progress_at=created_unix + 60
                if status
                in [
                    OpenAIBatchStatus.IN_PROGRESS,
                    OpenAIBatchStatus.FINALIZING,
                    OpenAIBatchStatus.COMPLETED,
                    OpenAIBatchStatus.FAILED,
                ]
                else None,
                expires_at=created_unix + 24 * 3600,
                finalizing_at=completed_at - 60 if status == OpenAIBatchStatus.COMPLETED else None,
                completed_at=completed_at,
                failed_at=failed_at,
                expired_at=None,
                cancelling_at=None,
                cancelled_at=cancelled_at,
                request_counts=create_mock_request_counts(status),
                usage=_get_batch_usage(),
                metadata=get_random_metadata() if random.random() > 0.5 else None,
            )
        )
    return mock_batches


def create_mock_files(count: int = 10) -> List[OpenAIFileObjectSchema]:
    """Generates a list of mock file data."""
    mock_files = []
    now_unix = int(time.time())

    for i in range(1, count + 1):
        mock_files.append(
            OpenAIFileObjectSchema(
                id=get_random_file_id(),
                object="file",
                bytes=randint(1000, 50000),
                created_at=now_unix - randint(3600, 86400 * 5),
                filename=f"mock_file_{i}.jsonl",
                purpose=get_random_file_purpose(),
                status=get_random_file_status(),
            )
        )
    return mock_files
