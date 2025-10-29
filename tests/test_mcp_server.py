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
        logger.info("Testing MCP server connectivity and components...")
        async with Client(MCP_SERVER_URL) as client:
            logger.info("[1] Listing tools from MCP server...")
            tools = await client.list_tools()
            assert tools is not None, "Failed to retrieve tools, received None."
            assert len(tools) > 0, "No tools found on the MCP server."
            tool_names = {tool.name for tool in tools}
            logger.info(f"Found {len(tool_names)} tools: {tool_names}")
            assert "create_openai_batch" in tool_names
            assert "upload_openai_file" in tool_names

            logger.info("[2] Listing resources from MCP server...")
            resources = await client.list_resources()
            assert resources is not None, "Failed to retrieve resources, received None."
            assert len(resources) > 0, "No resources found on the MCP server."
            resource_names = {resource.name for resource in resources}
            logger.info(f"Found {len(resource_names)} resources: {resource_names}")
            assert "list_openai_batches" in resource_names
            assert "list_openai_files" in resource_names

            logger.info("[3] Listing resource templates from MCP server...")
            resource_templates = await client.list_resource_templates()
            assert resource_templates is not None, "Failed to retrieve resource templates, received None."
            assert len(resource_templates) > 0, "No resource templates found on the MCP server."
            resource_template_names = {template.name for template in resource_templates}
            logger.info(f"Found {len(resource_template_names)} resource templates: {resource_template_names}")
            assert "get_openai_file_details" in resource_template_names
            assert "get_openai_batch_details" in resource_template_names

    except Exception as e:
        pytest.fail(f"Failed to connect to or interact with the MCP server at {MCP_SERVER_URL}. With Error: {e}")
