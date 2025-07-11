#!/bin/zsh

# This script creates the directory and file structure for the prp_compiler project.
# It should be run from within the root of the project directory (e.g., inside 'prp_compiler/').

# --- Create Directories ---
# Using -p ensures that parent directories are created as needed and
# that the command doesn't fail if a directory already exists.
# Brace expansion {a,b,c} is used for a more compact command.
echo "Creating directories..."
mkdir -p \
  agent_capabilities/{knowledge,schemas,tools} \
  src/prp_compiler/agents \
  tests/agents

# --- Create Files ---
# The 'touch' command creates empty files. If a file already exists,
# it updates its modification timestamp without changing its content.
echo "Creating empty files..."
touch \
  .env \
  .gitignore \
  pyproject.toml \
  README.md \
  src/prp_compiler/__init__.py \
  src/prp_compiler/main.py \
  src/prp_compiler/config.py \
  src/prp_compiler/manifests.py \
  src/prp_compiler/orchestrator.py \
  src/prp_compiler/models.py \
  src/prp_compiler/agents/__init__.py \
  src/prp_compiler/agents/base_agent.py \
  src/prp_compiler/agents/planner.py \
  src/prp_compiler/agents/synthesizer.py \
  tests/__init__.py \
  tests/conftest.py \
  tests/test_manifests.py \
  tests/test_orchestrator.py \
  tests/agents/__init__.py \
  tests/agents/test_planner.py \
  tests/agents/test_synthesizer.py

echo "\nProject structure created successfully!"

# Optional: Display the created structure using 'tree' if installed
if command -v tree &> /dev/null
then
    echo "\nGenerated project tree:"
    tree -a
else
    echo "\n(Install 'tree' to visualize the directory structure)"
fi