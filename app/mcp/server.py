from fastapi import FastAPI
from fastmcp import FastMCP

# Ussing the experimental parser as FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER=true is set in env
from fastmcp.experimental.server.openapi import RouteMap, MCPType

from app.utils.logging_config import get_logger


logger = get_logger(__name__)


CUSTOM_ROUTE_MAPS = [
    # GET with path params → ResourceTemplates
    # API's such as `/files/{id}`
    RouteMap(
        methods=["GET"],
        pattern=r".*\{.*\}.*",
        mcp_type=MCPType.RESOURCE_TEMPLATE,
    ),
    # Other GETs → Resources
    RouteMap(
        methods=["GET"],
        pattern=r".*",
        mcp_type=MCPType.RESOURCE,
    ),
    # POST/PUT/DELETE → Tools (default)
]


def create_mcp_server(fast_api_app: FastAPI) -> FastMCP:
    """
    Creates and configures the MCP server from the FastAPI application.
    """
    mcp_server = FastMCP.from_fastapi(
        app=fast_api_app,
        route_maps=CUSTOM_ROUTE_MAPS,
    )
    logger.info(f"MCP server created with custom route maps for FastAPI App: '{fast_api_app.title}'")
    return mcp_server
