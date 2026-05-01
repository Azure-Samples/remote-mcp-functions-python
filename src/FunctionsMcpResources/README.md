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

## Run locally

### 1. Start Azurite (required for the snippet resource which uses blob storage)

```bash
docker run -d -p 10000:10000 -p 10001:10001 -p 10002:10002 \
  mcr.microsoft.com/azure-storage/azurite
```

### 2. Upload sample snippets to Azurite

Once Azurite is running, you need to upload the sample snippet files to blob storage. You can use [Azure Storage Explorer](https://azure.microsoft.com/features/storage-explorer/) or the Azure CLI:

```bash
# Using Azure CLI with Azurite connection string
az storage container create --name snippets \
  --connection-string "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"

# Upload sample snippets
az storage blob upload-batch --source ../../__queuestorage__/snippets \
  --destination snippets \
  --connection-string "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
```

### 3. Start the Functions host

From this directory (`src/FunctionsMcpResources`), start the Functions host:

```bash
func start
```

The MCP endpoint will be available at `http://localhost:7073/runtime/webhooks/mcp`.

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

Three sample snippets are included in `__queuestorage__/snippets/`:

1. **HelloWorld.json** - A simple Hello World function
2. **QuickSort.json** - QuickSort algorithm implementation
3. **FibonacciSequence.json** - Fibonacci sequence generator

You can add more snippets by creating JSON files in the same format and uploading them to the blob storage container.

## Related documentation

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Azure Functions Python Developer Guide](https://learn.microsoft.com/azure/azure-functions/functions-reference-python)
- [Azure Functions Blob Storage Bindings](https://learn.microsoft.com/azure/azure-functions/functions-bindings-storage-blob)
