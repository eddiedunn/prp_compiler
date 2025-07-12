import subprocess
import sys


def _run_command(command: list[str]):
    """Helper to run a command and exit if it fails."""
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(command)}", file=sys.stderr)
        print(result.stdout, file=sys.stdout)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    print(result.stdout)


def lint():
    """Runs ruff format and ruff check."""
    print("Running ruff format...")
    _run_command(["ruff", "format", "."])
    print("\nRunning ruff check...")
    _run_command(["ruff", "check", "."])
    print("\nLinting complete.")


def validate():
    """Runs linting and mypy type checking."""
    lint()
    print("\nRunning mypy...")
    _run_command(["mypy"])
    print("\nValidation complete.")
