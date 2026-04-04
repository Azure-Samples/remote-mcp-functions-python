# Sample MCP App for weather

This Azure Functions app demonstrates an MCP App that displays weather information with an interactive UI. It showcases how MCP tools can return interactive interfaces instead of plain text.

<img src="/media/weather-ui.png" alt="Weather tool returning UI" width="50%">

## What Are MCP Apps?

[MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) let tools return interactive interfaces. When a tool declares a UI resource, the host renders it in a sandboxed iframe where users can interact directly.

**MCP Apps = Tool + UI Resource**

The architecture uses two MCP primitives:
1. **Tools** with UI metadata pointing to a resource URI
2. **Resources** containing bundled HTML/JavaScript served via the `ui://` scheme

## Features

This MCP App provides:

- **get_weather**: A tool that returns current weather data for any city using the Open-Meteo API
- **Weather Widget**: An interactive HTML/JavaScript UI that displays the weather data visually

## Prerequisites

- [Python](https://www.python.org/downloads/) version 3.13 or higher
- [Node.js](https://nodejs.org/) (for building the UI)
- [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local)
- An MCP-compatible host (Claude Desktop, VS Code, ChatGPT, etc.)

## Local Development

### 1. Build the UI

The UI must be bundled before running the function app. From the `src/McpWeatherApp/app` directory:

```bash
npm install
npm run build
```

This creates a bundled `app/dist/index.html` file that the function serves.

### 2. Start Azurite

An Azure Storage Emulator is needed for the function app to run locally:

```bash
docker run -p 10000:10000 -p 10001:10001 -p 10002:10002 \
    mcr.microsoft.com/azure-storage/azurite
```

> **Note**: If using the Azurite VS Code extension, run `Azurite: Start` from the command palette.

### 3. Install Python Dependencies

From the `src/McpWeatherApp` directory, create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 4. Run the Function App

```bash
func start
```

The MCP server will be available at `http://localhost:7071/runtime/webhooks/mcp`.

## Using the MCP App

### Connect from VS Code

1. Open [.vscode/mcp.json](../../.vscode/mcp.json)
2. Find the server called `local-mcp-function` and click **Start**
3. The server uses the endpoint: `http://localhost:7071/runtime/webhooks/mcp`

### Prompt the Agent

Ask Copilot: **"What's the weather in Seattle?"**

The agent will call the `get_weather` tool, and instead of just showing text, you'll see an interactive weather widget with the current conditions.

## How It Works

### The Tool with UI Metadata

The `get_weather` tool declares it has an associated UI using metadata:

```python
# Required metadata pointing to the UI resource
TOOL_METADATA = json.dumps({"ui": {"resourceUri": "ui://weather/index.html"}})

@app.mcp_tool(metadata=TOOL_METADATA)
@app.mcp_tool_property(arg_name="location", description="City name to check weather for")
def get_weather(location: str) -> Dict[str, Any]:
    """Returns current weather for a location via Open-Meteo."""
    # Fetch and return weather data
```

The `resourceUri` tells the MCP host that when this tool is invoked, there's an interactive UI available at `ui://weather/index.html`.

### The Resource Serving the UI

The `get_weather_widget` function serves the bundled HTML at the matching URI:

```python
RESOURCE_METADATA = json.dumps({"ui": {"prefersBorder": True}})

@app.mcp_resource_trigger(
    arg_name="context",
    uri=WEATHER_WIDGET_URI,
    resource_name=WEATHER_WIDGET_NAME,
    description=WEATHER_WIDGET_DESCRIPTION,
    mime_type=WEATHER_WIDGET_MIME_TYPE,
    metadata=RESOURCE_METADATA
)
def get_weather_widget(context) -> str:
    """Get the weather widget HTML content."""
    # Return the bundled HTML/JS from app/dist/index.html
```

### The Complete Flow

1. User asks: "What's the weather in Seattle?"
2. Agent calls the `get_weather` tool
3. Tool returns weather data (JSON) **and** the host sees the `ui.resourceUri` metadata
4. Host fetches the UI resource from `ui://weather/index.html`
5. Host renders the HTML in a sandboxed iframe, passing the tool result as context
6. User sees an interactive weather widget instead of plain text

## The UI (TypeScript)

The frontend in `app/src/weather-app.ts` receives the tool result and renders the weather display. It's bundled with Vite into a single `index.html` that the resource serves.

To rebuild the UI after making changes:

```bash
cd app
npm run build
```

## Deployment to Azure

See [Deploy to Azure for Remote MCP](../../README.md#deploy-to-azure-for-remote-mcp) for deployment instructions. The UI will be automatically bundled and deployed with the function app. 

## Weather Service

The `weather_service.py` module handles geocoding (converting city names to coordinates) and fetching weather data from the Open-Meteo API. It provides a clean interface for the function app to retrieve weather information.

## Customization

To customize the weather widget:

1. Edit the UI in `app/src/weather-app.ts`
2. Modify styles in the TypeScript file
3. Rebuild the UI with `npm run build`
4. Restart the function app with `func start`

You can also extend the weather service to include additional data like forecasts, humidity, wind speed, etc.

## Troubleshooting

| Error | Solution |
|---|---|
| `AttributeError: 'FunctionApp' object has no attribute 'mcp_resource_trigger'` | Python 3.13 is required. Verify with `python3 --version`. Install via `brew install python@3.13` (macOS) or from [python.org](https://www.python.org/downloads/). Recreate your virtual environment with Python 3.13 after installing. |
| Connection refused | Ensure Azurite is running (`docker run -p 10000:10000 -p 10001:10001 -p 10002:10002 mcr.microsoft.com/azure-storage/azurite`) |
| API version not supported by Azurite | Pull the latest Azurite image (`docker pull mcr.microsoft.com/azure-storage/azurite`) then restart Azurite and the app |
