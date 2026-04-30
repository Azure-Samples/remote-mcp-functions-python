import azure.functions as func
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Simple prompt with no arguments. Returns a static code review checklist.
# Demonstrates the basic mcp_prompt_trigger usage.
@app.mcp_prompt_trigger(
    arg_name="context",
    prompt_name="code_review_checklist",
    description="Returns a structured code review checklist prompt for evaluating code changes."
)
def code_review_checklist(context: func.PromptInvocationContext) -> str:
    logging.info("Code review checklist prompt invoked.")
    
    return """You are a senior software engineer performing a code review.
Use the following checklist to evaluate the code:

1. **Correctness** — Does the code do what it's supposed to?
2. **Error Handling** — Are edge cases and failures handled?
3. **Security** — Are there any vulnerabilities (injection, auth, secrets)?
4. **Performance** — Are there obvious inefficiencies?
5. **Readability** — Is the code clear and well-named?
6. **Tests** — Are there adequate tests for the changes?

Provide your feedback in a structured format with a severity level
(critical, warning, suggestion) for each finding."""


# Prompt with arguments.
# Generates a context-aware summarization prompt for a given topic and audience.
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
    
    logging.info(f"Summarize prompt invoked for topic: {topic}")
    
    audience_instruction = (
        f"Tailor the summary for a **{audience}** audience."
        if audience is not None
        else "Write the summary for a general technical audience."
    )
    
    return f"""Summarize the following topic concisely and accurately:

**Topic:** {topic}

{audience_instruction}

Guidelines:
- Start with a one-sentence overview.
- Include 3–5 key points as bullet items.
- End with a brief conclusion or recommendation.
- Keep the total length under 300 words."""


# Prompt with arguments for generating API documentation.
@app.mcp_prompt_trigger(
    arg_name="context",
    prompt_name="generate_documentation",
    prompt_arguments=[
        func.PromptArgument("function_name", "The name of the function to document.", required=False),
        func.PromptArgument("style", "Documentation style: 'concise', 'detailed', or 'tutorial'.", required=False)
    ],
    description="Generates API documentation for a function. Arguments are configured in Program.cs."
)
def generate_documentation(context: func.PromptInvocationContext) -> str:
    function_name = context.arguments.get("function_name", "(unknown)")
    style = context.arguments.get("style", "concise")
    
    logging.info(f"Generate docs prompt invoked for function: {function_name}")
    
    return f"""Generate API documentation for the function named **{function_name}**.

Documentation style: **{style}**

Include the following sections:
- **Description** — What the function does.
- **Parameters** — List each parameter with its type and purpose.
- **Return Value** — What the function returns.
- **Example Usage** — A short code example showing how to call it."""