import asyncio
from fastmcp.client import Client
from app.utils.logging_config import get_logger
from app.utils.config import MCP_SERVER_URL

logger = get_logger(__name__)


async def call_tool_by_name(client: Client, tool_name: str, tool_params: dict):
    """
    Calls a specific tool by its name with the given parameters.
    """
    try:
        logger.info(f"\nCalling tool: '{tool_name}' with params: {tool_params}")
        result = await client.call_tool(tool_name, tool_params)
        logger.info(f"Tool call result: {result.data}")
        return result
    except Exception as e:
        logger.error(f"Error calling tool '{tool_name}': {e}")
        return None


async def get_resources(client: Client):
    """
    Lists all available resources.
    """
    resources = await client.list_resources()
    logger.info("\nAvailable resources:")
    for resource in resources:
        logger.info(f"- {resource.name}")
    return resources


async def get_resource_templates(client: Client):
    """
    Lists all available resource templates.
    """
    resource_templates = await client.list_resource_templates()
    logger.info("\nAvailable resource templates:")
    for template in resource_templates:
        logger.info(f"- {template.name}")
    return resource_templates


async def get_tools(client: Client):
    tools = await client.list_tools()
    logger.info("Available tools:")
    for tool in tools:
        logger.info(f"- {tool.name}")
    return tools


async def main():
    """
    An example client to interact with the MCP server.
    """
    async with Client(MCP_SERVER_URL) as client:
        tools = await get_tools(client)
        resources = await get_resources(client)
        resource_templates = await get_resource_templates(client)
        logger.info(
            f"Gathred Tools: {len(tools)}, Resource: {len(resources)}, Resource Templates: {len(resource_templates)}"
        )


if __name__ == "__main__":
    asyncio.run(main())
