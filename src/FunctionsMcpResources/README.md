# FunctionsMcpResources — MCP Resource Templates on Azure Functions (Python)

This project is a Python Azure Function app that exposes MCP (Model Context Protocol) resource templates as a remote MCP server. Resource templates allow MCP clients to discover and read structured data through URI-based patterns.

> **Note:** MCP tools are in the [FunctionsMcpTool](../FunctionsMcpTool) project, and prompts are in the [FunctionsMcpPrompts](../FunctionsMcpPrompts) project.

## Resources included

| Resource | URI | Description |
|----------|-----|-------------|
| `Snippet` | `snippet://{Name}` | Resource template that reads a code snippet by name from blob storage. Clients discover it via `resources/templates/list` and substitute the `Name` parameter. |
| `ServerInfo` | `info://server` | Static resource that returns server name, version, runtime, and timestamp. |

## Key concepts

- **Resource templates** have URI parameters (e.g., `{Name}`) that clients substitute at runtime — they're like parameterized endpoints.
- **Static resources** have fixed URIs and return the same structure every call.
- **Resource metadata** (like cache TTL) can be passed in the `metadata` parameter of the `@app.mcp_resource_trigger` decorator.

## Prerequisites

- [Python 3.13+](https://www.python.org/downloads/)
- [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local?pivots=programming-language-python#install-the-azure-functions-core-tools) >= `4.5.0`
- [Docker](https://www.docker.com/) (for the Azurite storage emulator — needed by the snippet resource template)

> **Important:** This project uses the **preview extension bundle** (`Microsoft.Azure.Functions.ExtensionBundle.Preview`) configured in `host.json`. The preview bundle is required because resource templates with URI parameters (e.g., `snippet://{Name}`) are not yet supported in the standard bundle.

## Run locally

### 1. Start Azurite (required for the snippet resource which uses blob storage)

```bash
docker run -d -p 10000:10000 -p 10001:10001 -p 10002:10002 \
  mcr.microsoft.com/azure-storage/azurite \
  azurite --skipApiVersionCheck --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0
```

> **Note:** The `--skipApiVersionCheck` flag is required because the `azure-storage-blob` Python SDK uses a newer API version than Azurite currently supports.

### 2. Install dependencies

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Start the Functions host

From this directory (`src/FunctionsMcpResources`), start the Functions host:

```bash
func start
```

The MCP endpoint will be available at `http://localhost:7071/runtime/webhooks/mcp`.

### 4. Seed a snippet using the `save_snippet` tool

This project includes a `save_snippet` MCP tool that writes snippets to blob storage. Use it to seed data before reading resources. For example, from VS Code Chat or MCP Inspector:

> "Save a snippet called HelloWorld with the content: print('Hello, World!')"

This creates a blob at `snippets/HelloWorld.json` which can then be read via the `snippet://HelloWorld` resource.

## Connect from VS Code

The [.vscode/mcp.json](../../.vscode/mcp.json) in the workspace root is already configured with a local server entry pointing to `http://localhost:7071/runtime/webhooks/mcp`. Click **Start** above the `local-mcp-function` server name.

MCP resources are attached as context in VS Code Chat (they aren't invoked like tools or prompts):

1. Open the **Chat** panel.
2. Click the **+** (Attach) button in the chat input.
3. Select **MCP Resources**.
4. Choose a resource:
   - **`ServerInfo`** — no parameters needed. Returns server name, version, runtime, and timestamp.
   - **`Snippet`** — enter a snippet name (e.g., `HelloWorld`). Reads the matching blob from storage.
5. The resource content is attached to the conversation as context for the model.

## Deploy to Azure

From the repository root, use `azd` to deploy:

```bash
azd env set DEPLOY_SERVICE resources
azd provision
azd deploy --service resources
```

## Examining the code

Resources are defined in [function_app.py](function_app.py). Each resource is a Python function with an `@app.mcp_resource_trigger` decorator:

### Resource Template (with URI parameter)

```python
@app.mcp_resource_trigger(
    arg_name="context",
    uri="snippet://{Name}",
    resource_name="Snippet",
    description="Reads a code snippet by name from blob storage.",
    mime_type="application/json"
)
@app.blob_input(
    arg_name="snippet_content",
    path="snippets/{mcpresourceargs.Name}.json",
    connection="AzureWebJobsStorage"
)
def get_snippet_resource(context, snippet_content: Optional[bytes]) -> str:
    # The {mcpresourceargs.Name} binding expression automatically extracts
    # the Name parameter from the resource URI and passes it to the blob binding
    if snippet_content is None:
        return json.dumps({"error": "Snippet not found"})
    return snippet_content.decode('utf-8')
```

The `{mcpresourceargs.Name}` binding expression automatically extracts the `Name` parameter from the resource URI and passes it to the blob input binding.

### Static Resource (no parameters)

```python
@app.mcp_resource_trigger(
    arg_name="context",
    uri="info://server",
    resource_name="ServerInfo",
    description="Returns information about the MCP server.",
    mime_type="application/json",
    metadata=json.dumps({"cache": {"ttlSeconds": 60}})
)
def get_server_info(context) -> str:
    server_info = {
        "name": "FunctionsMcpResources",
        "version": "1.0.0",
        "runtime": f"Python {platform.python_version()}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return json.dumps(server_info)
```

## Testing the resources

### Using MCP Inspector

Install and use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to test your resources:

```bash
npx @modelcontextprotocol/inspector http://localhost:7073/runtime/webhooks/mcp
```

### Using curl

Test the ServerInfo static resource:

```bash
curl -X POST http://localhost:7073/runtime/webhooks/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "resources/read",
    "params": {
      "uri": "info://server"
    }
  }'
```

List available resource templates:

```bash
curl -X POST http://localhost:7073/runtime/webhooks/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "resources/templates/list"
  }'
```

Read a specific snippet:

```bash
curl -X POST http://localhost:7073/runtime/webhooks/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "resources/read",
    "params": {
      "uri": "snippet://HelloWorld"
    }
  }'
```

## Architecture

```
┌─────────────────┐
│   MCP Client    │
│  (e.g., Agent)  │
└────────┬────────┘
         │
         │ HTTP
         │
┌────────▼────────────────────────┐
│   Azure Functions (Python)      │
│  ┌──────────────────────────┐   │
│  │  get_snippet_resource    │   │
│  │  (Resource Template)     │   │
│  └──────────┬───────────────┘   │
│             │                   │
│             │ Blob Binding      │
│             │                   │
│  ┌──────────▼───────────────┐   │
│  │   Azure Blob Storage     │   │
│  │   (snippets container)   │   │
│  └──────────────────────────┘   │
│                                 │
│  ┌──────────────────────────┐   │
│  │   get_server_info        │   │
│  │   (Static Resource)      │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

## Sample snippets

You can seed any JSON snippet into blob storage. The snippet name is determined by the blob filename (without the `.json` extension). For example, uploading `HelloWorld.json` makes it available at `snippet://HelloWorld`.

Example snippet format:

```json
{"name": "HelloWorld", "language": "python", "code": "print('Hello, World!')"}
```

You can add more snippets by creating JSON files and uploading them to the `snippets` blob container.

## Related documentation

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Azure Functions Python Developer Guide](https://learn.microsoft.com/azure/azure-functions/functions-reference-python)
- [Azure Functions Blob Storage Bindings](https://learn.microsoft.com/azure/azure-functions/functions-bindings-storage-blob)
