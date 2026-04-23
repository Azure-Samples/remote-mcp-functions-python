# FunctionsMcpPrompts — MCP Prompts on Azure Functions (Python)

This project is a Python Azure Function app that exposes MCP (Model Context Protocol) prompts as a remote MCP server. Prompts are reusable prompt templates that MCP clients can discover and invoke, optionally with arguments.

> **Note:** MCP tools are in the [FunctionsMcpTool](../FunctionsMcpTool/) project.

## Prompts included

| Prompt | Arguments | Description |
|--------|-----------|-------------|
| `code_review_checklist` | _(none)_ | Returns a structured code review checklist for evaluating code changes. |
| `summarize_content` | `topic` (required), `audience` (optional) | Generates a summarization prompt tailored to a given topic and audience. |
| `generate_documentation` | `function_name` (optional), `style` (optional) | Generates API documentation for a function. |

## Key concepts

- **Simple prompts** (like `code_review_checklist`) take no arguments and return static prompt text.
- **Parameterized prompts** use `prompt_arguments` to accept arguments from the client.
- Prompts can define arguments as required or optional, and read them from `context.arguments`.

## Prerequisites

- [Python](https://www.python.org/downloads/) version 3.13 or higher
- [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local?pivots=programming-language-python#install-the-azure-functions-core-tools) >= `4.8.0`
- `azure-functions` version 2.2.0b2 or greater
- .NET SDK (for building the MCP extension)

## Run locally

### 1. Build the MCP extension

From this directory (`src/FunctionsMcpPrompts`), build the MCP extension:

```shell
dotnet restore extensions.csproj
dotnet build extensions.csproj
```

### 2. Install Dependencies

Create and activate a virtual environment, then install dependencies:

```shell
python3 -m venv .venv

# macOS/Linux
source .venv/bin/activate    

# Windows
.venv\Scripts\activate  

pip install -r requirements.txt
```

### 3. Start the Functions host

```shell
func start
```

The MCP endpoint will be available at `http://localhost:7071/runtime/webhooks/mcp`.

## Deploy to Azure

```shell
azd env set DEPLOY_SERVICE prompts
azd provision
azd deploy --service prompts
```

## Examining the code

Prompts are defined in `function_app.py`. Each prompt is a Python function with the `@app.mcp_prompt_trigger` decorator:

```python
@app.mcp_prompt_trigger(
    arg_name="context",
    prompt_name="summarize_content",
    prompt_arguments=[
        func.PromptArgument("topic", "The topic or content to summarize.", required=True),
        func.PromptArgument("audience", "Target audience (e.g., 'executive', 'developer', 'beginner').", required=False)
    ],
    description="Generates a summarization prompt tailored to a given topic and audience."
)
def summarize_content(context: func.PromptInvocationContext) -> str:
    topic = context.arguments.get("topic", "")
    audience = context.arguments.get("audience")
    # Returns a formatted prompt string
```

The `prompt_arguments` parameter defines the arguments that MCP clients see when they list available prompts.
