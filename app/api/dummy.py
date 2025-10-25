from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import List

from app.schemas.batch import OpenAIBatchResponse
from app.schemas.file import OpenAIFileObjectSchema
from app.utils.common import format_unix_timestamp
from app.utils.mock_data import create_mock_batches, create_mock_files

router = APIRouter(
    responses={404: {"description": "Not found"}},
)

templates = Jinja2Templates(directory="app/templates")


templates.env.filters["unix_ts"] = format_unix_timestamp


@router.get(
    "/view/batches",
    response_class=HTMLResponse,
    name="view_dummy_batches",
    operation_id="view_dummy_batches",
)
async def read_dummy_batches(request: Request):
    mock_data = create_mock_batches(25)
    return templates.TemplateResponse(
        request,
        "batches_dashboard.html",
        {
            "batches": mock_data,
            "total_count": len(mock_data),
        },
    )


@router.get(
    "/view/files",
    response_class=HTMLResponse,
    name="view_dummy_files",
    operation_id="view_dummy_files",
)
async def read_dummy_files(request: Request):
    mock_data = create_mock_files(15)
    return templates.TemplateResponse(
        request,
        "files_dashboard.html",
        {
            "files": mock_data,
            "total_count": len(mock_data),
        },
    )


@router.get(
    "/raw/batches",
    response_model=List[OpenAIBatchResponse],
    operation_id="list_dummy_batches",
)
async def list_batches():
    return create_mock_batches(25)


@router.get(
    "/raw/files",
    response_model=List[OpenAIFileObjectSchema],
    operation_id="list_dummy_files",
)
async def list_files():
    return create_mock_files(10)
