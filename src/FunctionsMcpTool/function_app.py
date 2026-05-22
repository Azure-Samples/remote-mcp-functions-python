import logging
import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from io import BytesIO

import azure.functions as func
from mcp.types import ImageContent, TextContent, CallToolResult
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

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


# ============================================================================
# Rich Content Tools
# ============================================================================

@app.mcp_tool()
@app.mcp_tool_property(arg_name="text", description="The text to encode in the QR code.", is_required=True)
def generate_qr_code(text: str) -> ImageContent:
    """Demonstrates returning a single ImageContentBlock. Generates a QR code PNG and returns it as a base64-encoded image."""
    logging.info(f"Generating QR code for text of length {len(text)}")
    
    try:
        import qrcode
        from qrcode.image.pil import PilImage
    except ImportError:
        logging.error("qrcode library not installed")
        raise Exception("qrcode library is required. Install with: pip install qrcode[pil]")
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()
    
    return ImageContent(
        type="image",
        data=base64.b64encode(png_bytes).decode('utf-8'),
        mimeType="image/png"
    )



# ============================================================================
# Snippet Data Class
# ============================================================================

@dataclass
@func.mcp_content
class Snippet:
    """
    Snippet model for structured content.
    
    This class demonstrates structured data handling in MCP tools:
    - When returned from a tool function, it's automatically serialized as structured content
    - Properties serve as documentation for the data structure
    """
    name: str
    """The name of the snippet"""
    
    content: Optional[str] = None
    """The code snippet content"""


# ============================================================================
# Advanced Snippet Tools
# ============================================================================

@app.mcp_tool()
@app.mcp_tool_property(arg_name="snippetname", description="The name of the snippet.", is_required=True)
def get_snippet_with_metadata(snippetname: str) -> CallToolResult:
    """
    Demonstrates returning both content blocks and structured metadata via CallToolResult.
    
    Returns a CallToolResult with:
    - content: List of ContentBlock objects (for backward compatibility)
    - structured_content: JSON metadata (for clients that support it)
    
    This pattern allows clients to choose between simple text content or
    richer structured data depending on their capabilities.
    """
    logging.info(f"Getting snippet with metadata: {snippetname}")
    
    # Try to read the snippet from blob storage
    snippet_content = None
    try:
        blob_service_uri = os.environ.get("AzureWebJobsStorage__blobServiceUri")
        
        if blob_service_uri:
            from azure.identity import DefaultAzureCredential
            credential = DefaultAzureCredential(
                managed_identity_client_id=os.environ.get("AzureWebJobsStorage__clientId")
            )
            blob_service_client = BlobServiceClient(blob_service_uri, credential=credential)
            container_client = blob_service_client.get_container_client("snippets")
            blob_client = container_client.get_blob_client(f"{snippetname}.json")
            
            blob_data = blob_client.download_blob()
            snippet_content = blob_data.readall().decode('utf-8')
    except Exception as ex:
        logging.warning(f"Could not read snippet '{snippetname}': {ex}")
    
    # Build metadata
    metadata = {
        "name": snippetname,
        "found": snippet_content is not None,
        "character_count": len(snippet_content) if snippet_content else 0,
        "retrieved_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Return CallToolResult with both content blocks and structured metadata
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=snippet_content if snippet_content else f"Snippet '{snippetname}' not found."
            ),
            TextContent(
                type="text",
                text=json.dumps(metadata, indent=2)
            )
        ],
        structured_content=metadata
    )


@app.mcp_tool()
@app.mcp_tool_property(
    arg_name="snippet_items",
    description="Array of snippet objects, each with 'name' and 'content' properties. Example: [{\"name\": \"example1\", \"content\": \"code here\"}, {\"name\": \"example2\", \"content\": \"code here\"}]",
    is_required=True
)
def batch_save_snippets(snippet_items) -> str:
    """
    Demonstrates batch tool inputs - saving multiple snippets in one operation.
    
    Accepts an array of snippet objects and saves each one to blob storage.
    This pattern is useful for bulk operations and reduces the number of
    tool invocations needed.
    
    Args:
        snippet_items: List of dicts with 'name' and 'content' keys (or JSON string)
        
    Returns:
        JSON string with summary of saved snippets
    """
    # Parse snippet_items if it's a string
    if isinstance(snippet_items, str):
        try:
            snippet_items = json.loads(snippet_items)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse snippet_items JSON: {e}")
            return json.dumps({
                "error": f"Invalid JSON format: {str(e)}"
            })
    
    logging.info(f"Batch saving {len(snippet_items)} snippets")
    
    try:
        blob_service_uri = os.environ.get("AzureWebJobsStorage__blobServiceUri")
        if not blob_service_uri:
            return json.dumps({
                "error": "AzureWebJobsStorage__blobServiceUri not configured"
            })
        
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential(
            managed_identity_client_id=os.environ.get("AzureWebJobsStorage__clientId")
        )
        blob_service_client = BlobServiceClient(blob_service_uri, credential=credential)
        container_client = blob_service_client.get_container_client("snippets")
        
        # Create container if it doesn't exist
        try:
            container_client.create_container()
        except:
            pass  # Container already exists
        
        saved_snippets = []
        
        for item in snippet_items:
            try:
                name = item.get("name")
                content = item.get("content", "")
                
                if not name:
                    logging.warning("Skipping snippet with no name")
                    continue
                
                blob_client = container_client.get_blob_client(f"{name}.json")
                blob_client.upload_blob(
                    content,
                    overwrite=True
                )
                saved_snippets.append(name)
                logging.info(f"Saved snippet: {name}")
                
            except Exception as ex:
                logging.error(f"Failed to save snippet {item.get('name', 'unknown')}: {ex}")
        
        result = {
            "message": f"Successfully saved {len(saved_snippets)} snippets",
            "snippets": saved_snippets
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as ex:
        logging.error(f"Batch save failed: {ex}")
        return json.dumps({
            "error": f"Batch save operation failed: {str(ex)}"
        })


@app.mcp_tool()
@app.mcp_tool_property(arg_name="name", description="The name of the snippet", is_required=True)
@app.mcp_tool_property(arg_name="content", description="The code snippet content", is_required=True)
def save_snippet_structured(name: str, content: str) -> Snippet:
    """
    Demonstrates returning a structured data class (Snippet POCO equivalent).
    
    When a dataclass is returned, it's automatically serialized as structured
    content, providing type information and documentation to MCP clients.
    This is the Python equivalent of the .NET [McpContent] pattern.
    
    Args:
        name: The snippet name
        content: The snippet content
        
    Returns:
        Snippet dataclass instance
    """
    logging.info(f"Saving snippet '{name}' as structured content")
    
    # Save to blob storage
    try:
        blob_service_uri = os.environ.get("AzureWebJobsStorage__blobServiceUri")
        if not blob_service_uri:
            logging.warning("AzureWebJobsStorage__blobServiceUri not configured")
            return Snippet(name=name, content=content)
        
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential(
            managed_identity_client_id=os.environ.get("AzureWebJobsStorage__clientId")
        )
        blob_service_client = BlobServiceClient(blob_service_uri, credential=credential)
        container_client = blob_service_client.get_container_client("snippets")
        blob_client = container_client.get_blob_client(f"{name}.json")
        blob_client.upload_blob(content, overwrite=True)
    except Exception as ex:
        logging.warning(f"Could not save to blob storage: {ex}")
    
    # Return structured Snippet object
    return Snippet(name=name, content=content)
