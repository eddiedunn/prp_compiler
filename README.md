# PRP Compiler: An Agentic System for Crafting PRPs

This project is an agentic system designed to automate the creation of high-fidelity Product Requirement Prompts (PRPs). It uses a multi-agent architecture powered by Google's Gemini API to analyze a user's goal, gather relevant context, and synthesize a complete and well-structured PRP based on a predefined schema.

## Architecture

The PRP Compiler operates through a sophisticated agentic workflow:

1.  **Primitive Curation**: The system organizes all agentic capabilities as versioned primitives in the `agent_primitives/` directory. Each primitive is an Action, Knowledge, Pattern, or Schema, and is described by a `manifest.yml`.
2.  **Planning Agent (ReAct Loop)**: The `PlannerAgent` uses a ReAct (Reason + Act) loop to iteratively select actions, retrieve knowledge, and assemble context for the user goal, using function-calling and introspective reasoning.
3.  **Orchestration**: The `Orchestrator` executes the ReAct loop, driving the planner and executing actions until the agent determines the context is complete.
4.  **Synthesizer Agent**: The `SynthesizerAgent` receives the final assembled context and schema and produces a validated PRP JSON, strictly conforming to the chosen schema.

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

Once installed and configured, you can run the compiler from your terminal. The main commands are:

### Compile a PRP

```bash
prp-compiler compile "Create a command-line tool for managing a to-do list" --out my_todo_app_prp.json
```

This runs the full agentic workflow and writes the final PRP JSON to the specified file.

### Build or Rebuild the Knowledge Vector Store

```bash
prp-compiler build-knowledge --primitives-path agent_primitives --vector-db-path chroma_db
```

This command (re)builds the vector database used for retrieval-augmented generation (RAG) from all curated knowledge primitives.
### Run as a Service

```bash
prp-compiler serve --workers 4
```

This starts a simple async queue processor that can handle multiple PRP compilation jobs concurrently.

## Contributing

We welcome new primitives and improvements! See [CONTRIBUTING.md](CONTRIBUTING.md) for details on the curation workflow and development process.

For an in-depth look at the system architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

