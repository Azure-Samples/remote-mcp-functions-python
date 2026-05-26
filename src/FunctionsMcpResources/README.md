# FunctionsMcpResources — MCP Resource Templates on Azure Functions (Python)

This project is a Python Azure Function app that exposes MCP (Model Context Protocol) resource templates as a remote MCP server. Resource templates allow MCP clients to discover and read structured data through URI-based patterns.

> **Note:** MCP tools are in the [FunctionsMcpTool](../FunctionsMcpTool/) project, and prompts are in the [FunctionsMcpPrompts](../FunctionsMcpPrompts/) project.

## Resources included

| Resource | URI | Description |
|----------|-----|-------------|
| `Snippet` | `snippet://{Name}` | Resource template that reads a code snippet by name from blob storage. Clients discover it via `resources/templates/list` and substitute the `Name` parameter. |
| `ServerInfo` | `info://server` | Static resource that returns server name, version, runtime, and timestamp. |

## Key concepts

- **Resource templates** have URI parameters (e.g., `{Name}`) that clients substitute at runtime — they're like parameterized endpoints.
- **Static resources** have fixed URIs and return the same structure every call.
- **Resource metadata** (like cache TTL) can be passed in the `metadata` parameter of the `@app.mcp_resource_trigger` decorator.

> [!NOTE]
> This project uses the **preview extension bundle** (`Microsoft.Azure.Functions.ExtensionBundle.Preview`) configured in `host.json`. The preview bundle is required because resource templates with URI parameters (e.g., `snippet://{Name}`) are not yet supported in the standard bundle.

## Prerequisites

- [Python 3.13+](https://www.python.org/downloads/)
- [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local?pivots=programming-language-python#install-the-azure-functions-core-tools) >= `4.8.0`
- [Azure Developer CLI (azd)](https://aka.ms/azd) **1.23.x or above** (for deployment)
- [Docker](https://www.docker.com/) (for the Azurite storage emulator — needed by the snippet resource template)

## Prepare your local environment

An Azure Storage Emulator is needed because the snippet resource reads blobs from storage. Start Azurite:

```shell
docker run -d -p 10000:10000 -p 10001:10001 -p 10002:10002 \
    mcr.microsoft.com/azure-storage/azurite \
    azurite --skipApiVersionCheck --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0
```

> If you use the Azurite VS Code extension instead, run **Azurite: Start** now.

## Run locally

### 1. Install dependencies

Create and activate a virtual environment, then install dependencies:

```shell
python3 -m venv .venv
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 2. Start the Functions host

From this directory (`src/FunctionsMcpResources`), start the Functions host:

```shell
func start
```

The MCP endpoint will be available at `http://localhost:7071/runtime/webhooks/mcp`.

### 3. Seed a snippet using the `save_snippet` tool

This project includes a `save_snippet` MCP tool that writes snippets to blob storage. Use it to seed data before reading resources. For example, from VS Code Chat or MCP Inspector:

> "Save a snippet called HelloWorld with the content: print('Hello, World!')"

This creates a blob at `snippets/HelloWorld.json` which can then be read via the `snippet://HelloWorld` resource.

## Connect to the MCP server

### Option A: VS Code with GitHub Copilot

Open **`.vscode/mcp.json`** in the workspace root. Find the server called **`local-mcp-function`** and click **Start**. It points to:

```
http://localhost:7071/runtime/webhooks/mcp
```

MCP resources are attached as context in VS Code Chat (they aren't invoked like tools or prompts):

1. Open the **Chat** panel.
2. Click the **+** (Attach) button in the chat input.
3. Select **MCP Resources**.
4. Choose a resource:
   - **`ServerInfo`** — no parameters needed. Returns server name, version, runtime, and timestamp.
   - **`Snippet`** — enter a snippet name (e.g., `HelloWorld`). Reads the matching blob from storage.
5. The resource content is attached to the conversation as context for the model.

### Option B: MCP Inspector

1. Install and run MCP Inspector:

   ```shell
   npx @modelcontextprotocol/inspector
   ```

2. Open the Inspector URL (e.g. `http://0.0.0.0:5173/#resources`).
3. Set the transport type to **Streamable HTTP**.
4. Set the URL to `http://0.0.0.0:7071/runtime/webhooks/mcp` and click **Connect**.
5. Click **List Resources** or **List Resource Templates** to browse available resources.

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

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Connection refused locally | Ensure Azurite is running (`docker run -p 10000:10000 ...`) |
| API version not supported by Azurite | Add `--skipApiVersionCheck` flag to the Azurite command, or pull the latest image |
| `AttributeError: 'FunctionApp' object has no attribute 'mcp_resource_trigger'` | Python 3.13 is required. Verify with `python3 --version`. |
| `azd up` provision succeeded but deploy failed | Transient error — run `azd deploy` again |
