# Contributing to the PRP Compiler

We welcome contributions to the `prp_compiler`! This guide provides instructions on how to extend the system by adding new primitives. For a detailed overview of the system's design, please see [ARCHITECTURE.md](./ARCHITECTURE.md).

## Adding a New Primitive

All agent capabilities are defined as "primitives" within the `agent_primitives/` directory. Adding a new capability is as simple as creating a new folder and a manifest file.

### 1. Adding a New Action

Actions are executable tools for the Planner agent to use during its research phase.

1.  **Create a Directory:** Create a new directory under `agent_primitives/actions/<your_action_name>/<version>/`. Use semantic versioning (e.g., `1.0.0`).
2.  **Create `manifest.json`:** This file describes your action.
    ```json
    {
      "name": "your_action_name",
      "type": "action",
      "version": "1.0.0",
      "entrypoint": "your_action.py:run", // Path to the Python function
      "inputs_schema": {
        "type": "object",
        "properties": {
          "arg1": {"type": "string", "description": "Description of arg1."}
        },
        "required": ["arg1"]
      },
      "description": "A brief description of what this action does."
    }
    ```
3.  **Create the Python script** (`your_action.py`) specified in the `entrypoint`. It must contain a `run` function that accepts the arguments defined in your schema.

### 2. Adding a New Knowledge Document

Knowledge documents are long-form texts that are embedded and stored in the RAG vector database.

1.  **Create a Directory:** `agent_primitives/knowledge/<your_knowledge_topic>/<version>/`.
2.  **Create `manifest.json`:**
    ```json
    {
      "name": "your_knowledge_topic",
      "type": "knowledge",
      "version": "1.0.0",
      "entrypoint": "content.md", // The name of the markdown file
      "description": "A detailed guide on a specific topic.",
      "keywords": ["keyword1", "keyword2"]
    }
    ```
3.  **Add your `content.md` file** in the same directory.
4.  **Re-build the knowledge store:** After adding the file, run `prp-compiler build-knowledge` (Note: we need to add this command to `main.py`).

### 3. Adding a New Pattern or Schema

Patterns (reference examples) and Schemas (output templates) follow the same structure as Knowledge documents but are placed in the `patterns/` or `schemas/` directories respectively, and have a `type` of `pattern` or `schema` in their manifest.

## Running Tests Before Submitting

Before submitting a pull request, please ensure you have run the full test suite, including the golden set evaluation harness.

```bash
uv run pytest
```

If you add a new core feature, please consider adding a new test case to the `tests/golden/` directory to prevent future regressions.
