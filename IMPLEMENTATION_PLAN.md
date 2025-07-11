Of course. This is the perfect approach for a complex, multi-stage project. By breaking it down into self-contained, validated phases, we enable agents of varying capabilities to contribute effectively and ensure a robust final product.

Here is the master implementation plan for the `prp_compiler`, broken down into distinct, stand-alone phases with all necessary context included in each block.

---

### **Master Implementation Plan: The `prp_compiler`**

**OVERALL GOAL:** Create a Python CLI tool named `prp_compiler` that intelligently generates comprehensive PRP documents by orchestrating calls to the Google Gemini API and leveraging a local knowledge base.

---

### **Phase 1: Project Foundation and Directory Structure**

*   **Difficulty:** Easy
*   **Goal:** Establish the basic project skeleton, define dependencies, and create the necessary directory structure. This phase ensures the project is correctly set up for all subsequent development.

#### **Context for Phase 1**

*   **Documentation & References:**
    *   **uv Project Management:** [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv) (For understanding `uv install` and `pyproject.toml`).
    *   **TOML Syntax:** [https://toml.io/en/](https://toml.io/en/) (For understanding the `pyproject.toml` format).
*   **Desired Codebase Architecture:**
    ```
    prp_compiler/
    ├── .env
    ├── .gitignore
    ├── pyproject.toml
    ├── README.md
    ├── agent_capabilities/
    │   ├── knowledge/
    │   ├── schemas/
    │   └── tools/
    └── src/
        └── prp_compiler/
            ├── __init__.py
            ├── main.py
            ├── config.py
            ├── manifests.py
            ├── orchestrator.py
            ├── models.py
            └── agents/
                ├── __init__.py
                ├── base_agent.py
                ├── planner.py
                └── synthesizer.py
    /tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_manifests.py
    ├── test_orchestrator.py
    └── agents/
        ├── __init__.py
        ├── test_planner.py
        └── test_synthesizer.py
    ```

#### **Implementation Steps for Phase 1**

1.  **CREATE** the file `pyproject.toml` in the root with the following content. This file defines the project, its dependencies, and the CLI script entry point.
    ```toml
    [project]
    name = "prp-compiler"
    version = "0.1.0"
    description = "An agentic system for compiling high-fidelity PRPs."
    requires-python = ">=3.9"
    dependencies = [
        "google-generativeai",
        "python-dotenv",
        "PyYAML",
        "pydantic",
        "tiktoken",
    ]

    [project.scripts]
    prp-compiler = "prp_compiler.main:run"

    [tool.pytest.ini_options]
    pythonpath = ["src"]
    ```
2.  **CREATE** the file `.gitignore` in the root to prevent committing secrets and temporary files.
    ```gitignore
    __pycache__/
    *.pyc
    .env
    /manifests/
    /tests/temp_*/
    build/
    dist/
    *.egg-info
    ```
3.  **CREATE** the entire directory structure as specified in the "Desired Codebase Architecture" above. Use `mkdir -p` to create all directories and `touch` to create empty `__init__.py` files and other Python files to act as placeholders.
4.  **CREATE** an empty `README.md` file.
5.  **CREATE** an empty `.env` file.

#### **Validation for Phase 1**
*   Run the command `uv venv && uv install .` from the project's root directory. It must complete without any errors, indicating that `pyproject.toml` is valid and the basic structure is sound.

---

### **Phase 2: Data Models and Configuration**

*   **Difficulty:** Easy to Medium
*   **Goal:** Define the core data structures using Pydantic for robust validation and create a centralized configuration handler for the Gemini API key.

#### **Context for Phase 2**

*   **Documentation & References:**
    *   **Pydantic V2 Models:** [https://docs.pydantic.dev/latest/](https://docs.pydantic.dev/latest/)
    *   **Python `dotenv`:** [https://pypi.org/project/python-dotenv/](https://pypi.org/project/python-dotenv/)
*   **Code Context:**
    *   You will be creating *new* files; no existing code needs to be modified.

#### **Implementation Steps for Phase 2**

1.  **CREATE** the Pydantic models in `src/prp_compiler/models.py`. This file will define the "shape" of the data that flows through the application, ensuring type safety.
    ```python
    # In src/prp_compiler/models.py
    from pydantic import BaseModel, Field
    from typing import List, Dict, Any

    class ManifestItem(BaseModel):
        name: str
        description: str
        arguments: str | None = None
        keywords: List[str] = Field(default_factory=list)
        file_path: str

    class ToolPlanItem(BaseModel):
        command_name: str
        arguments: str

    class ExecutionPlan(BaseModel):
        tool_plan: List[ToolPlanItem]
        knowledge_plan: List[str]
        schema_choice: str
    ```
2.  **CREATE** the configuration handler in `src/prp_compiler/config.py`. This module is responsible for securely loading the API key.
    ```python
    # In src/prp_compiler/config.py
    import os
    from dotenv import load_dotenv
    import google.generativeai as genai

    def configure_gemini():
        """Loads API key from .env and configures the Gemini client."""
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file or environment variables.")
        genai.configure(api_key=api_key)
        print("Gemini API configured successfully.")
    ```3.  **UPDATE** the `.env` file in the project root with a placeholder key.
    ```
    GEMINI_API_KEY="YOUR_API_KEY_HERE"
    ```

#### **Validation for Phase 2**
*   Create a temporary test script `tests/temp_phase2_validation.py`:
    ```python
    from prp_compiler.models import ExecutionPlan
    from prp_compiler.config import configure_gemini

    def test_models():
        # This will fail if the model is invalid
        ExecutionPlan.parse_obj({
            "tool_plan": [{"command_name": "test", "arguments": "args"}],
            "knowledge_plan": ["doc1"],
            "schema_choice": "schema1"
        })
        print("Pydantic models are valid.")

    def test_config():
        try:
            configure_gemini()
        except ValueError as e:
            # This is expected if the key isn't set yet
            print(f"Config function works as expected: {e}")

    test_models()
    test_config()
    ```
*   Run `uv run python tests/temp_phase2_validation.py`. It should print success messages.

---

### **Phase 3: Core Logic - Manifests and Orchestration**

*   **Difficulty:** Medium
*   **Goal:** Implement the non-AI core logic: the manifest generator that inventories the agent's capabilities and the orchestrator that assembles context and resolves dynamic content.

#### **Context for Phase 3**

*   **Documentation & References:**
    *   **PyYAML:** [https://pyyaml.org/wiki/PyYAMLDocumentation](https://pyyaml.org/wiki/PyYAMLDocumentation)
    *   **Python `subprocess`:** [https://docs.python.org/3/library/subprocess.html](https://docs.python.org/3/library/subprocess.html)
    *   **Python `re` (for regex):** [https://docs.python.org/3/library/re.html](https://docs.python.org/3/library/re.html)
*   **Pydantic Model for Manifests (from Phase 2):**
    ```python
    class ManifestItem(BaseModel):
        name: str
        description: str
        arguments: str | None = None
        keywords: List[str] = Field(default_factory=list)
        file_path: str
    ```
*   **Example File with Frontmatter (for testing):**
    ```markdown
    ---
    name: example-tool
    description: This is a test tool.
    arguments: The file to process.
    ---
    # Example Tool
    This is the body of the tool file.
    ```

#### **Implementation Steps for Phase 3**

1.  **IMPLEMENT** the manifest generator in `src/prp_compiler/manifests.py`.
    ```python
    # In src/prp_compiler/manifests.py
    import json
    import yaml
    from pathlib import Path
    from typing import List, Dict, Any
    from .models import ManifestItem

    def _parse_frontmatter(file_path: Path) -> Dict[str, Any]:
        # Implementation: Read file, split by '---', parse YAML, handle errors.
        # ...
    
    def generate_manifest(capability_path: Path) -> List[ManifestItem]:
        # Implementation: Walk dir, call _parse_frontmatter, create list of ManifestItem, include file_path.
        # ...

    def save_manifest(manifest_data: List[ManifestItem], output_path: Path):
        # Implementation: Convert Pydantic objects to dicts and save as JSON.
        # ...
    ```
2.  **IMPLEMENT** the orchestrator in `src/prp_compiler/orchestrator.py`.
    ```python
    # In src/prp_compiler/orchestrator.py
    import re
    import subprocess
    from pathlib import Path
    from .models import ExecutionPlan, ManifestItem
    from typing import List, Dict

    class Orchestrator:
        # ...
        def _resolve_dynamic_content(self, raw_context: str) -> str:
            # Implementation: Use re.sub with a callback function to handle both '!' and '@'.
            # Inside the callback, use subprocess.run for '!' and Path.read_text for '@'.
            # ...
    ```
3.  **IMPLEMENT** the tokenizer utility in `src/prp_compiler/utils.py`.
    ```python
    # In src/prp_compiler/utils.py
    import tiktoken
    # ... (content from master PRP)
    ```
4.  **CREATE** the corresponding unit tests.

#### **Validation for Phase 3**
*   **CREATE** a file `tests/test_manifests.py`. Write a test that creates a temporary directory with dummy capability files (including one with bad YAML) and asserts that `generate_manifest` produces the correct list of `ManifestItem` objects.
*   **CREATE** a file `tests/test_orchestrator.py`. Write a test for `_resolve_dynamic_content`. Use `unittest.mock.patch` to mock `subprocess.run` and `pathlib.Path.read_text`. Assert that a string with `!echo "hello"` and `@some/file.txt` is correctly transformed into a string containing `hello` and the mocked file content.

---

### **Phase 4: Agentic Intelligence Implementation**

*   **Difficulty:** Hard
*   **Goal:** Implement the `Planner` and `Synthesizer` agents that interact with the Gemini API. This is the "brain" of the system.

#### **Context for Phase 4**

*   **Documentation & References:**
    *   **Google Gemini API (Python):** [https://ai.google.dev/docs/gemini_api_overview](https://ai.google.dev/docs/gemini_api_overview)
*   **Pydantic Model for Planner Output (from Phase 2):**
    ```python
    class ExecutionPlan(BaseModel):
        tool_plan: List[ToolPlanItem]
        knowledge_plan: List[str]
        schema_choice: str
    ```
*   **Planner Prompt Template:**
    ```prompt
    You are an expert AI engineering architect. Your task is to create an execution plan for building a comprehensive Product Requirement Prompt (PRP).

    User's Goal: "{user_goal}"
    Available Tools: {tools_manifest}
    Available Knowledge: {knowledge_manifest}
    Available Schemas: {schemas_manifest}

    Based on the user's goal, select the required tools, knowledge, and the single best schema. Your output must be a single, valid JSON object matching this structure: {"tool_plan": [...], "knowledge_plan": [...], "schema_choice": "..."}
    ```*   **Synthesizer Prompt Template:**
    ```prompt
    You are an expert prompt engineer. Your task is to synthesize the following context into a final PRP, strictly adhering to the provided Schema Template.

    **Schema Template:**
    ---
    {schema_template}
    ---

    **Assembled Context:**
    ---
    {context}
    ---

    Now, produce the final, complete PRP.
    ```

#### **Implementation Steps for Phase 4**

1.  **IMPLEMENT** the `BaseAgent` in `src/prp_compiler/agents/base_agent.py` exactly as specified in the master PRP, including the `_clean_json_response` method.
2.  **IMPLEMENT** the `PlannerAgent` in `src/prp_compiler/agents/planner.py`, inheriting from `BaseAgent`. The `plan()` method must construct the prompt above, make the API call, clean the response, and validate it using `ExecutionPlan.parse_raw()`.
3.  **IMPLEMENT** the `SynthesizerAgent` in `src/prp_compiler/agents/synthesizer.py`, inheriting from `BaseAgent`. The `synthesize()` method must construct its prompt and return the final Markdown.

#### **Validation for Phase 4**
*   **CREATE** `tests/agents/test_planner.py`. Use `unittest.mock.patch` to mock `genai.GenerativeModel.generate_content`.
    *   Test 1: Assert that the `plan()` method calls the mock API with a correctly formatted prompt.
    *   Test 2: Provide a mocked API response (a JSON string with markdown fences) and assert that `plan()` correctly cleans, parses, and returns a valid `ExecutionPlan` object.
*   **CREATE** `tests/agents/test_synthesizer.py`. Mock the API and test that the `synthesize()` method constructs the correct prompt containing both the schema and context.

---

### **Phase 5: CLI Entry Point and Final Integration**

*   **Difficulty:** Medium
*   **Goal:** Create the main command-line interface that ties all the previously built components together into a single, executable workflow.

#### **Context for Phase 5**

*   **Documentation & References:**
    *   **Python `argparse`:** [https://docs.python.org/3/library/argparse.html](https://docs.python.org/3/library/argparse.html)
*   **Workflow Diagram (Mermaid):**
    ```mermaid
    graph TD
        A[main.py] --> B[Generate Manifests]
        B --> C[Instantiate Planner]
        C --> D[planner.plan()]
        D --> E[Instantiate Orchestrator]
        E --> F[orchestrator.assemble_context()]
        F --> G[Check Tokens]
        G --> H[Instantiate Synthesizer]
        H --> I[synthesizer.synthesize()]
        I --> J[Save File]
    ```

#### **Implementation Steps for Phase 5**

1.  **IMPLEMENT** the `main.py` file.
    *   Use `argparse` to set up `--goal` and `--output` command-line arguments.
    *   Implement the main function that orchestrates the entire flow exactly as shown in the Mermaid diagram above.
    *   Wrap the main logic in a `try...except` block to catch any errors from the sub-modules and print a user-friendly error message.
    *   Add print statements to the console to show progress (e.g., "Generating manifests...", "Planning...", "Synthesizing...").
    *   The `run()` function at the top level should simply call this main function.

#### **Validation for Phase 5**
*   **CREATE** an integration test `tests/test_integration.py`. This test should *not* make real API calls.
    1.  Use a pytest fixture to create a temporary directory with a sample `agent_capabilities` structure.
    2.  Use `unittest.mock.patch` to mock `prp_compiler.agents.planner.PlannerAgent.plan`. Make it return a fixed, valid `ExecutionPlan` object.
    3.  Use `unittest.mock.patch` to mock `prp_compiler.agents.synthesizer.SynthesizerAgent.synthesize`. Make it return a fixed string like "## Final PRP".
    4.  Run the `main()` function from your test, pointing it to your temporary directories.
    5.  Assert that the output file is created and contains the text "## Final PRP". This proves all the components are wired together correctly.

---

### **Phase 6: Documentation and Final Polish**

*   **Difficulty:** Medium
*   **Goal:** Finalize the project by adding comprehensive user documentation, ensuring all tests pass, and verifying full test coverage.

#### **Context for Phase 6**

*   **Reference File:** `PRPs-agentic-eng-ref/README.md` (Use this as inspiration for structure and tone).
*   **Final Commands:** `uv run pytest --cov=src/prp_compiler`, `uv run ruff check .`, `uv run mypy .`

#### **Implementation Steps for Phase 6**

1.  **CREATE** a high-quality `README.md` file in the project root. It should include:
    *   A brief explanation of the project's purpose.
    *   **Installation:** `uv install .`
    *   **Configuration:** How to create the `.env` file and set `GEMINI_API_KEY`.
    *   **Usage:** A clear example of how to run the CLI: `prp-compiler --goal "..." --output "..."`.
    *   **Architecture:** A brief description of the agentic workflow.
2.  **CREATE** `tests/conftest.py` if you have any shared pytest fixtures (e.g., the temporary directory setup).
3.  **RUN** the full test suite with coverage: `uv run pytest --cov=src/prp_compiler`.
4.  **ANALYZE** the coverage report. If any critical logic is untested, add unit tests to cover it, aiming for >80%.
5.  **RUN** all final validation commands (`ruff`, `mypy`) and fix any remaining issues.

#### **Validation for Phase 6**
*   The command `uv run pytest --cov=src/prp_compiler` must pass with a coverage result of at least 80%.
*   The `README.md` must be clear and provide sufficient instructions for a new user to successfully run the tool.
*   The `prp-compiler` command must be runnable from any directory after installation with `uv install .`.