
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

## MCP Inspector

For more advanced debugging and interaction with the MCP server, you can use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector). This tool provides a web-based interface for exploring and testing MCP servers.

To run the inspector, you'll need Node.js installed. Then, you can use the following command:

```bash
npx @modelcontextprotocol/inspector
```

This will start the inspector, which you can access in your web browser at [`http://localhost:6274`](http://localhost:6274). From there, you can connect to your running MCP server.

### Docker Workflow

The MCP Inspector is also integrated into the Docker development workflow. When you run the development environment, the inspector service is started automatically.

You can access it by opening the URL provided in the inspector's logs. To view the logs, run:

```bash
make docker-logs-inspector
```

Then, copy the URL from the logs (which includes a security token) and paste it into your browser.

#### Connecting to the Server

The inspector is now configured to automatically connect to the `app-dev` service when it starts. You should see the tools and resources listed in the UI without needing to manually configure the connection.
You can go to below url to access the inspector.
```bash
http://localhost:6274
```

## Framework

This MCP integration is built using the [FastMCP](https://gofastmcp.com/integrations/fastapi) framework, which simplifies the creation of MCP-compliant servers in Python.
