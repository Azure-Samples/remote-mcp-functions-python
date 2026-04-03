# FunctionsMcpTool - Snippet Management MCP Server

This Azure Functions app implements a simple MCP server with tools for managing code snippets using Azure Blob Storage.

## Features

This MCP server provides three tools:

- **hello_mcp**: A simple hello world tool for testing connectivity
- **get_snippet**: Retrieve a saved code snippet by name from Azure Blob Storage
- **save_snippet**: Save a code snippet with a name to Azure Blob Storage

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

From the `src/FunctionsMcpTool` directory:

```shell
pip install -r requirements.txt
```

> **Best practice**: Create a virtual environment before installing dependencies to avoid conflicts.

### 3. Run the Function App

```shell
func start
```

The MCP server will be available at `http://0.0.0.0:7071/runtime/webhooks/mcp`.

## Using the MCP Server

### Connect from VS Code - GitHub Copilot

1. **Add MCP Server** from the command palette
2. Add URL: `http://0.0.0.0:7071/runtime/webhooks/mcp`
3. **List MCP Servers** from the command palette and start the server
4. In Copilot chat agent mode, try these prompts:
   - "Say Hello"
   - "Save this snippet as snippet1" (with code selected)
   - "Retrieve snippet1 and apply to newFile.py"

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

```python
@app.mcp_tool()
def hello_mcp() -> str:
    """Hello world."""
    return "Hello I am MCPTool!"

@app.mcp_tool()
@app.mcp_tool_property(arg_name="snippetname", description="The name of the snippet.")
@app.blob_input(arg_name="file", connection="AzureWebJobsStorage", path=_BLOB_PATH)
def get_snippet(file: func.InputStream, snippetname: str) -> str:
    """Retrieve a snippet by name from Azure Blob Storage."""
    # ... implementation

@app.mcp_tool()
@app.mcp_tool_property(arg_name="snippetname", description="The name of the snippet.")
@app.mcp_tool_property(arg_name="snippet", description="The content of the snippet.")
@app.blob_output(arg_name="file", connection="AzureWebJobsStorage", path=_BLOB_PATH)
def save_snippet(file: func.Out[str], snippetname: str, snippet: str) -> str:
    """Save a snippet with a name to Azure Blob Storage."""
    # ... implementation
```

The MCP decorators automatically:
- Infer tool properties from function signatures and type hints
- Handle JSON serialization
- Expose the functions as MCP tools without manual configuration

## Deployment to Azure

To deploy this app to Azure, use `azd up` from the repository root. See the [main README](../../README.md) for complete deployment instructions.

## Troubleshooting

| Error | Solution |
|---|---|
| Connection refused | Ensure Azurite is running |
| API version not supported by Azurite | Pull the latest Azurite image and restart |
| Blob not found | Verify the snippet was saved successfully and the name matches exactly |
