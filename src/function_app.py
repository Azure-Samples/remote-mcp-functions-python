import json
import logging
from pathlib import Path
from typing import Dict, Any

import azure.functions as func
from weather_service import WeatherService

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Weather service instance
weather_service = WeatherService()

# Constants for the Weather Widget resource
WEATHER_WIDGET_URI = "ui://weather/index.html"
WEATHER_WIDGET_NAME = "Weather Widget"
WEATHER_WIDGET_DESCRIPTION = "Interactive weather display for MCP Apps"
WEATHER_WIDGET_MIME_TYPE = "text/html;profile=mcp-app"

# Metadata for the tool (as valid JSON string)
TOOL_METADATA = '{"ui": {"resourceUri": "ui://weather/index.html"}}'

# Metadata for the resource (as valid JSON string)
RESOURCE_METADATA = '{"ui": {"prefersBorder": true}}'

# Constants for the Azure Blob Storage container, file, and blob path
_SNIPPET_NAME_PROPERTY_NAME = "snippetname"
_BLOB_PATH = "snippets/{mcptoolargs." + _SNIPPET_NAME_PROPERTY_NAME + "}.json"


@app.mcp_tool()
def hello_mcp() -> str:
    """Hello world."""
    return "Hello I am MCPTool!"


@app.mcp_tool()
@app.mcp_tool_property(arg_name="snippetname", description="The name of the snippet.")
@app.blob_input(arg_name="file", connection="AzureWebJobsStorage", path=_BLOB_PATH)
def get_snippet(file: func.InputStream, snippetname: str) -> str:
    """Retrieve a snippet by name from Azure Blob Storage."""
    snippet_content = file.read().decode("utf-8")
    logging.info(f"Retrieved snippet: {snippet_content}")
    return snippet_content


@app.mcp_tool()
@app.mcp_tool_property(arg_name="snippetname", description="The name of the snippet.")
@app.mcp_tool_property(arg_name="snippet", description="The content of the snippet.")
@app.blob_output(arg_name="file", connection="AzureWebJobsStorage", path=_BLOB_PATH)
def save_snippet(file: func.Out[str], snippetname: str, snippet: str) -> str:
    """Save a snippet with a name to Azure Blob Storage."""
    if not snippetname:
        return "No snippet name provided"

    if not snippet:
        return "No snippet content provided"

    file.set(snippet)
    logging.info(f"Saved snippet: {snippet}")
    return f"Snippet '{snippet}' saved successfully"


# Weather Widget Resource - returns HTML content for the weather widget
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
    logging.info("Getting weather widget")
    
    try:
        # Get the path to the widget HTML file
        # Current file is src/function_app.py, look for src/app/index.html
        current_dir = Path(__file__).parent
        file_path = current_dir / "app" / "dist" / "index.html"
        
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        else:
            logging.warning(f"Weather widget file not found at: {file_path}")
            # Return a fallback HTML if file not found
            return """<!DOCTYPE html>
<html>
<head><title>Weather Widget</title></head>
<body>
  <h1>Weather Widget</h1>
  <p>Widget content not found. Please ensure the app/index.html file exists.</p>
</body>
</html>"""
    except Exception as e:
        logging.error(f"Error reading weather widget file: {e}")
        return """<!DOCTYPE html>
<html>
<head><title>Weather Widget Error</title></head>
<body>
  <h1>Weather Widget</h1>
  <p>Error loading widget content.</p>
</body>
</html>"""


# Get Weather Tool - returns current weather for a location
@app.mcp_tool(metadata=TOOL_METADATA)
@app.mcp_tool_property(arg_name="location", description="City name to check weather for (e.g., Seattle, New York, Miami)")
def get_weather(location: str) -> Dict[str, Any]:
    """Returns current weather for a location via Open-Meteo."""
    logging.info(f"Getting weather for location: {location}")
    
    try:
        result = weather_service.get_current_weather(location)
        
        if "TemperatureC" in result:
            logging.info(f"Weather fetched for {result['Location']}: {result['TemperatureC']}°C")
        else:
            logging.warning(f"Weather error for {result['Location']}: {result.get('Error', 'Unknown error')}")
        
        return json.dumps(result)
    except Exception as e:
        logging.error(f"Failed to get weather for {location}: {e}")
        return json.dumps({
            "Location": location or "Unknown",
            "Error": f"Unable to fetch weather: {str(e)}",
            "Source": "api.open-meteo.com"
        })

