---

### **The Curation Protocol: A Guide to Building High-Quality Agentic Primitives**

#### **1. Core Philosophy: The Agent as a Craftsman**

Our `prp_compiler` is an AI craftsman. Like any master craftsman, its performance depends on two things: its skill (the agent's reasoning ability) and the quality of its workshop (the `agent_primitives`).

This guide details how we stock and maintain that workshop. **Curation is not a one-time task; it is the continuous process of providing the agent with the best possible tools, materials, and blueprints.** Our goal is to create a library of primitives so effective that the agent's "first draft" is of near-production quality.

#### **2. The Four Primitive Types: A Quick Reference**

Every file added to the `agent_primitives` directory **must** be categorized into one of these four types. This is the foundational taxonomy of our agent's "mind."

| Primitive Type | Directory | Purpose (Analogy)              | Key Characteristic                                                                  |
| :------------- | :-------- | :----------------------------- | :---------------------------------------------------------------------------------- |
| **Action**     | `actions/`  | The Agent's Tools (Verbs)      | **Executable.** Represents an active research capability (e.g., `web_search`).         |
| **Knowledge**  | `knowledge/`| The Agent's Encyclopedia       | **Referenceable.** Deep, factual, and tech-specific documents for RAG.             |
| **Pattern**    | `patterns/` | The Agent's Cookbook/Casebook  | **Illustrative.** Concise, standalone examples of "how we solve X."                 |
| **Schema**     | `schemas/`  | The Agent's Blueprints         | **Structural.** Defines the required format and sections of the final PRP output. |

---

#### **3. The Curation Workflow: From Idea to Primitive**

Follow this five-step process whenever adding a new primitive to the library.

##### **Step 1: Identify the Gap**

Start by asking "What is the agent missing?"
*   Is it failing to generate good PRPs for a specific technology (e.g., Rust)? -> **This suggests a `Knowledge` gap.**
*   Is it struggling to structure its plans for a common task (e.g., API design)? -> **This suggests a `Pattern` gap.**
*   Is it unable to find a specific piece of live information (e.g., the current project's file structure)? -> **This suggests an `Action` gap.**
*   Is its final output unstructured or missing key sections? -> **This suggests a `Schema` gap.**

##### **Step 2: Categorize the Primitive**

Based on the gap, determine which of the four primitive types is the correct solution. This is the most important decision in the curation process.

*   **Is it an executable process to gather *new* information?** -> It's an **Action**.
*   **Is it a deep, factual document about a *specific technology or concept*?** -> It's **Knowledge**.
*   **Is it a complete, high-quality example of *how to solve a recurring problem*?** -> It's a **Pattern**.
*   **Is it a template that defines the *structure* of an output?** -> It's a **Schema**.

##### **Step 3: Author or Adapt the Content**

Create the content for the primitive, following these principles:
*   **Actions:** Write the Python script or prompt template that performs the action. It must be robust and handle errors.
*   **Knowledge:** Author a comprehensive Markdown document. Use clear headers, as these are used for chunking. The content must be factual and well-researched.
*   **Patterns:** Create a standalone, exemplary solution to a problem. This is often a complete prompt template itself, showing best practices.
*   **Schemas:** Define a JSON schema or a Markdown template with clear placeholders.

##### **Step 4: Add Rich Metadata (`manifest.yml`)**

This step is non-negotiable. It is how the agent discovers and understands the primitive. **If a primitive doesn't have a manifest, it doesn't exist for the agent.**

Create a `manifest.yml` file in the primitive's versioned directory with the following fields:
*   `name`: A unique, `snake_case` identifier.
*   `type`: One of `action`, `knowledge`, `pattern`, or `schema`.
*   `version`: The semantic version (e.g., `1.0.0`).
*   `description`: A concise, one-sentence explanation of what the primitive is and when to use it. *This is the most important field for the Planner agent.*
*   `keywords`: (For `knowledge` and `patterns`) A list of lowercase keywords that the RAG system and Planner can use for semantic matching.
*   `entrypoint`: The main file for the primitive (e.g., `main.py`, `content.md`, `schema.json`).
*   `inputs_schema`: (For `actions` only) A JSON schema defining the arguments the action takes.

##### **Step 5: Validate and Test**

The system's quality depends on its evaluation harness.
1.  **For new `Knowledge`:** After adding the document, you must rebuild the vector store.
2.  **For all primitives:** Create a new test case in the `tests/golden/` directory.
    *   Create a `goal.md` that is specifically designed to require your new primitive.
    *   Create an `expected_prp.json` that shows the structure you expect the agent to produce *after* using your new primitive.
    *   Run `uv run pytest`. If the test fails, it means the Planner isn't selecting your primitive correctly, or the primitive itself is not providing the right context. Debug and refine until the test passes.

---

#### **4. A Concrete Example: Adding a Rust Linter Action**

**1. Identify the Gap:** The agent can write Rust code but cannot validate it against our team's standards using `clippy`.

**2. Categorize:** This is a process to gather new information (linting results) about generated code. It is an **Action**.

**3. Author:** We'll assume a Python script exists that can run `cargo clippy`.

**4. Add Metadata:**
*   Create directory: `agent_primitives/actions/run_rust_linter/1.0.0/`
*   Create `manifest.yml`:
    ```yaml
    name: "run_rust_linter"
    type: "action"
    version: "1.0.0"
    description: "Runs 'cargo clippy' on a specified Rust project directory to check for code quality and correctness."
    entrypoint: "run_clippy.py:run"
    inputs_schema:
      type: "object"
      properties:
        directory:
          type: "string"
          description: "The path to the Rust project to lint."
      required: ["directory"]
    ```
*   Create `run_clippy.py` with a `run(directory: str)` function.

**5. Validate:**
*   Create `tests/golden/02_rust_linting/`.
*   `goal.md`: "Generate a simple Rust 'hello world' program and then validate it using the linter."
*   `expected_prp.json`: The expected output, which should include a plan to call `run_rust_linter`.
*   Run `uv run pytest` and ensure the new test case passes.

---

#### **5. Principles of Excellent Curation**

*   **Atomicity:** One Primitive, One Job. A knowledge document should be about one specific topic. An action should do one thing well.
*   **Discoverability:** If it's not in the `description` and `keywords`, the agent will never find it. Write descriptions for an LLM, not a human.
*   **Generality vs. Specificity:** `Actions` and `Schemas` should be general. `Knowledge` documents should be highly specific. `Patterns` live in between—they solve a general problem with specific examples.
*   **Trust and Verifiability:** `Knowledge` is the highest-trust information source. `Actions` are the most dangerous; they must be secure and well-tested.
*   **The Gardener's Mindset:** Primitives are not "fire-and-forget." They must be reviewed, updated, versioned, and sometimes deprecated. A healthy primitive library is a living system.

---
**Action Item:** This guide should be saved as `DOCUMENTATION.md` in the root of the `prp_compiler` repository. It will serve as the canonical reference for all future development and contributions.