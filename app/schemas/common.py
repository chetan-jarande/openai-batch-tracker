from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Generic type variable for paginated responses
DataType = TypeVar("DataType")


class Msg(BaseModel):
    """
    Schema for a generic message response.
    """

    message: str = Field(
        ...,
        description="A message detailing the result of an operation."
    )
    details: Optional[str] = Field(None, description="Optional additional details.")


class PaginatedResponse(BaseModel, Generic[DataType]):
    """
    Generic schema for paginated API responses.
    """

    count: int = Field(
        ...,
        description="Total number of items available."
    )
    limit: int = Field(
        ...,
        description="Number of items per page (page size)."
    )
    offset: int = Field(
        ...,
        description="Offset of the current page."
    )
    # next_page: Optional[str] = Field(None, description="URL for the next page of results, if any.")
    # previous_page: Optional[str] = Field(None, description="URL for the previous page of results, if any.")
    items: List[DataType] = Field(
        ...,
        description="List of items for the current page."
    )


if __name__ == "__main__":
    # Example of how to use these common schemas
    logger.info("Testing common schemas...")

    # Test Msg schema
    msg_success = Msg(message="Operation completed successfully.")
    msg_with_details = Msg(
        message="Error occurred.", details="Database connection failed."
    )
    logger.info(f"Msg success: {msg_success.model_dump_json(indent=2)}")
    logger.info(f"Msg with details: {msg_with_details.model_dump_json(indent=2)}")

    # Test PaginatedResponse schema
    class SampleItem(BaseModel):
        id: int
        value: str

    paginated_data = PaginatedResponse[SampleItem](
        count=50,
        limit=5,
        offset=0,
        items=[
            SampleItem(id=1, value="Item A"),
            SampleItem(id=2, value="Item B"),
        ],
    )
    logger.info(f"Paginated response: {paginated_data.model_dump_json(indent=2)}")
    logger.info("Common schemas test complete.")
