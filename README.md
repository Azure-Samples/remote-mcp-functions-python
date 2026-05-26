<!--
---
name: Remote MCP with Azure Functions (Python)
description: Run a remote MCP server on Azure functions.  
page_type: sample
languages:
- python
- bicep
- azdeveloper
products:
- azure-functions
- azure
urlFragment: remote-mcp-functions-python
---
-->

# Getting Started with Remote MCP Servers using Azure Functions (Python)

This repo has a collection of samples to help you easily build and deploy a custom remote MCP server to the cloud using Azure Functions. You can clone/restore/run on your local machine with debugging, and `azd up` to have a server in the cloud in a couple minutes.

All sample MCP servers are configured with [built-in authentication](https://learn.microsoft.com/en-us/azure/app-service/overview-authentication-authorization) using Microsoft Entra as the identity provider.

You can also use [API Management](https://learn.microsoft.com/azure/api-management/secure-mcp-servers) to secure the server, as well as network isolation using VNET.

If you're looking for samples in more languages check out the [.NET/C#](https://github.com/Azure-Samples/remote-mcp-functions-dotnet) and [Node.js/TypeScript](https://github.com/Azure-Samples/remote-mcp-functions-typescript) versions.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/remote-mcp-functions-python)

## Prerequisites

+ [Python](https://www.python.org/downloads/) version 3.13 or higher
+ [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local?pivots=programming-language-python#install-the-azure-functions-core-tools) >= `4.8.0`
+ [Azure Developer CLI](https://aka.ms/azd) **1.23.x or above** (for deployment)
+ [Docker](https://www.docker.com/) (for the Azurite storage emulator)
+ [Visual Studio Code](https://code.visualstudio.com/) (recommended)
+ [Azure Functions extension](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions)

Below is the architecture diagram for the Remote MCP Server using Azure Functions:

![Architecture Diagram](/media/architecture-diagram-http.png)

## Samples in this repo

Each project README has instructions for running locally, connecting to the MCP server, deploying to the cloud, and more.

| Project | Description | Getting Started |
|---------|-------------|-----------------|
| **FunctionsMcpTool** | MCP Tools — snippet CRUD, QR code generation, structured metadata, batch operations | [README](src/FunctionsMcpTool/README.md) |
| **FunctionsMcpResources** | MCP Resources — snippet resource template, server info resource | [README](src/FunctionsMcpResources/README.md) |
| **FunctionsMcpPrompts** | MCP Prompts — code review checklist, summarize content, generate docs | [README](src/FunctionsMcpPrompts/README.md) |
| **McpWeatherApp** | Weather App — MCP App demo with interactive UI | [README](src/McpWeatherApp/README.md) |

## Next Steps

+ Learn more about the [Azure Functions MCP extension](https://learn.microsoft.com/azure/azure-functions/functions-bindings-mcp?pivots=programming-language-typescript)
+ Learn more about [built-in MCP auth](https://learn.microsoft.com/azure/azure-functions/functions-mcp-tutorial?tabs=mcp-extension&pivots=programming-language-python#remote-mcp-server-authorization)
+ Follow our blog posts on [Azure SDK Blog](https://devblogs.microsoft.com/azure-sdk) and [Tech Community](https://techcommunity.microsoft.com/category/azure/blog/appsonazureblog) for updates.

