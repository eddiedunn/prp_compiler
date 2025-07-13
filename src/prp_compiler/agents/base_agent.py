import re
from typing import Any

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - allow tests without package

    class DummyModel:
        def generate_content(self, *args, **kwargs):
            class Res:
                text = "{}"
                candidates = [
                    type(
                        "C",
                        (),
                        {
                            "content": type(
                                "P",
                                (),
                                {"parts": [type("FC", (), {"function_call": None})()]},
                            )()
                        },
                    )
                ]

            return Res()

    genai = type("genai", (), {"GenerativeModel": lambda *a, **kw: DummyModel()})


class BaseAgent:
    """Base class for all agents, handling API configuration and common utilities."""

    def __init__(self, model_name: str = "gemini-1.5-flash"):
        # Configuration is now handled in main.py
        self.model = genai.GenerativeModel(model_name)
        self.debug = True  # Enable debug logging by default

    def generate_content(self, prompt: str, **kwargs):
        """Wrapper around model.generate_content with debug logging."""
        self._log_debug(
            "Sending request to Gemini API",
            {
                "prompt": prompt[:500] + "..." if len(prompt) > 500 else prompt,
                "kwargs": {
                    k: str(v)[:200] + "..."
                    if hasattr(v, "__len__") and len(str(v)) > 200
                    else v
                    for k, v in kwargs.items()
                },
            },
        )

        try:
            response = self.model.generate_content(prompt, **kwargs)

            # Safely retrieve the response text as some Gemini SDK versions
            # raise an exception when ``response.text`` is accessed on
            # function-call results.
            response_text = None
            try:
                response_text = response.text
            except Exception as exc:  # pragma: no cover - depends on SDK behaviour
                response_text = f"[text unavailable: {exc}]"

            # Log the raw response
            self._log_debug(
                "Received response from Gemini API",
                {
                    "type": type(response).__name__,
                    "text": response_text,
                    "has_candidates": hasattr(response, "candidates")
                    and bool(response.candidates),
                    "candidates_count": len(response.candidates)
                    if hasattr(response, "candidates")
                    else 0,
                },
            )

            # Log details about the first candidate if available
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                self._log_debug(
                    "First candidate details",
                    {
                        "content_type": type(candidate.content).__name__
                        if hasattr(candidate, "content")
                        else "No content",
                        "has_parts": hasattr(candidate.content, "parts")
                        and bool(candidate.content.parts),
                        "parts_count": len(candidate.content.parts)
                        if hasattr(candidate.content, "parts")
                        else 0,
                    },
                )

                if hasattr(candidate.content, "parts") and candidate.content.parts:
                    part = candidate.content.parts[0]
                    self._log_debug(
                        "First part details",
                        {
                            "type": type(part).__name__,
                            "has_function_call": hasattr(part, "function_call"),
                            "function_call_type": type(part.function_call).__name__
                            if hasattr(part, "function_call")
                            else "No function_call",
                            "function_call_attrs": dir(part.function_call)
                            if hasattr(part, "function_call") and part.function_call
                            else "No function_call",
                        },
                    )

            return response

        except Exception as e:
            self._log_debug(
                f"Error in generate_content: {str(e)}",
                {
                    "error_type": type(e).__name__,
                    "error_args": getattr(e, "args", "No args"),
                },
            )
            raise

    def _log_debug(self, message: str, data: Any = None):
        """Helper method for debug logging."""
        if not self.debug:
            return

        print("\n=== DEBUG ===")
        print(message)
        if data is not None:
            if hasattr(data, "__dict__"):
                print(f"Type: {type(data).__name__}")
                print("Attributes:")
                for k, v in data.__dict__.items():
                    print(f"  {k}: {v}")
            else:
                print(f"Type: {type(data).__name__}")
                print(f"Value: {data}")
        print("==========\n")

    def _clean_json_response(self, text: str) -> str:
        """
        Cleans the raw text response from the LLM to extract a valid JSON object.
        It handles markdown fences, optional 'json' specifiers, and surrounding text.
        """
        # Match ```json, ```, or just the JSON object itself
        match = re.search(
            r"```(?:json)?\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*\})", text, re.DOTALL
        )
        if match:
            # Prioritize the content within fences if both groups are found
            return match.group(1) or match.group(2)

        # As a fallback, try to find the first and last curly braces
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            result = text[start:end]
            self._log_debug("Extracted JSON from text", result)
            return result
        except ValueError:
            self._log_debug("No JSON object found in text", text)
            return text  # Return original text if no JSON object is found
