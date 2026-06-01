"""
On-Behalf-Of (OBO) auth tool — calls Microsoft Graph as the signed-in user.

In production (with built-in MCP auth), the user's token arrives via HTTP
headers. This tool exchanges that token for a Graph token using the OBO flow,
then calls Graph's /me endpoint as that user.

In local development, falls back to the developer's local identity
(az login, VS Code, etc.).
"""

import base64
import json
import logging
import os

import azure.functions as func
from azure.functions.mcp import MCPToolContext

bp = func.Blueprint()


@bp.mcp_tool()
async def hello_tool_with_auth(context: MCPToolContext) -> str:
    """Greets the signed-in user by name using the On-Behalf-Of (OBO) flow to call Microsoft Graph.

    In production (with built-in MCP auth), the user's
    token arrives via HTTP headers. This tool exchanges that token for a Graph
    token using the OBO flow, then calls Graph's /me endpoint as that user.

    In local development, falls back to the developer's local identity
    (az login, VS Code, etc.).
    """
    from azure.identity import (
        AzureCliCredential,
        AzureDeveloperCliCredential,
        ChainedTokenCredential,
    )

    graph_scopes = ["https://graph.microsoft.com/.default"]
    is_local = os.environ.get("AZURE_FUNCTIONS_ENVIRONMENT") == "Development"

    if is_local:
        # Locally, use whatever developer identity is signed in.
        credential = ChainedTokenCredential(
            AzureCliCredential(),
            AzureDeveloperCliCredential(),
        )
    else:
        # In production, exchange the user's token for a Graph token via OBO.
        credential = _build_obo_credential(context)

    # Call Microsoft Graph /me
    try:
        import asyncio
        import aiohttp

        token = await asyncio.to_thread(credential.get_token, *graph_scopes)
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {token.token}"},
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logging.error(f"Graph API error ({resp.status}): {body}")
                    return f"Graph API error ({resp.status}): {body}"
                me = await resp.json()
                display_name = me.get("displayName", "Unknown")
                mail = me.get("mail") or me.get("userPrincipalName", "")
                return f"Hello, {display_name} ({mail})!"

    except Exception as ex:
        logging.error(f"Failed to call Microsoft Graph: {ex}", exc_info=True)
        return f"Failed to call Microsoft Graph: {ex}"


def _build_obo_credential(context):
    """Build an OnBehalfOfCredential from Easy Auth headers in the MCP context.

    The OBO flow exchanges the user's token for a downstream token (e.g. Graph)
    using three pieces of information:
      1. The user's bearer token (from X-MS-TOKEN-AAD-ACCESS-TOKEN header)
      2. The user's tenant ID (from X-MS-CLIENT-PRINCIPAL header)
      3. A client assertion proving this app's identity (via managed identity
         with a federated credential)
    """
    from azure.identity import ManagedIdentityCredential, OnBehalfOfCredential

    # Extract HTTP headers from the MCP transport context.
    # MCPToolContext is a Dict with structure: {transport: {properties: {headers: {...}}}}
    headers = (
        context.get("transport", {}).get("properties", {}).get("headers", {})
    )

    # 1. Get the user's access token
    user_token = headers.get("X-MS-TOKEN-AAD-ACCESS-TOKEN", "")
    if not user_token:
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            user_token = auth_header[len("Bearer "):]

    if not user_token:
        raise ValueError(
            "No user access token found. Ensure built-in MCP auth is enabled with the token store turned on."
        )

    # 2. Get the tenant ID from X-MS-CLIENT-PRINCIPAL
    encoded_principal = headers.get("X-MS-CLIENT-PRINCIPAL", "")
    if not encoded_principal:
        raise ValueError("X-MS-CLIENT-PRINCIPAL header is missing.")

    try:
        principal = json.loads(base64.b64decode(encoded_principal))
        tenant_id = None
        for claim in principal.get("claims", []):
            typ = claim.get("typ", "")
            if typ in ("tid", "http://schemas.microsoft.com/identity/claims/tenantid"):
                tenant_id = claim.get("val")
                break
        if not tenant_id:
            raise ValueError("Tenant ID claim not found in X-MS-CLIENT-PRINCIPAL.")
    except (json.JSONDecodeError, Exception) as ex:
        raise ValueError(f"Failed to decode X-MS-CLIENT-PRINCIPAL: {ex}") from ex

    # 3. Build a client assertion callback using the managed identity's
    #    federated credential (proves the app's identity without a client secret)
    federated_mi_client_id = os.environ.get("OVERRIDE_USE_MI_FIC_ASSERTION_CLIENTID")
    if not federated_mi_client_id:
        raise ValueError("OVERRIDE_USE_MI_FIC_ASSERTION_CLIENTID is not set.")

    client_id = os.environ.get("WEBSITE_AUTH_CLIENT_ID")
    if not client_id:
        raise ValueError("WEBSITE_AUTH_CLIENT_ID is not set.")

    token_exchange_audience = os.environ.get("TokenExchangeAudience", "api://AzureADTokenExchange")
    managed_identity = ManagedIdentityCredential(client_id=federated_mi_client_id)

    def client_assertion_func():
        assertion_token = managed_identity.get_token(f"{token_exchange_audience}/.default")
        return assertion_token.token

    return OnBehalfOfCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_assertion_func=client_assertion_func,
        user_assertion=user_token,
    )
