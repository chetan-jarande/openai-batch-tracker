import asyncio
from fastmcp.client import Client
from app.utils.logging_config import get_logger
from app.utils.config import MCP_SERVER_URL

logger = get_logger(__name__)


async def verify_tools(client: Client):
    """
    Verifies that the expected tools are available on the MCP server.
    """
    tools = await client.list_tools()
    tool_names = {tool.name for tool in tools}
    logger.info(f"Found {len(tool_names)} tools: {tool_names}")

    # Add your expected tool names here
    expected_tools = {
        "create_batch_batches_create_post",
        "cancel_batch_batches__batch_id__cancel_post",
        "upload_file_to_openai_files_upload_post",
        "delete_openai_file_files__openai_file_id__delete",
    }

    missing_tools = expected_tools - tool_names
    if missing_tools:
        logger.warning(f"Missing tools: {missing_tools}")
    else:
        logger.info("All expected tools are present.")


async def verify_resources(client: Client):
    """
    Verifies that the expected resources are available on the MCP server.
    """
    resources = await client.list_resources()
    resource_names = {resource.name for resource in resources}
    logger.info(f"Found {len(resource_names)} resources: {resource_names}")

    # Add your expected resource names here
    expected_resources = {
        "list_batches_batches_list_get",
        "list_files_from_openai_files_list_get",
    }

    missing_resources = expected_resources - resource_names
    if missing_resources:
        logger.warning(f"Missing resources: {missing_resources}")
    else:
        logger.info("All expected resources are present.")


async def main():
    """
    Main function to run the verification checks.
    """
    async with Client(MCP_SERVER_URL) as client:
        await verify_tools(client)
        await verify_resources(client)


if __name__ == "__main__":
    asyncio.run(main())
