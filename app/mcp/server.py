from enum import StrEnum
from fastapi import FastAPI
from fastmcp import FastMCP

from fastmcp.server.http import create_streamable_http_app, StarletteWithLifespan

from mcp.server.streamable_http import EventStore

from app.mcp.redis_event_store import RedisEventStore
from app.utils.logging_config import get_logger
from app.utils.config import settings


logger = get_logger(__name__)


if settings.FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER:
    logger.info("Ussing the experimental parser as FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER=true is set in env")
    from fastmcp.experimental.server.openapi import RouteMap, MCPType
else:
    from fastmcp.server.openapi import RouteMap, MCPType


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


class McpAppModes(StrEnum):
    STATELESS = "stateless"  # No server memory; safe across many workers
    STATEFUL = "stateful"  # Per-process memory; needs sticky routing if multi-worker or >1 worker
    EVENT_STORE = "event_store"  # Stateful + shared store across workers (e.g., Redis)


def create_mcp_app(
    mcp_server: FastMCP,
    mode: McpAppModes = McpAppModes.STATEFUL,
) -> StarletteWithLifespan:
    """
    Build an MCP HTTP app using Streamable HTTP.

    Modes:
      - `STATELESS`:
          * Server keeps no cross-request session state.
          * Scales horizontally with multiple workers (no stickiness required).
          * Note:
            - sessions cannot be resumed after disconnection.
            - Default json_response=None: returns SSE stream; no JSON wrapping.
      - `STATEFUL`:
          * Per-process sessions (in-memory). With multiple workers you must ensure
            sticky routing by Mcp-Session-Id, or you will see 400 “No valid session ID”.
      - `EVENT_STORE`: [Experimental]
          * True stateful sessions shared across workers via a central event store (e.g., Redis).
          * Experimental: still add sticky routing to reduce cross-worker chatter.
          * sticky routing should be keyed on the Mcp-Session-Id from header;
            MCP Streamable HTTP uses this header to keep sessions.

    Docs:
      - [MCP Transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
    """
    # Sine we are using the Route-merge pattern it expects the MCP app itself to be mounted at /mcp
    # (i.e., the sub-app's internal path is /mcp)
    logger.info(f"Creating MCP App with {mode}")
    match mode:
        case McpAppModes.STATELESS:
            return mcp_server.http_app(
                path="/mcp",
                json_response=None,
                stateless_http=True,  # multi-worker friendly
                transport="streamable-http",  # or "http" (both hit the same factory)
            )

        case McpAppModes.STATEFUL:
            return mcp_server.http_app(
                path="/mcp",
                json_response=True,
                # stateless_http defaults to False => stateful per-process
                transport="streamable-http",
            )

        case McpAppModes.EVENT_STORE:
            redis_store: EventStore = RedisEventStore(
                namespace="mcp",
                ttl_seconds=24 * 60 * 60,
            )

            return create_streamable_http_app(
                server=mcp_server,
                streamable_http_path="/mcp",
                event_store=redis_store,  # enable cross-worker resumability
                json_response=True,
                # stateless_http=False    # default (stateful)
            )
        case _:
            raise ValueError(f"Unknown MCP mode: {mode}")
