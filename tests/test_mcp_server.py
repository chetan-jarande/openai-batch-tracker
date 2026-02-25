import pytest
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@pytest.mark.asyncio
async def test_mcp_server_components(mcp_client):
    """
    Integration test to verify MCP server components using in-memory transport.
    """
    try:
        logger.info("Testing MCP server components...")

        logger.info("[1] Listing tools from MCP server...")
        tools = await mcp_client.list_tools()
        assert tools is not None, "Failed to retrieve tools, received None."
        assert len(tools) > 0, "No tools found on the MCP server."
        tool_names = {tool.name for tool in tools}
        logger.info(f"Found {len(tool_names)} tools: {tool_names}")
        assert "create_openai_batch" in tool_names
        assert "upload_openai_file" in tool_names

        logger.info("[2] Listing resources from MCP server...")
        resources = await mcp_client.list_resources()
        assert resources is not None, "Failed to retrieve resources, received None."
        assert len(resources) > 0, "No resources found on the MCP server."
        resource_names = {resource.name for resource in resources}
        logger.info(f"Found {len(resource_names)} resources: {resource_names}")
        assert "list_openai_batches" in resource_names
        assert "list_openai_files" in resource_names

        logger.info("[3] Listing resource templates from MCP server...")
        resource_templates = await mcp_client.list_resource_templates()
        assert resource_templates is not None, "Failed to retrieve resource templates, received None."
        assert len(resource_templates) > 0, "No resource templates found on the MCP server."
        resource_template_names = {template.name for template in resource_templates}
        logger.info(f"Found {len(resource_template_names)} resource templates: {resource_template_names}")
        assert "get_openai_file_details" in resource_template_names
        assert "get_openai_batch_details" in resource_template_names

    except Exception as e:
        pytest.fail(f"Failed to interact with the MCP server. With Error: {e}")
