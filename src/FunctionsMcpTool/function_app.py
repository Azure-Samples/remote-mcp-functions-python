import logging
import base64
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from io import BytesIO

import azure.functions as func
from mcp.types import ImageContent, TextContent, ContentBlock, ResourceLink, CallToolResult
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


@app.mcp_tool()
@app.mcp_tool_property(arg_name="label", description="The label text for the badge.", is_required=True)
@app.mcp_tool_property(arg_name="value", description="The value text for the badge.", is_required=True)
@app.mcp_tool_property(arg_name="color", description="The hex color for the value section (e.g., '#4CAF50').", is_required=False)
def generate_badge(label: str, value: str, color: str = "#4CAF50") -> List[ContentBlock]:
    """Demonstrates returning multiple content blocks (List[ContentBlock]). Generates an SVG status badge and returns it alongside a text description."""
    logging.info(f"Generating badge: {label} | {value}")
    
    label_width = len(label) * 7 + 12
    value_width = len(value) * 7 + 12
    total_width = label_width + value_width
    
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20">
  <rect width="{label_width}" height="20" fill="#555"/>
  <rect x="{label_width}" width="{value_width}" height="20" fill="{color}"/>
  <text x="{label_width // 2}" y="14" fill="#fff" text-anchor="middle"
        font-family="Verdana,sans-serif" font-size="11">{label}</text>
  <text x="{label_width + value_width // 2}" y="14" fill="#fff" text-anchor="middle"
        font-family="Verdana,sans-serif" font-size="11">{value}</text>
</svg>"""
    
    return [
        TextContent(type="text", text=f"Badge: {label} — {value}"),
        ImageContent(
            type="image",
            data=base64.b64encode(svg.encode('utf-8')).decode('utf-8'),
            mimeType="image/svg+xml"
        )
    ]


@app.mcp_tool()
@app.mcp_tool_property(arg_name="url", description="The URL of the website to preview.", is_required=True)
async def get_website_preview(url: str) -> List[ContentBlock]:
    """Demonstrates returning TextContentBlock and ResourceLinkBlock together. Fetches basic metadata from a URL and returns it with a resource link."""
    import aiohttp
    import html
    
    logging.info(f"Fetching website preview for {url}")
    
    # Ensure URL has a protocol
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
        logging.info(f"Added https:// protocol to URL: {url}")
    
    title = url
    description = "No description available."
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), 
                                  headers={"User-Agent": "MCPTool/1.0"}) as response:
                html_content = await response.text()
                
                # Extract title
                title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE)
                if title_match:
                    title = html.unescape(title_match.group(1)).strip()
                
                # Extract description
                desc_match = re.search(
                    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\'\']',
                    html_content,
                    re.IGNORECASE
                )
                if desc_match:
                    description = html.unescape(desc_match.group(1)).strip()
    
    except Exception as ex:
        logging.warning(f"Failed to fetch metadata for {url}: {ex}")
        description = f"Could not fetch metadata: {str(ex)}"
    
    return [
        TextContent(type="text", text=f"{title}\n\n{description}"),
        ResourceLink(
            type="resource_link",
            uri=url,
            name=title,
            description=description
        )
    ]


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
        connection_string = os.environ.get("AzureWebJobsStorage")
        if connection_string:
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
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
        connection_string = os.environ.get("AzureWebJobsStorage")
        if not connection_string:
            return json.dumps({
                "error": "AzureWebJobsStorage connection string not configured"
            })
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
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
        connection_string = os.environ.get("AzureWebJobsStorage")
        if connection_string:
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            container_client = blob_service_client.get_container_client("snippets")
            blob_client = container_client.get_blob_client(f"{name}.json")
            blob_client.upload_blob(content, overwrite=True)
    except Exception as ex:
        logging.warning(f"Could not save to blob storage: {ex}")
    
    # Return structured Snippet object
    return Snippet(name=name, content=content)
