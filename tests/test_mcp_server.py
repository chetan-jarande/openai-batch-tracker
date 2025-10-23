import pytest
from fastmcp.client import Client
from app.utils.logging_config import get_logger
from app.utils.config import MCP_SERVER_URL

logger = get_logger(__name__)


@pytest.mark.asyncio
async def test_mcp_server_connectivity_and_components():
    """
    Integration test to connect to the running MCP server and verify components.
    Assumes the MCP server is running and accessible.
    """
    try:
        async with Client(MCP_SERVER_URL) as client:
            # 1. Test listing tools
            tools = await client.list_tools()
            assert tools is not None, "Failed to retrieve tools, received None."
            assert len(tools) > 0, "No tools found on the MCP server."

            tool_names = {tool.name for tool in tools}
            logger.info(f"Found {len(tool_names)} tools: {tool_names}")

            # Assert that a few critical tools exist
            assert "create_batch_batches_create_post" in tool_names
            assert "upload_file_to_openai_files_upload_post" in tool_names

            # 2. Test listing resources
            resources = await client.list_resources()
            assert resources is not None, "Failed to retrieve resources, received None."
            assert len(resources) > 0, "No resources found on the MCP server."

            resource_names = {resource.name for resource in resources}
            logger.info(f"Found {len(resource_names)} resources: {resource_names}")

            # Assert that a few critical resources exist
            assert "list_batches_batches_list_get" in resource_names
            assert "service_status_check_status_get" in resource_names

    except Exception as e:
        pytest.fail(
            f"Failed to connect to or interact with the MCP server at {MCP_SERVER_URL}. "
            f"Ensure the server is running. Error: {e}"
        )
