
# MCP Support

This document outlines the Model Context Protocol (MCP) support integrated into the OpenAI Batch Tracker service. MCP provides a standardized interface for AI models to interact with the service, enabling them to discover and utilize available tools and resources programmatically.

## Running the MCP Client

Once the main application server is running, you can test the MCP integration by running the client script. This script will connect to the MCP server, list all available tools and resources, and demonstrate how to interact with them.

To run the MCP client, use the following command from the root of the project:

```bash
python -m app.mcp.client
```

This will output a list of registered tools and resources, confirming that the MCP server is operational and accessible.

## MCP App Types

The integration supports different modes for the MCP application, configured based on the environment:

- **`McpAppModes.STATEFUL`**: Used in development (`DEV`) environments. This mode maintains session state in memory, which is useful for debugging and interactive development.
- **`McpAppModes.STATELESS`**: Used in production (`PROD`) environments. This mode does not maintain any session state, ensuring that the application is scalable and resilient.
- **`McpAppModes.EVENT_STORE`**: An experimental mode that uses a Redis-backed event store for session management allows session resumability between multiple workers. This provides persistence and is suitable for more advanced use cases. Community contributions and feedback are welcome.

The mode is determined by the `CONF_ENV` setting in the application's configuration.

## VS Code Configuration for MCP

To enhance the development experience with MCP in VS Code, you can add the following configuration to your `.vscode/mcp.json` file. This allows you to interact with the MCP server directly from the VS Code interface.

```json
{
	"servers": {
		"batch-tracker-mcp": {
			"url": "http://localhost:8000/mcp",
			"type": "http"
		},
	},
	"inputs": []
}
```

This configuration defines the endpoint for the MCP server, making it easy to send requests and view responses within the editor.

## Framework

This MCP integration is built using the [FastMCP](https://gofastmcp.com/integrations/fastapi) framework, which simplifies the creation of MCP-compliant servers in Python.
