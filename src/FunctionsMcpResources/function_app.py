"""
FunctionsMcpResources - MCP Resource Templates on Azure Functions (Python)

This module demonstrates both resource templates and static resources using Azure Functions.
- Resource templates have URI parameters (e.g., {Name}) that clients substitute at runtime
- Static resources have fixed URIs and return consistent data structures
"""

import json
import logging
import os
import platform
import re
from datetime import datetime, timezone

import azure.functions as func
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ============================================================================
# Resource URI and Metadata Constants
# ============================================================================

# Snippet Resource Template (has URI parameter {Name})
SNIPPET_RESOURCE_URI = "snippet://{Name}"
SNIPPET_RESOURCE_NAME = "Snippet"
SNIPPET_RESOURCE_DESCRIPTION = "Reads a code snippet by name from blob storage."
SNIPPET_MIME_TYPE = "application/json"

# Server Info Static Resource (fixed URI, no parameters)
SERVER_INFO_RESOURCE_URI = "info://server"
SERVER_INFO_RESOURCE_NAME = "ServerInfo"
SERVER_INFO_RESOURCE_DESCRIPTION = "Returns information about the MCP server, including version and runtime."
SERVER_INFO_MIME_TYPE = "application/json"

# Metadata for ServerInfo resource (cache TTL)
SERVER_INFO_METADATA = json.dumps({"cache": {"ttlSeconds": 60}})

# ============================================================================
# Resource Template: Snippet
# ============================================================================

@app.mcp_resource_trigger(
    arg_name="context",
    uri=SNIPPET_RESOURCE_URI,
    resource_name=SNIPPET_RESOURCE_NAME,
    description=SNIPPET_RESOURCE_DESCRIPTION,
    mime_type=SNIPPET_MIME_TYPE
)
def get_snippet_resource(context) -> str:
    """
    Resource template that exposes snippets by name.
    
    The {Name} parameter in the URI makes this a resource template rather than
    a static resource — clients can discover it via resources/templates/list
    and read specific snippets by substituting the Name parameter.
    
    This implementation manually extracts the Name parameter from the URI
    and uses the Azure Blob Storage SDK to read the corresponding blob.
    
    Args:
        context: MCP resource invocation context
    
    Returns:
        JSON string containing the snippet content or an error message
    """
    logging.info(f"Snippet resource template invoked: {context.uri}")
    
    try:
        # Extract the Name parameter from the URI (e.g., "snippet://HelloWorld" -> "HelloWorld")
        # The URI pattern is "snippet://{Name}"
        match = re.match(r"snippet://(.+)", context.uri)
        if not match:
            error_response = {
                "error": "Invalid URI",
                "message": f"URI does not match expected pattern 'snippet://{{Name}}'"
            }
            return json.dumps(error_response)
        
        snippet_name = match.group(1)
        logging.info(f"Extracted snippet name: {snippet_name}")
        
        # Get the blob storage connection string
        connection_string = os.environ.get("AzureWebJobsStorage")
        if not connection_string:
            error_response = {
                "error": "Configuration error",
                "message": "AzureWebJobsStorage connection string not found"
            }
            return json.dumps(error_response)
        
        # Create blob service client and read the blob
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client("snippets")
        blob_client = container_client.get_blob_client(f"{snippet_name}.json")
        
        # Download the blob content
        blob_data = blob_client.download_blob()
        snippet_content = blob_data.readall().decode('utf-8')
        
        return snippet_content
        
    except Exception as e:
        logging.error(f"Error reading snippet: {e}")
        error_response = {
            "error": "Snippet not found",
            "message": f"No snippet found for the requested name. Error: {str(e)}"
        }
        return json.dumps(error_response)

# ============================================================================
# Static Resource: Server Info
# ============================================================================

@app.mcp_resource_trigger(
    arg_name="context",
    uri=SERVER_INFO_RESOURCE_URI,
    resource_name=SERVER_INFO_RESOURCE_NAME,
    description=SERVER_INFO_RESOURCE_DESCRIPTION,
    mime_type=SERVER_INFO_MIME_TYPE,
    metadata=SERVER_INFO_METADATA
)
def get_server_info(context) -> str:
    """
    Static resource (no URI parameters) that returns server information.
    
    Demonstrates the difference between a static resource and a resource template.
    This resource has a fixed URI with no parameters and returns dynamic server
    metadata each time it's invoked.
    
    The cache metadata (ttlSeconds: 60) hints to clients that they can cache
    this resource for 60 seconds.
    
    Args:
        context: MCP resource invocation context
    
    Returns:
        JSON string containing server information
    """
    logging.info("Server info resource invoked.")
    
    server_info = {
        "name": "FunctionsMcpResources",
        "version": "1.0.0",
        "runtime": f"Python {platform.python_version()}",
        "platform": platform.platform(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return json.dumps(server_info, indent=2)
