# FunctionsMcpTool - MCP Server Sample

This Azure Functions app implements an MCP server that demonstrates various tool patterns, including rich content responses, structured data, batch operations, and Azure Blob Storage integration. It provides comprehensive examples of MCP capabilities on Azure Functions.

## Features

This MCP server provides the following tools organized by category:

### Basic Tools

- **hello_mcp**: Simple hello world tool for testing connectivity
- **get_snippet**: Retrieve a saved code snippet by name from Azure Blob Storage
- **save_snippet**: Save a code snippet with a name to Azure Blob Storage

### Rich Content Tools

- **generate_qr_code**: Generates a QR code PNG from text and returns it as base64-encoded `ImageContent` (demonstrates single image response)
- **generate_badge**: Creates an SVG status badge and returns it with a text description (demonstrates multiple `ContentBlock` responses)
- **get_website_preview**: Fetches a website's title/description and returns it with a `ResourceLink` (demonstrates `TextContent` + `ResourceLinkBlock`)

### Advanced Snippet Tools

- **get_snippet_with_metadata**: Returns snippet content plus structured JSON metadata (demonstrates content blocks with structured data)
- **batch_save_snippets**: Saves multiple snippets in a single operation (demonstrates batch/array tool inputs)
- **save_snippet_structured**: Saves a snippet and returns a structured `Snippet` object (demonstrates POCO/dataclass pattern)

## Prerequisites

- [Python](https://www.python.org/downloads/) version 3.13 or higher
- [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local?pivots=programming-language-python#install-the-azure-functions-core-tools) >= `4.8.0`
- Azure Storage Emulator (Azurite) for local development

## Local Development

### 1. Start Azurite

An Azure Storage Emulator is needed to store snippets locally:

```shell
docker run -p 10000:10000 -p 10001:10001 -p 10002:10002 \
    mcr.microsoft.com/azure-storage/azurite
```

> **Note**: If using the Azurite VS Code extension, run `Azurite: Start` from the command palette.

### 2. Install Dependencies

From the `src/FunctionsMcpTool` directory, create and activate a virtual environment, then install dependencies:

```shell
python3 -m venv .venv

# macOS/Linux
source .venv/bin/activate    

# Windows
.venv\Scripts\activate  

pip install -r requirements.txt
```

### 3. Run the Function App

```shell
func start
```

## Using the MCP Server

### Connect from VS Code - GitHub Copilot

1. Open [.vscode/mcp.json](../../.vscode/mcp.json)
2. Find the server called `local-mcp-function` and click **Start**. The server uses the endpoint: `http://localhost:7071/runtime/webhooks/mcp`
3. In Copilot chat agent mode, try these prompts:
   
   **Basic Tools:**
   - "Say Hello"
   - "Save this snippet as snippet1" (with code selected)
   - "Retrieve snippet1 and apply to newFile.py"
   
   **Rich Content Tools:**
   - "Generate a QR code for https://example.com"
   - "Create a badge with label 'build' and value 'passing'"
   - "Get a preview of https://github.com"
   
   **Advanced Tools:**
   - "Get snippet1 with metadata"
   - "Batch save these snippets: [{'name': 'test1', 'content': 'code1'}, {'name': 'test2', 'content': 'code2'}]"

### Connect from MCP Inspector

1. Install and run MCP Inspector:
   ```shell
   npx @modelcontextprotocol/inspector
   ```
2. Open the URL displayed (e.g., http://0.0.0.0:5173/#resources)
3. Set transport type to `Streamable HTTP`
4. Set URL to `http://0.0.0.0:7071/runtime/webhooks/mcp` and **Connect**
5. **List Tools**, select a tool, and **Run Tool**

## Verify Local Storage

After saving snippets, verify they're stored in Azurite:

### Using Azure Storage Explorer

1. Open Azure Storage Explorer
2. Navigate to **Emulator & Attached** → **Storage Accounts** → **(Emulator - Default Ports) (Key)**
3. Go to **Blob Containers** → **snippets**
4. View your saved snippet blobs

### Using Azure CLI

```shell
# List blobs in the snippets container
az storage blob list --container-name snippets --connection-string "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
```

## How It Works

The function uses Azure Functions' first-class MCP decorators to expose tools:

### Basic Tool Example

```python
@app.mcp_tool()
def hello_mcp() -> str:
    """Hello world."""
    return "Hello I am MCPTool!"
```

### Blob Storage Integration

```python
@app.mcp_tool()
@app.mcp_tool_property(arg_name="snippetname", description="The name of the snippet.")
@app.blob_input(arg_name="file", connection="AzureWebJobsStorage", path=_BLOB_PATH)
def get_snippet(file: func.InputStream, snippetname: str) -> str:
    """Retrieve a snippet by name from Azure Blob Storage."""
    snippet_content = file.read().decode("utf-8")
    return snippet_content
```

### Rich Content Response - Single Image

```python
@app.mcp_tool()
@app.mcp_tool_property(arg_name="text", description="The text to encode in the QR code.", required=True)
def generate_qr_code(text: str) -> ImageContent:
    """Generates a QR code PNG and returns it as a base64-encoded image."""
    # Generate QR code...
    return ImageContent(
        type="image",
        data=base64.b64encode(png_bytes).decode('utf-8'),
        mimeType="image/png"
    )
```

### Rich Content Response - Multiple Content Blocks

```python
@app.mcp_tool()
@app.mcp_tool_property(arg_name="label", description="The label text for the badge.", required=True)
@app.mcp_tool_property(arg_name="value", description="The value text for the badge.", required=True)
def generate_badge(label: str, value: str, color: str = "#4CAF50") -> List[ContentBlock]:
    """Generates an SVG badge and returns it alongside a text description."""
    return [
        TextContent(type="text", text=f"Badge: {label} — {value}"),
        ImageContent(
            type="image",
            data=base64.b64encode(svg.encode('utf-8')).decode('utf-8'),
            mimeType="image/svg+xml"
        )
    ]
```

### Structured Content with Metadata

```python
@app.mcp_tool()
@app.mcp_tool_property(arg_name="snippetname", description="The name of the snippet.", required=True)
def get_snippet_with_metadata(snippetname: str) -> Dict[str, Any]:
    """Returns both content blocks and structured metadata."""
    metadata = {
        "name": snippetname,
        "found": snippet_content is not None,
        "character_count": len(snippet_content) if snippet_content else 0,
        "retrieved_at": datetime.now(timezone.utc).isoformat()
    }
    
    return {
        "content": [
            {"type": "text", "text": snippet_content or "Not found"},
            {"type": "text", "text": json.dumps(metadata, indent=2)}
        ],
        "structured_content": metadata
    }
```

### Batch Operations

```python
@app.mcp_tool()
@app.mcp_tool_property(
    arg_name="snippet_items",
    description="Array of snippet objects with 'name' and 'content' properties",
    required=True
)
async def batch_save_snippets(snippet_items: List[Dict[str, str]]) -> str:
    """Saves multiple snippets in a single operation."""
    # Save each snippet to blob storage...
    return json.dumps({
        "message": f"Successfully saved {len(saved_snippets)} snippets",
        "snippets": saved_snippets
    })
```

### Structured Data Class (POCO Pattern)

```python
@dataclass
class Snippet:
    """Snippet model for structured content."""
    name: str
    content: Optional[str] = None

@app.mcp_tool()
@app.mcp_tool_property(arg_name="name", description="The name of the snippet", required=True)
@app.mcp_tool_property(arg_name="content", description="The code snippet content", required=True)
def save_snippet_structured(name: str, content: str) -> Snippet:
    """Returns a structured dataclass instance."""
    # Save to storage...
    return Snippet(name=name, content=content)
```

The MCP decorators automatically:
- Infer tool properties from function signatures and type hints
- Handle JSON serialization for rich content types
- Support batch operations with array/object inputs
- Expose the functions as MCP tools without manual configuration

## Deployment to Azure

See [Deploy to Azure for Remote MCP](../../README.md#deploy-to-azure-for-remote-mcp) for deployment instructions. 

## Troubleshooting

## Troubleshooting

| Error | Solution |
|---|---|
| `AttributeError: 'FunctionApp' object has no attribute 'mcp_resource_trigger'` | Python 3.13 is required. Verify with `python3 --version`. Install via `brew install python@3.13` (macOS) or from [python.org](https://www.python.org/downloads/). Recreate your virtual environment with Python 3.13 after installing. |
| Connection refused | Ensure Azurite is running (`docker run -p 10000:10000 -p 10001:10001 -p 10002:10002 mcr.microsoft.com/azure-storage/azurite`) |
| API version not supported by Azurite | Pull the latest Azurite image (`docker pull mcr.microsoft.com/azure-storage/azurite`) then restart Azurite and the app |
| Blob not found | Verify the snippet was saved successfully and the name matches exactly |
