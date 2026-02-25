import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from fastmcp.client import Client
from app.main import mcp_server, combined_app
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@pytest.fixture(scope="session")
def rest_client():
    """
    Fixture for testing standard REST API endpoints using TestClient (synchronous).
    """
    with TestClient(combined_app) as c:
        yield c


@pytest_asyncio.fixture
async def mcp_client():
    """
    Fixture that provides an MCP client connected to the in-memory MCP server.
    This allows tests to interact with the MCP server without starting a real HTTP server.
    """
    async with Client(mcp_server) as client:
        yield client
