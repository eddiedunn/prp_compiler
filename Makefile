# Makefile for prp_compiler project

# List available Gemini models
list-models:
	uv run -m prp_compiler.main list-models

# Compile a PRP from a goal (provide GOAL and OUT)
compile:
	uv run -m prp_compiler.main compile "$(GOAL)" --out $(OUT)

# Run all tests
check:
	uv run pytest

# Run linter (ruff)
lint:
	uv run ruff .

# Run type checker (mypy)
typecheck:
	uv run mypy src/

# Clean build and test artifacts
clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache __pycache__ src/__pycache__ src/prp_compiler/__pycache__

.PHONY: list-models compile check lint typecheck clean
