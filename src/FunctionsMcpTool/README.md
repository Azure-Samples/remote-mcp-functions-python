# FunctionsMcpTool — Remote MCP Server on Azure Functions (Python)

This project is a Python Azure Function app that exposes multiple MCP (Model Context Protocol) tools as a remote MCP server. It includes tools for snippets, QR code generation, badges, structured metadata, batch operations, and a **hello with auth** tool that demonstrates the On-Behalf-Of (OBO) flow to call Microsoft Graph as the signed-in user.

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

This project requires OAuth-based authentication through the [built-in MCP auth feature](https://learn.microsoft.com/azure/app-service/configure-authentication-mcp?toc=/azure/azure-functions/toc.json&bc=/azure/azure-functions/breadcrumb/toc.json) with Microsoft Entra as the identity provider, and it is enabled by default. 

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

### Step 4: Consent to the application

The `hello_tool_with_auth` tool requires consent for delegated permission to access Microsoft Graph. For testing, you can grant consent just for yourself by logging into the application in a browser. See [Consent authoring](#consent-authoring) for how you would handle this for production scenarios.

Navigate to the `/.auth/login/aad` endpoint of your deployed function app. For example, if your function app is at `https://my-mcp-function-app.azurewebsites.net`, navigate to:

```
https://my-mcp-function-app.azurewebsites.net/.auth/login/aad
```

Sign in with your Azure subscription email and accept the permissions prompt. This completes the consent flow for you.

### Step 5: Connect to the remote MCP server

Open **`.vscode/mcp.json`** and click **Start** above **`remote-mcp-function`**. You'll be prompted for `functionapp-name` — find it in your `azd` command output or the `.azure/<env>/.env` file. You'll also be prompted to authenticate with Microsoft — click **Allow** and sign in.

> **Tip:** A successful connection shows the number of tools the server exposes. Click **More... → Show Output** above the server name to see request/response details.

> If you run into issues, see the [Troubleshooting](#troubleshooting) section below.

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

### Calling Microsoft Graph with the On-Behalf-Of flow (`hello_tool_with_auth`)

The `hello_tool_with_auth` tool (in [`hello_tool_with_auth.py`](hello_tool_with_auth.py)) demonstrates how to call a downstream API (Microsoft Graph) **as the signed-in user** using the On-Behalf-Of (OBO) flow.

**Local development** falls back to your local developer identity (Azure CLI, azd, etc.):

```python
if is_local:
    credential = ChainedTokenCredential(
        AzureCliCredential(),
        AzureDeveloperCliCredential(),
    )
else:
    credential = _build_obo_credential(context)
```

**In production**, the `_build_obo_credential` function exchanges the user's auth token for a Microsoft Graph token using three pieces of information:

1. **The user's bearer token** — extracted from the `X-MS-TOKEN-AAD-ACCESS-TOKEN` header (or `Authorization` fallback)
2. **The user's tenant ID** — decoded from the `X-MS-CLIENT-PRINCIPAL` header
3. **A client assertion** — obtained from a managed identity with a federated credential, proving the app's identity without a client secret

```python
def _build_obo_credential(context):
    # Extract headers from MCP context
    headers = context.get("HttpTransport", {}).get("Headers", {})

    user_token = headers.get("X-MS-TOKEN-AAD-ACCESS-TOKEN", "")
    tenant_id = ...  # decoded from X-MS-CLIENT-PRINCIPAL

    managed_identity = ManagedIdentityCredential(client_id=federated_mi_client_id)

    def client_assertion_func():
        return managed_identity.get_token("api://AzureADTokenExchange/.default").token

    return OnBehalfOfCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_assertion_func=client_assertion_func,
        user_assertion=user_token,
    )
```

The resulting credential is then used to call Microsoft Graph `/me` and greet the user by name:

```python
token = credential.get_token("https://graph.microsoft.com/.default")
async with aiohttp.ClientSession() as session:
    async with session.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {token.token}"},
    ) as resp:
        me = await resp.json()
        return f"Hello, {me['displayName']} ({me['mail']})!"
```

## Consent authoring

In the steps described for this example, you consented to the application by signing into it in a browser. This allowed the application to request delegated permissions to the Microsoft Graph. There are two main ways that consent can be handled:

- **User consent** — This is the approach used in the example above. Each user signs into the application and consents to the permissions requested. They can only do this for themselves, unless they are a tenant administrator with the ability to consent on behalf of others. In this sample, user consent is appropriate because it allows you to quickly test things without impacting other users. However, the way user consent is authored in this sample does not reflect how you would typically do it in a production scenario. This is described in more detail below.

- **Admin consent** — A tenant administrator can consent to the application on behalf of all users when they sign in and review the permissions. Once this is done, individual users can sign in without needing to consent themselves. This approach is more scalable and ensures that all users can access the application without running into consent issues. For the purposes of a sample, admin consent is not appropriate, but it is a great choice for production scenarios.

The user consent approach for this sample is a separate login because the sample uses Visual Studio Code as the client. Although Visual Studio Code is pre-authorized to our application, that only creates consent for the user to call the MCP server. It doesn't create consent for the MCP server to call the Microsoft Graph on behalf of the user. When we log into the application directly, we request Microsoft Graph permissions as part of a combined consent experience.

The main difference is that because Visual Studio Code is using a single sign-on flow, it only requests a token for the MCP server. It does not present an opportunity for the user to interactively consent to any permissions needed for or by the MCP server. If you built a client that used an interactive login of some kind, you could have it all handled entirely by that client. It would not be necessary to have a separate browser login.

See [Overview of permissions and consent in the Microsoft identity platform](https://learn.microsoft.com/en-us/entra/identity-platform/permissions-consent-overview) for additional information on how Entra ID handles consent.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Connection refused locally | Ensure Azurite is running (`docker run -p 10000:10000 ...`) |
| API version not supported by Azurite | Add `--skipApiVersionCheck` flag to the Azurite command, or pull the latest image |
| `hello_tool_with_auth` fails locally | Ensure you're signed in with `az login` or `azd auth login` |
| OBO errors in production | Verify that consent has been granted (see Step 4) and that the Entra app registration is configured correctly |
| `An error occurred invoking 'hello_tool_with_auth'` right after `azd up` | Restart the function app: `az functionapp restart -g <resource-group> -n <function-app-name>`. The OBO flow signs a client assertion with the user-assigned managed identity via a federated identity credential (FIC). Right after provisioning, the auth runtime can hold a stale signing credential while the FIC propagates in Entra. Check **Application Insights > Logs** for `AADSTS50013: Assertion failed signature validation` to confirm. |
| Generic "An error occurred invoking" with no details | Check **Application Insights > Logs** and query `exceptions \| where timestamp > ago(1h) \| project timestamp, outerMessage, innermostMessage` to find the actual error. |
| `AttributeError: 'FunctionApp' object has no attribute 'mcp_resource_trigger'` | Python 3.13 is required. Verify with `python3 --version`. |
| `azd up` provision succeeded but deploy failed | Transient error — run `azd deploy` again |
