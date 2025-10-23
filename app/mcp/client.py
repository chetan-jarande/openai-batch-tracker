import asyncio
from fastmcp.client import Client
from app.utils.logging_config import get_logger
from app.utils.config import MCP_SERVER_URL

logger = get_logger(__name__)


async def main():
    """
    An example client to interact with the MCP server.
    """
    async with Client(MCP_SERVER_URL) as client:
        # List available tools
        tools = await client.list_tools()
        logger.info("Available tools:")
        for tool in tools:
            logger.info(f"- {tool}")

        # List available resources
        resources = await client.list_resources()
        logger.info("\nAvailable resources:")
        for resource in resources:
            logger.info(f"- {resource.name}")

        # Example: Call a tool (replace with a real tool and parameters)
        # try:
        #     result = await client.call_tool(
        #         "create_batch_create_post",
        #         {
        #             "input_file_id": "your_file_id",
        #             "endpoint": "/v1/chat/completions",
        #             "completion_window": "24h",
        #         },
        #     )
        #     logger.info(f"\nTool call result: {result.data}")
        # except Exception as e:
        #     logger.error(f"\nError calling tool: {e}")


if __name__ == "__main__":
    asyncio.run(main())
