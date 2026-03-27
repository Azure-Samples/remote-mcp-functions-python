import json
import logging
from pathlib import Path
from typing import Dict, Any

import azure.functions as func
from weather_service import WeatherService
from iot_service import IoTService

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

# IoT service instance
iot_service = IoTService()

# Constants for the IoT Blob Storage path
_IOT_DEVICE_ID_PROPERTY_NAME = "device_id"
_IOT_BLOB_PATH = "iot-sensors/{mcptoolargs." + _IOT_DEVICE_ID_PROPERTY_NAME + "}.json"

# Constants for the IoT Dashboard resource
IOT_DASHBOARD_URI = "ui://iot/index.html"
IOT_DASHBOARD_NAME = "IoT Sensor Dashboard"
IOT_DASHBOARD_DESCRIPTION = "Interactive dashboard for industrial IoT sensor data"
IOT_DASHBOARD_MIME_TYPE = "text/html;profile=mcp-app"
IOT_TOOL_METADATA = '{"ui": {"resourceUri": "ui://iot/index.html"}}'
IOT_RESOURCE_METADATA = '{"ui": {"prefersBorder": true}}'


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


# ---------------------------------------------------------------------------
# IoT Tools
# ---------------------------------------------------------------------------

# IoT Dashboard Resource - returns HTML content for the IoT dashboard widget
@app.mcp_resource_trigger(
    arg_name="context",
    uri=IOT_DASHBOARD_URI,
    resource_name=IOT_DASHBOARD_NAME,
    description=IOT_DASHBOARD_DESCRIPTION,
    mime_type=IOT_DASHBOARD_MIME_TYPE,
    metadata=IOT_RESOURCE_METADATA
)
def get_iot_dashboard(context) -> str:
    """Get the IoT sensor dashboard HTML content."""
    logging.info("Getting IoT dashboard")

    try:
        current_dir = Path(__file__).parent
        file_path = current_dir / "iot-app" / "dist" / "index.html"

        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        else:
            logging.warning(f"IoT dashboard file not found at: {file_path}")
            return """<!DOCTYPE html>
<html>
<head><title>IoT Dashboard</title></head>
<body>
  <h1>IoT Sensor Dashboard</h1>
  <p>Dashboard not found. Run <code>cd src/iot-app && npm install && npm run build</code> first.</p>
</body>
</html>"""
    except Exception as e:
        logging.error(f"Error reading IoT dashboard file: {e}")
        return """<!DOCTYPE html>
<html>
<head><title>IoT Dashboard Error</title></head>
<body>
  <h1>IoT Sensor Dashboard</h1>
  <p>Error loading dashboard content.</p>
</body>
</html>"""

@app.mcp_tool()
@app.mcp_tool_property(
    arg_name="device_id",
    description="Unique identifier of the IoT device (e.g. sensor-industrial-001).",
    property_type=func.McpPropertyType.STRING
)
@app.mcp_tool_property(
    arg_name="location",
    description="Physical location of the device (e.g. Plant-A / Zone-3 / Line-2).",
    property_type=func.McpPropertyType.STRING
)
@app.mcp_tool_property(
    arg_name="timestamp",
    description="ISO 8601 timestamp of the reading (e.g. 2026-03-19T10:30:00Z).",
    property_type=func.McpPropertyType.DATETIME
)
@app.mcp_tool_property(
    arg_name="firmware_version",
    description="Firmware version of the device using semver (e.g. 2.4.1).",
    property_type=func.McpPropertyType.STRING
)
@app.mcp_tool_property(
    arg_name="status",
    description="Operational status of the device: operational | degraded | offline | maintenance.",
    property_type=func.McpPropertyType.STRING
)
@app.mcp_tool_property(
    arg_name="tags",
    description='Labels associated with the device (e.g. "critical", "area-b").',
    property_type=func.McpPropertyType.STRING,
    as_array=True
)
@app.mcp_tool_property(
    arg_name="metrics",
    description=(
        "Current physical measurements: "
        "temperature_celsius (float), humidity_percent (float 0-100), "
        "pressure_bar (float > 0), vibration_hz (float >= 0), power_consumption_kw (float >= 0)."
    ),
    property_type=func.McpPropertyType.OBJECT
)
@app.mcp_tool_property(
    arg_name="alerts",
    description=(
        "Alert objects. Each must have: "
        "code (string), severity (info|warning|critical), message (string), "
        "triggered_at (ISO 8601 string), resolved (boolean)."
    ),
    property_type=func.McpPropertyType.OBJECT,
    as_array=True
)
@app.mcp_tool_property(
    arg_name="maintenance",
    description=(
        "Maintenance info: "
        "last_service_date (YYYY-MM-DD), next_service_date (YYYY-MM-DD), "
        "technician (string), notes (string)."
    ),
    property_type=func.McpPropertyType.OBJECT
)
@app.mcp_tool_property(
    arg_name="network",
    description=(
        "Network info: "
        "ip_address (string), protocol (string, e.g. MQTT), "
        "signal_strength_dbm (int <= 0), connected_gateway (string)."
    ),
    property_type=func.McpPropertyType.OBJECT
)
@app.mcp_tool_property(
    arg_name="history_last_5_readings",
    description="Last temperature readings (up to 10 values), oldest first.",
    property_type=func.McpPropertyType.FLOAT,
    as_array=True
)
@app.blob_output(arg_name="file", connection="AzureWebJobsStorage", path=_IOT_BLOB_PATH)
def ingest_sensor_data(
    file: func.Out[str],
    device_id: str,
    location: str,
    timestamp: str,
    firmware_version: str,
    status: str,
    tags: str,
    metrics: str,
    alerts: str,
    maintenance: str,
    network: str,
    history_last_5_readings: str,
) -> str:
    """Validate and save an IoT sensor payload to Azure Blob Storage."""
    if not device_id:
        return "Error: device_id not provided."

    try:
        data = {
            "device_id": device_id,
            "location": location,
            "timestamp": timestamp,
            "firmware_version": firmware_version,
            "status": status,
            "tags": tags,
            "metrics": metrics,
            "alerts": alerts if alerts else [],
            "maintenance": maintenance if maintenance else {},
            "network": network,
            "history_last_5_readings": history_last_5_readings if history_last_5_readings else [],
        }
    except json.JSONDecodeError as e:
        return f"Error: one or more JSON fields are invalid. Detail: {e}"

    try:
        sensor = iot_service.validate_payload(data)
    except Exception as e:
        return f"Payload validation error: {e}"

    file.set(sensor.to_json())
    logging.info(f"IoT payload saved for device '{device_id}'")
    return f"Payload for device '{device_id}' saved successfully."


@app.mcp_tool(metadata=IOT_TOOL_METADATA)
@app.mcp_tool_property(
    arg_name="device_id",
    description="Unique identifier of the IoT device to generate the report for."
)
@app.blob_input(arg_name="file", connection="AzureWebJobsStorage", path=_IOT_BLOB_PATH)
def get_sensor_report(file: func.InputStream, device_id: str) -> str:
    """Read IoT sensor data from Azure Blob Storage and return a full report
    with health score, metrics, active alerts, and maintenance information."""
    if not device_id:
        return json.dumps({"error": "device_id not provided."})

    try:
        raw = file.read().decode("utf-8")
    except Exception as e:
        logging.error(f"Error reading blob for device '{device_id}': {e}")
        return json.dumps({"error": f"Device '{device_id}' not found or read error."})

    try:
        data = json.loads(raw)
        sensor = iot_service.validate_payload(data)
        report = iot_service.generate_report(sensor)
        logging.info(f"Report generated for device '{device_id}'")
        return json.dumps(report)
    except Exception as e:
        logging.error(f"Error generating report for '{device_id}': {e}")
        return json.dumps({"error": str(e)})


@app.mcp_tool()
@app.mcp_tool_property(
    arg_name="device_id",
    description="Unique identifier of the IoT device whose active alerts should be listed."
)
@app.blob_input(arg_name="file", connection="AzureWebJobsStorage", path=_IOT_BLOB_PATH)
def list_active_alerts(file: func.InputStream, device_id: str) -> str:
    """Read IoT sensor data from Azure Blob Storage and return
    only the alerts that have not yet been resolved (resolved=false)."""
    if not device_id:
        return json.dumps({"error": "device_id not provided."})

    try:
        raw = file.read().decode("utf-8")
    except Exception as e:
        logging.error(f"Error reading blob for device '{device_id}': {e}")
        return json.dumps({"error": f"Device '{device_id}' not found or read error."})

    try:
        data = json.loads(raw)
        sensor = iot_service.validate_payload(data)
        alerts = iot_service.get_active_alerts(sensor)
        result = {
            "device_id": device_id,
            "active_alerts_count": len(alerts),
            "active_alerts": alerts,
        }
        logging.info(f"Active alerts for device '{device_id}': {len(alerts)}")
        return json.dumps(result)
    except Exception as e:
        logging.error(f"Error retrieving alerts for '{device_id}': {e}")
        return json.dumps({"error": str(e)})


@app.mcp_tool()
@app.mcp_tool_property(
    arg_name="device_id",
    description="Unique identifier of the IoT device to compute the metrics summary for."
)
@app.blob_input(arg_name="file", connection="AzureWebJobsStorage", path=_IOT_BLOB_PATH)
def get_sensor_metrics_summary(file: func.InputStream, device_id: str) -> str:
    """Read IoT sensor data from Azure Blob Storage and return a statistical
    summary of the current metrics and reading history
    (min, max, average, standard deviation, trend)."""
    if not device_id:
        return json.dumps({"error": "device_id not provided."})

    try:
        raw = file.read().decode("utf-8")
    except Exception as e:
        logging.error(f"Error reading blob for device '{device_id}': {e}")
        return json.dumps({"error": f"Device '{device_id}' not found or read error."})

    try:
        data = json.loads(raw)
        sensor = iot_service.validate_payload(data)
        summary = iot_service.get_metrics_summary(sensor)
        logging.info(f"Metrics computed for device '{device_id}'")
        return json.dumps(summary)
    except Exception as e:
        logging.error(f"Error computing metrics for '{device_id}': {e}")
        return json.dumps({"error": str(e)})

