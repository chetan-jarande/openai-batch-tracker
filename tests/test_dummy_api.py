import pytest
from pydantic import ValidationError

from app.schemas.batch import OpenAIBatchResponse
from app.schemas.file import OpenAIFileObjectSchema


@pytest.mark.parametrize(
    "endpoint, schema, expected_count",
    [
        ("/dummy/raw/batches", OpenAIBatchResponse, 25),
        ("/dummy/raw/files", OpenAIFileObjectSchema, 10),
    ],
)
def test_raw_endpoints_schema_and_content(rest_client, endpoint, schema, expected_count):
    """
    Tests the raw JSON endpoints for schema compliance, content, and data types.
    This is a robust way to catch breaking changes from the OpenAI package.
    """
    response = rest_client.get(endpoint)

    assert response.status_code == 200

    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == expected_count

    # Validate each object in the list against the Pydantic schema
    for item in response_data:
        try:
            # This is the key validation step. If the response data doesn't
            # match the schema, this will raise a ValidationError.
            schema.model_validate(item)
        except ValidationError as e:
            pytest.fail(f"Schema validation failed for item in {endpoint}:\n{item}\n{e}")

        # Also, perform some basic type checks on essential fields
        assert "id" in item
        assert isinstance(item["id"], str)
        assert "created_at" in item
        assert isinstance(item["created_at"], int)


@pytest.mark.parametrize(
    "endpoint, expected_title",
    [
        ("/dummy/view/batches", "<h1>OpenAI Batch Job Dashboard</h1>"),
        ("/dummy/view/files", "<h1>OpenAI Files Dashboard</h1>"),
    ],
)
def test_view_endpoints_render_successfully(rest_client, endpoint, expected_title):
    """
    Tests that the HTML dashboard endpoints render successfully.
    """
    response = rest_client.get(endpoint)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert expected_title in response.text
