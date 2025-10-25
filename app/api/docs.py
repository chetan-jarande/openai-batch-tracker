from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import markdown2

from app.utils.common import find_project_root
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# Dynamically determine the project root directory
PROJECT_ROOT = find_project_root()
DOCS_DIRECTORY = PROJECT_ROOT / "docs"
LICENSE_FILENAME = "LICENSE"
README_FILENAME = "README.md"
DEFAULT_FILES = [LICENSE_FILENAME, README_FILENAME]
MARKDOWN_EXTRAS = ["fenced-code-blocks", "tables", "header-ids"]


@router.get(
    "/",
    response_class=HTMLResponse,
    name="view_docs_list",
    summary="List Documentation Files",
    operation_id="list_docs",
    description="Retrieves a list of available Markdown documents from the `/docs` directory and includes a link to the project's LICENSE file.",
)
async def list_docs(request: Request):
    """
    Serves a page that lists all available Markdown documents.

    This endpoint scans the project's `/docs` directory for `.md` files
    and also includes static entries for the `LICENSE` and `README.md` files,
    presenting them as a list of links for the user to view.
    """
    try:
        # Use pathlib to iterate and filter files
        md_files = [f.name for f in DOCS_DIRECTORY.iterdir() if f.is_file() and f.suffix == ".md"]
        # Prepend the LICENSE file to the list
        files = DEFAULT_FILES + md_files
    except FileNotFoundError as e:
        logger.warning(f"File not found in {DOCS_DIRECTORY} with error: {e}. Will be showing {DEFAULT_FILES} only.")
        files = DEFAULT_FILES
    return templates.TemplateResponse(request, "docs_viewer_list.html", {"docs": files})


@router.get(
    "/{filename}",
    response_class=HTMLResponse,
    name="view_doc_content",
    summary="View a Document or License",
    operation_id="get_doc",
    description="Renders the content of a specific documentation file or the project's LICENSE. It handles Markdown files and plain text files differently.",
)
async def get_doc(request: Request, filename: str):
    """
    Reads a specific file and renders its content in an appropriate HTML template.

    - If the filename is 'LICENSE', it reads the project's root LICENSE file
      and renders it as plain text.
    - Otherwise, it assumes the file is a Markdown document within the `/docs`
      directory, converts it to HTML, and renders it.

    Args:
        request: The incoming FastAPI request object.
        filename: The name of the file to render (e.g., 'LICENSE' or 'my_doc.md').
    """
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename.",
        )

    try:
        if filename in [LICENSE_FILENAME, README_FILENAME]:
            filepath = PROJECT_ROOT / filename
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if filename.endswith(".md"):
                content_html = markdown2.markdown(content, extras=MARKDOWN_EXTRAS)
                return templates.TemplateResponse(
                    request,
                    "docs_viewer_detail.html",
                    {"title": filename, "content": content_html},
                )
            else:
                return templates.TemplateResponse(request, "license.html", {"content": content})
        else:
            filepath = DOCS_DIRECTORY / filename
            with open(filepath, "r", encoding="utf-8") as f:
                content_md = f.read()
            content_html = markdown2.markdown(content_md, extras=MARKDOWN_EXTRAS)
            return templates.TemplateResponse(
                request,
                "docs_viewer_detail.html",
                {"title": filename, "content": content_html},
            )
    except FileNotFoundError as e:
        logger.error(f"File not found: {filename} with error: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found.",
        )
