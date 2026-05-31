# FunctionsMcpTool — Remote MCP Server on Azure Functions (Python)

This project is a Python Azure Function app that exposes multiple MCP (Model Context Protocol) tools as a remote MCP server. It includes tools for snippets, QR code generation, structured metadata, batch operations, and more.

> **Note:** MCP resources are in the [FunctionsMcpResources](../FunctionsMcpResources/) project, and prompts are in the [FunctionsMcpPrompts](../FunctionsMcpPrompts/) project.

> [!NOTE]
> This project uses the **preview extension bundle** (`Microsoft.Azure.Functions.ExtensionBundle.Preview`) configured in `host.json`. The preview bundle is required because some return types (e.g., `CallToolResult`, `ImageContent`) are not yet supported in the standard bundle.

## Tools included

| Tool | Description |
|------|-------------|
| `hello_mcp` | Simple hello world tool |
| `hello_tool_with_auth` | Greets the signed-in user by name via Microsoft Graph (OBO flow) |
| `get_snippet` | Retrieves a code snippet from blob storage |
| `save_snippet` | Saves a code snippet to blob storage |
| `generate_qr_code` | Generates a QR code image from text |
| `generate_badge` | Generates an SVG status badge (List[ContentBlock]) |
| `get_website_preview` | Fetches website metadata and returns a resource link (List[ContentBlock]) |
| `get_snippet_with_metadata` | Retrieves a snippet with structured metadata (CallToolResult) |
| `batch_save_snippets` | Saves multiple snippets at once |
| `save_snippet_structured` | Saves a snippet and returns a structured dataclass |

## Prerequisites

- [Python](https://www.python.org/downloads/) version 3.13 or higher
- [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local?pivots=programming-language-python#install-the-azure-functions-core-tools) >= `4.8.0`
- [Azure Developer CLI (azd)](https://aka.ms/azd) **1.23.x or above** (for deployment)
- [Docker](https://www.docker.com/) (for the Azurite storage emulator)

## Prepare your local environment

An Azure Storage Emulator is needed because the snippet tools save and retrieve blobs from storage. Start Azurite:

```shell
docker run -d -p 10000:10000 -p 10001:10001 -p 10002:10002 \
    mcr.microsoft.com/azure-storage/azurite \
    azurite --skipApiVersionCheck --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0
```

> If you use the Azurite VS Code extension instead, run **Azurite: Start** now.

## Run locally

### 1. Install dependencies

From this directory (`src/FunctionsMcpTool`), create and activate a virtual environment, then install dependencies:

```shell
python3 -m venv .venv
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 2. Start the Functions host

```shell
func start
```

## Connect to the MCP server

### Option A: VS Code with GitHub Copilot

1. Open **`.vscode/mcp.json`** in the workspace root. Find the server called **`local-mcp-function`** and click **Start** above the name. It points to:

   ```
   http://localhost:7071/runtime/webhooks/mcp
   ```

2. In Copilot chat **agent** mode, try prompts like:

   ```
   Say Hello
   ```

   ```
   Save this snippet as snippet1
   ```

   ```
   Retrieve snippet1 and apply to NewFile.py
   ```

3. When prompted to run a tool, consent by clicking **Continue**.

4. Press `Ctrl+C` in the terminal to stop the function host when done.

### Option B: MCP Inspector

1. In a new terminal, install and run MCP Inspector:

   ```shell
   npx @modelcontextprotocol/inspector
   ```

2. Open the Inspector URL (e.g. `http://0.0.0.0:5173/#resources`).
3. Set the transport type to **Streamable HTTP**.
4. Set the URL to `http://0.0.0.0:7071/runtime/webhooks/mcp` and click **Connect**.
5. Click **List Tools**, select a tool, and **Run Tool**.

## Deploy to Azure

### Step 1: Sign in

```shell
az login
azd auth login
```

### Step 2: Create an environment

```shell
azd env new <environment-name>
```

This also becomes the resource group name.

### Step 3: Provision and deploy

By default, OAuth-based authentication is enabled using the [built-in MCP auth feature](https://learn.microsoft.com/azure/app-service/configure-authentication-mcp?toc=/azure/azure-functions/toc.json&bc=/azure/azure-functions/breadcrumb/toc.json) with Microsoft Entra as the identity provider.

Configure VS Code as an allowed client application for Microsoft Entra:

```shell
azd env set PRE_AUTHORIZED_CLIENT_IDS aebc6443-996d-45c2-90f0-388ff96faa56
```

Optionally enable VNet isolation:

```shell
azd env set VNET_ENABLED true
```

Deploy the project. When prompted, pick your subscription and an Azure region.

```shell
azd up
```

### Step 4: Connect to the remote MCP server

Open **`.vscode/mcp.json`** and click **Start** above **`remote-mcp-function`**. You'll be prompted for `functionapp-name` — find it in your `azd` command output or the `.azure/<env>/.env` file. Since authentication is enabled, you'll also be prompted to sign in with Microsoft.

> **Tip:** Click **More... → Show Output** above the server name to see request/response details.

### Redeploy and clean up

- **Redeploy:** `azd deploy`
- **Clean up all resources:** `azd down`

## Examining the code

Each tool is a Python function with an `@app.mcp_tool()` decorator that exposes it as an MCP tool:

### Basic Tool

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

### Rich Content Response — Single Image

```python
@app.mcp_tool()
@app.mcp_tool_property(arg_name="text", description="The text to encode in the QR code.", required=True)
def generate_qr_code(text: str) -> ImageContent:
    """Generates a QR code PNG and returns it as a base64-encoded image."""
    return ImageContent(
        type="image",
        data=base64.b64encode(png_bytes).decode('utf-8'),
        mimeType="image/png"
    )
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Connection refused locally | Ensure Azurite is running (`docker run -p 10000:10000 ...`) |
| API version not supported by Azurite | Add `--skipApiVersionCheck` flag to the Azurite command, or pull the latest image |
| `AttributeError: 'FunctionApp' object has no attribute 'mcp_resource_trigger'` | Python 3.13 is required. Verify with `python3 --version`. |
| `azd up` provision succeeded but deploy failed | Transient error — run `azd deploy` again |
