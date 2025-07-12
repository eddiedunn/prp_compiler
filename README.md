# PRP Compiler: An Agentic System for Crafting PRPs

This project is an agentic system designed to automate the creation of high-fidelity Product Requirement Prompts (PRPs). It uses a multi-agent architecture powered by Google's Gemini API to analyze a user's goal, gather relevant context, and synthesize a complete and well-structured PRP based on a predefined schema.

## Architecture

The PRP Compiler operates through a sophisticated agentic workflow:

1.  **Manifest Generation**: The system begins by scanning its capability directories (`tools/`, `knowledge/`, `schemas/`) to create manifests—JSON files that catalog all available resources.
2.  **Planning Agent**: The `PlannerAgent` receives the user's high-level goal. It consults the manifests to understand the available tools, knowledge, and schemas. It then formulates a step-by-step `ExecutionPlan`, selecting the optimal resources for the task.
3.  **Orchestration**: The `Orchestrator` takes the `ExecutionPlan` and resolves all dynamic content. It executes shell commands (for `!`) and reads file contents (for `@`) to assemble a complete context.
4.  **Synthesizer Agent**: The `SynthesizerAgent` receives the final assembled context and the chosen schema template. It uses this information to generate the final, polished Product Requirement Prompt (PRP) in Markdown format.

## Installation

This project is managed with `uv`, a fast Python package installer and resolver.

To install the project and its dependencies, run the following command from the project root:

```bash
uv pip install -e .
```


## Configuration

The compiler requires a Google Gemini API key to function.

1.  Create a file named `.env` in the project root.
2.  Add your API key to the file:
    ```
    GEMINI_API_KEY="your_api_key_here"
    ```

The application will automatically load this key to configure the Gemini client.

## Usage

Once installed and configured, you can run the compiler from your terminal. The main command accepts a user goal and an output file path.

**Example:**

```bash
prp-compiler --goal "Create a command-line tool for managing a to-do list" --output "my_todo_app_prp.md"
```

This command will trigger the full agentic workflow and write the final, synthesized PRP to `my_todo_app_prp.md`.