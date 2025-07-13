# Strategy: Simple Feature Implementation

This is a strategy for creating a standard feature PRP. Follow these steps in your ReAct loop.

1.  **Understand the Goal:** Use the `summarize_text` action on the user's goal to confirm your understanding and extract key technical terms.
2.  **Analyze Existing Code:** Use the `list_directory` and `read_file` actions to find similar patterns in the codebase. This is your highest priority.
3.  **Consult Knowledge Base:** Use the `retrieve_knowledge` action to search for best practices related to the technologies identified in the previous steps.
4.  **Finalize the Plan:** When you have sufficient context from the codebase and knowledge base, call the `finish` action. Select `prp_base_schema` as your schema choice and include any relevant patterns you found.
