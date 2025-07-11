from .base_agent import BaseAgent

SYNTHESIZER_PROMPT_TEMPLATE = """
You are an expert prompt engineer. Your task is to generate a complete and detailed Product Requirement Prompt (PRP) in **Markdown format**.

**Instructions:**
1.  Use the `Schema Template` below as the structural blueprint for the final document.
2.  Read the `Assembled Context` which contains information from various sources.
3.  Carefully fill in each section of the schema using the information provided in the context.
4.  Replace all placeholder text (e.g., "[Placeholder for...]") with specific, relevant details derived from the context and the user's goal.
5.  The final output must be a single, coherent Markdown document, ready for a development team. Do not output JSON or any other format.

**Schema Template:**
---
{schema_template}
---

**Assembled Context:**
---
{context}
---

Now, generate the final PRP as a complete Markdown document.
"""


class SynthesizerAgent(BaseAgent):
    """Agent responsible for synthesizing the final PRP."""

    def synthesize(self, schema_template: str, context: str) -> str:
        """
        Generates the final PRP by calling the LLM with the schema and context.
        """
        prompt = SYNTHESIZER_PROMPT_TEMPLATE.format(
            schema_template=schema_template, context=context
        )

        response = self.model.generate_content(prompt)
        return response.text
