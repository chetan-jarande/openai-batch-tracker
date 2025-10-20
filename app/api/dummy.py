from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import List
from datetime import datetime, timezone

from app.schemas.batch import OpenAIBatchResponse
from app.schemas.file import OpenAIFileObjectSchema
from tests.utils.mock_data import create_mock_batches, create_mock_files

router = APIRouter(
    responses={404: {"description": "Not found"}},
)

templates = Jinja2Templates(directory="app/templates")


def format_unix_timestamp(value: int, format_str: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    if value is None:
        return "N/A"
    try:
        dt_object = datetime.fromtimestamp(value, tz=timezone.utc)
        return dt_object.strftime(format_str)
    except (TypeError, ValueError) as e:
        return f"Invalid Timestamp: {value}: {str(e)}"


templates.env.filters["unix_ts"] = format_unix_timestamp


@router.get("/view/batches", response_class=HTMLResponse, name="view_dummy_batches")
async def read_dummy_batches(request: Request):
    mock_data = create_mock_batches(25)
    return templates.TemplateResponse(
        "batches_dashboard.html",
        {
            "request": request,
            "batches": mock_data,
            "total_count": len(mock_data),
        },
    )


@router.get("/view/files", response_class=HTMLResponse, name="view_dummy_files")
async def read_dummy_files(request: Request):
    mock_data = create_mock_files(15)
    return templates.TemplateResponse(
        "files_dashboard.html",
        {
            "request": request,
            "files": mock_data,
            "total_count": len(mock_data),
        },
    )


@router.get("/raw/batches", response_model=List[OpenAIBatchResponse])
async def list_batches():
    return create_mock_batches(25)


@router.get("/raw/files", response_model=List[OpenAIFileObjectSchema])
async def list_files():
    return create_mock_files(10)
