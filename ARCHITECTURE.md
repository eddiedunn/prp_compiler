# Architecture of the `prp_compiler`

This document provides a deep dive into the technical architecture of the `prp_compiler`. It is intended for contributors and those who wish to understand the system's internal workings.

## High-Level Workflow: ReAct and RAG

The `prp_compiler` operates on a two-stage agentic model: a **Planner Agent** that uses a ReAct (Reason, Act) loop to gather context, followed by a **Synthesizer Agent** that assembles the final output. Knowledge retrieval is handled on-demand via a Retrieval-Augmented Generation (RAG) pipeline.

### Workflow Diagram

```mermaid
graph TD
    subgraph "Setup (One-time or on-change)"
        A[agent_primitives/] --> B(PrimitiveLoader);
        B --> C[In-Memory Manifests];
        D[agent_primitives/knowledge] --> E(KnowledgeStore Builder);
        E -- Embeds & Chunks --> F[(Vector DB)];
    end

    subgraph "Execution Flow"
        G[User Goal] --> H{Planner Agent (ReAct Loop)};
        C -- Provides available actions/patterns --> H;
        
        H <--> I{Execute Action};
        I -- Calls research tool --> X[e.g., Web Search];
        
        H <--> J{Retrieve Knowledge};
        J -- Sends query --> F;
        F -- Returns chunks --> J;
        
        H -- "Context Complete" --> K[Final Assembled Context];
        K --> L{Synthesizer Agent};
        C -- Provides Schema --> L;
        L -- Validates against schema --> M[Final PRP (JSON)];
    end
    
    subgraph "Evaluation (CI/CD)"
        N[tests/golden/] --> O{Pytest Harness};
        M -- Is compared against --> O;
        O --> P((Pass/Fail));
    end

    style I fill:#cde,stroke:#333
    style J fill:#cde,stroke:#333
    style H fill:#f9f,stroke:#333,stroke-width:2px
    style L fill:#f9f,stroke:#333,stroke-width:2px
```

## Core Components

### 1. The Primitive Library (`agent_primitives/`)
This is the agent's knowledge base, dynamically loaded at runtime.
-   **`actions/`**: Executable research tools.
-   **`knowledge/`**: Curated documents for RAG.
-   **`patterns/`**: Best-practice examples to be read for context.
-   **`schemas/`**: Structural blueprints for the final output.

### 2. The `PrimitiveLoader`
Located in `src/prp_compiler/primitives.py`, this class is responsible for scanning the `agent_primitives` directory, parsing the `manifest.json` file for each primitive, and creating an in-memory library of available capabilities. It respects semver for version resolution.

### 3. The `KnowledgeStore`
Located in `src/prp_compiler/knowledge.py`, this class manages the RAG pipeline. Its `build()` method chunks and embeds all documents in `knowledge/`, storing them in a local ChromaDB vector store. Its `retrieve()` method allows the Planner to perform semantic searches for context.

### 4. The Planner Agent (ReAct Loop)
This is the core reasoning engine. It iteratively:
1.  **Thinks:** Decides on the next best step (e.g., "I need to know more about Java testing patterns").
2.  **Acts:** Selects a tool (e.g., `retrieve_knowledge` with the query "Java testing patterns") and executes it. This is enforced via Gemini's function-calling feature.
3.  **Observes:** Adds the result of the action to its working context.
This loop continues until the agent concludes it has sufficient context to generate a high-quality PRP.

### 5. The Synthesizer Agent
A simpler agent that receives the final, rich context from the Planner and a chosen output schema. Its sole job is to arrange the context into the structure defined by the schema, producing a final, validated JSON output.

The orchestrator caches results of expensive steps and resolves dynamic content references before synthesis.
