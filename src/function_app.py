import json
import logging

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Constants for the Azure Blob Storage container, file, and blob path
_SNIPPET_NAME_PROPERTY_NAME = "snippetname"
_SNIPPET_PROPERTY_NAME = "snippet"
_SNIPPET_BLOB_PATH = "snippets/{mcptoolargs." + _SNIPPET_NAME_PROPERTY_NAME + "}.json"
_SIMPLE_SENSOR_BLOB_PATH = "simple-sensor-data/{mcptoolargs.timestamp}-{mcptoolargs.sensor_id}.json"
_COMPLEX_SENSOR_BLOB_PATH = "complex-sensor-data/{mcptoolargs.timestamp}-{mcptoolargs.device_id}.json"

# Modified ToolProperty class to support nested properties
class ToolProperty:
    def __init__(self, property_name: str, property_type: str, description: str, properties=None, items=None):
        self.propertyName = property_name
        self.propertyType = property_type
        self.description = description
        self.properties = properties
        self.items = items

    def to_dict(self):
        result = {
            "propertyName": self.propertyName,
            "propertyType": self.propertyType,
            "description": self.description,
        }
        
        if self.properties:
            if isinstance(self.properties, list):
                result["properties"] = [prop.to_dict() if isinstance(prop, ToolProperty) else prop for prop in self.properties]
            else:
                result["properties"] = self.properties

        if self.items:
            if isinstance(self.items, ToolProperty):
                result["items"] = self.items.to_dict()
            else:
                result["items"] = self.items
                
        return result

# Define the tool properties using the ToolProperty class
tool_properties_save_snippets_object = [
    ToolProperty(_SNIPPET_NAME_PROPERTY_NAME, "string", "The name of the snippet."),
    ToolProperty(_SNIPPET_PROPERTY_NAME, "string", "The content of the snippet."),
]

tool_properties_get_snippets_object = [ToolProperty(_SNIPPET_NAME_PROPERTY_NAME, "string", "The name of the snippet.")]

# Convert the tool properties to JSON
tool_properties_save_snippets_json = json.dumps([prop.to_dict() for prop in tool_properties_save_snippets_object])
tool_properties_get_snippets_json = json.dumps([prop.to_dict() for prop in tool_properties_get_snippets_object])

@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="hello_mcp",
    description="Hello world.",
    toolProperties="[]",
)
def hello_mcp(context) -> None:
    """
    A simple function that returns a greeting message.

    Args:
        context: The trigger context (not used in this function).

    Returns:
        str: A greeting message.
    """
    return "Hello I am MCPTool!"


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="get_snippet",
    description="Retrieve a snippet by name.",
    toolProperties=tool_properties_get_snippets_json,
)
@app.generic_input_binding(arg_name="file", type="blob", connection="AzureWebJobsStorage", path=_SNIPPET_BLOB_PATH)
def get_snippet(file: func.InputStream, context) -> str:
    """
    Retrieves a snippet by name from Azure Blob Storage.

    Args:
        file (func.InputStream): The input binding to read the snippet from Azure Blob Storage.
        context: The trigger context containing the input arguments.

    Returns:
        str: The content of the snippet or an error message.
    """
    snippet_content = file.read().decode("utf-8")
    logging.info(f"Retrieved snippet: {snippet_content}")
    return snippet_content


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="save_snippet",
    description="Save a snippet with a name.",
    toolProperties=tool_properties_save_snippets_json,
)
@app.generic_output_binding(arg_name="file", type="blob", connection="AzureWebJobsStorage", path=_SNIPPET_BLOB_PATH)
def save_snippet(file: func.Out[str], context) -> str:
    content = json.loads(context)
    snippet_name_from_args = content["arguments"][_SNIPPET_NAME_PROPERTY_NAME]
    snippet_content_from_args = content["arguments"][_SNIPPET_PROPERTY_NAME]

    if not snippet_name_from_args:
        return "No snippet name provided"

    if not snippet_content_from_args:
        return "No snippet content provided"

    file.set(snippet_content_from_args)
    logging.info(f"Saved snippet: {snippet_content_from_args}")
    return f"Snippet '{snippet_content_from_args}' saved successfully"

# Define the tool properties for sensor data using the ToolProperty class
tool_properties_simple_sensor_data_object = [
    ToolProperty("sensor_id", "string", "ID of the sensor"),
    ToolProperty("metric_name", "string", "Name of the metric"),
    ToolProperty("value", "number", "Value of the metric"),
    ToolProperty("unit", "string", "Unit of the metric"),
    ToolProperty("timestamp", "DateTime", "Timestamp of the data"),
    ToolProperty("IsCalibrated", "boolean", "If the device is calibrated manually (true) or automatically (false)"),
]

# Convert the sensor data tool properties to JSON
tool_properties_simple_sensor_data_json = json.dumps([prop.to_dict() for prop in tool_properties_simple_sensor_data_object])

@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="save_simple_sensor_data",
    description="Save sensor data.",
    toolProperties=tool_properties_simple_sensor_data_json,
)
@app.generic_output_binding(arg_name="file", type="blob", connection="AzureWebJobsStorage", path=_SIMPLE_SENSOR_BLOB_PATH)
def save_simple_sensor_data(file: func.Out[str], context) -> str:
    """
    Save sensor data to Azure Blob Storage.

    Args:
        file (func.Out[str]): The output binding to write the sensor data to Azure Blob Storage.
        context: The trigger context containing the input arguments.

    Returns:
        str: A success message indicating that the sensor data was saved.
    """
    content = json.loads(context)
    logging.info(f"Received content: {content}")
    sensor_data = content["arguments"]

    if not sensor_data:
        return "No sensor data provided"

    file.set(json.dumps(sensor_data))
    logging.info(f"Saved sensor data: {sensor_data}")
    return "Sensor data saved successfully"

# Define the complex tool properties using ToolProperty class
def create_complex_sensor_tool_properties():
    # Location properties
    location_properties = [
        ToolProperty("latitude", "number", "Latitude of the device location"),
        ToolProperty("longitude", "number", "Longitude of the device location"),
        ToolProperty("altitude", "number", "Altitude of the device location"),
        ToolProperty("description", "string", "Description of the device location")
    ]

    # Metric properties
    metric_properties = [
        ToolProperty("name", "string", "Name of the metric"),
        ToolProperty("value", "number", "Value of the metric"),
        ToolProperty("unit", "string", "Unit of the metric"),
        ToolProperty("timestamp", "number", "Timestamp of the metric data (epoch seconds)"),
        ToolProperty("is_calibrated", "boolean", "Whether the metric is calibrated"),
        ToolProperty("quality", "string", "Quality status of the metric")
    ]

    # Sensor status properties
    status_properties = [
        ToolProperty("battery_level", "number", "Battery level percentage"),
        ToolProperty("signal_strength", "number", "Signal strength in dBm"),
        ToolProperty("last_maintenance", "number", "Timestamp of last maintenance (epoch seconds)"),
        ToolProperty("errors", "array", "List of error codes or messages", 
                    items=ToolProperty("error", "string", "Error code or message"))
    ]

    # Sensor properties
    sensor_properties = [
        ToolProperty("sensor_id", "string", "Unique identifier of the sensor"),
        ToolProperty("type", "string", "Type of the sensor (e.g., temperature, humidity)"),
        ToolProperty("metrics", "array", "List of metrics measured by the sensor",
                    items=ToolProperty("metric", "object", "Metric information", properties=metric_properties)),
        ToolProperty("status", "object", "Status information of the sensor", properties=status_properties)
    ]

    # Event properties
    event_properties = [
        ToolProperty("event_id", "string", "Unique identifier of the event"),
        ToolProperty("type", "string", "Type of the event"),
        ToolProperty("sensor_id", "string", "ID of the sensor related to the event"),
        ToolProperty("metric", "string", "Metric involved in the event"),
        ToolProperty("value", "number", "Value that triggered the event"),
        ToolProperty("threshold", "number", "Threshold value for the event"),
        ToolProperty("timestamp", "number", "Timestamp of the event (epoch seconds)"),
        ToolProperty("severity", "string", "Severity level of the event")
    ]

    # Network properties
    network_properties = [
        ToolProperty("type", "string", "Type of network connection (e.g., wifi, ethernet)"),
        ToolProperty("ssid", "string", "SSID of the WiFi network"),
        ToolProperty("ip", "string", "IP address of the device")
    ]

    # Configuration properties
    configuration_properties = [
        ToolProperty("sampling_interval_sec", "number", "Sampling interval in seconds"),
        ToolProperty("transmit_interval_sec", "number", "Data transmission interval in seconds"),
        ToolProperty("firmware_version", "string", "Firmware version of the device"),
        ToolProperty("network", "object", "Network configuration details", properties=network_properties)
    ]

    # Main device properties
    return [
        ToolProperty("device_id", "string", "Unique identifier of the device"),
        ToolProperty("timestamp", "DateTime", "Timestamp of the device data"),
        ToolProperty("location", "object", "Geographical and descriptive location of the device", properties=location_properties),
        ToolProperty("sensors", "array", "List of sensors attached to the device",
                    items=ToolProperty("sensor", "object", "Sensor information", properties=sensor_properties)),
        ToolProperty("events", "array", "List of events generated by the device",
                    items=ToolProperty("event", "object", "Event information", properties=event_properties)),
        ToolProperty("configuration", "object", "Device configuration details", properties=configuration_properties)
    ]

# Create and convert the complex sensor data tool properties
tool_properties_complex_sensor_data_object = create_complex_sensor_tool_properties()
tool_properties_complex_sensor_data_json = json.dumps([prop.to_dict() for prop in tool_properties_complex_sensor_data_object])

@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="save_complex_sensor_data",
    description="Save complex IoT device data with nested sensor, event, and configuration information.",
    toolProperties=tool_properties_complex_sensor_data_json,
)
@app.generic_output_binding(arg_name="file", type="blob", connection="AzureWebJobsStorage", path=_COMPLEX_SENSOR_BLOB_PATH)
def save_complex_sensor_data(file: func.Out[str], context) -> str:
    """
    Save complex IoT device data to Azure Blob Storage.

    Args:
        file (func.Out[str]): The output binding to write the device data to Azure Blob Storage.
        context: The trigger context containing the input arguments.

    Returns:
        str: A success message indicating that the device data was saved.
    """
    content = json.loads(context)
    logging.info(f"Received device data content: {content}")
    device_data = content["arguments"]

    if not device_data:
        return "No device data provided"

    if not device_data.get("device_id"):
        return "Device ID is required"

    # Save the complete device data structure
    file.set(json.dumps(device_data))
    logging.info(f"Saved device data for device: {device_data.get('device_id')}")
    return f"Device data for {device_data.get('device_id')} saved successfully"