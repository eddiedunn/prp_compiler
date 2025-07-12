# Knowledge Base: Modern Python Best Practices

## 1. Project Structure

A standard Python project should be organized logically to separate source code, tests, and documentation.

```
my_project/
├── src/
│   └── my_project/
│       ├── __init__.py
│       ├── main.py
│       └── module.py
├── tests/
│   ├── __init__.py
│   └── test_module.py
├── .gitignore
├── pyproject.toml
└── README.md
```

- **`src/` layout:** Placing your main package inside a `src` directory prevents many common import path issues.
- **`pyproject.toml`:** The modern standard for project metadata and dependency management, replacing `setup.py` and `requirements.txt` for most use cases.
- **`tests/`:** A top-level directory for all tests, mirroring the structure of your source package.

## 2. Dependency Management with `uv`

`uv` is an extremely fast Python package installer and resolver, written in Rust, designed as a drop-in replacement for `pip` and `pip-tools`.

- **Installation:** `pip install uv`
- **Creating a Virtual Environment:** `uv venv`
- **Activating:** `source .venv/bin/activate`
- **Adding a Dependency:** `uv pip install <package>` (e.g., `uv pip install pydantic`)
- **Syncing with `pyproject.toml`:** `uv pip sync pyproject.toml` installs all dependencies defined in the project file.
- **Running scripts:** `uv run <script_name>` executes a script defined in `pyproject.toml`'s `[tool.uv.scripts]` section.

Example `pyproject.toml` dependencies:

```toml
[project]
name = "my_project"
version = "0.1.0"
dependencies = [
    "pydantic>=2.0",
    "fastapi>=0.100",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "ruff",
    "mypy",
]
```

## 3. Testing with `pytest`

`pytest` is the de-facto standard for testing in Python due to its simplicity and powerful features like fixtures.

- **Test Discovery:** `pytest` automatically finds and runs files named `test_*.py` or `*_test.py` containing functions prefixed with `test_`.
- **Fixtures:** Use fixtures (`@pytest.fixture`) to provide a fixed baseline state or data for your tests. They are reusable and modular.
- **Assertions:** Use plain `assert` statements. `pytest` rewrites them to provide detailed introspection on failures.

Example test in `tests/test_module.py`:

```python
import pytest
from my_project.module import add_numbers

@pytest.mark.parametrize("a, b, expected", [
    (1, 2, 3),
    (-1, 1, 0),
    (0, 0, 0),
])
def test_add_numbers(a, b, expected):
    assert add_numbers(a, b) == expected
```

- **Running Tests:** `uv run pytest`

## 4. Code Style and Linting with `ruff`

`ruff` is an extremely fast Python linter and code formatter, written in Rust. It can replace dozens of tools like Flake8, isort, and Black.

- **Configuration:** Configure `ruff` in your `pyproject.toml`.

```toml
[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "I"] # Enable Flake8 error/warning codes and isort
```

- **Checking for Errors:** `ruff check .`
- **Fixing Errors Automatically:** `ruff check . --fix`
- **Formatting Code:** `ruff format .`

## 5. Type Checking with `mypy`

Static type checking helps catch bugs before they happen. `mypy` is the standard tool for this.

- **Configuration:** Configure `mypy` in `pyproject.toml`.

```toml
[tool.mypy]
python_version = "3.11"
warnings_as_errors = true

[[tool.mypy.overrides]]
module = "third_party_lib.*"
ignore_missing_imports = true
```

- **Running:** `mypy src/`

## 6. Data Validation with `Pydantic`

`Pydantic` provides data validation and settings management using Python type annotations. It's invaluable for building robust APIs and data processing pipelines.

```python
from pydantic import BaseModel, EmailStr, ValidationError

class User(BaseModel):
    id: int
    name: str
    email: EmailStr

try:
    user = User(id=1, name='John Doe', email='john.doe@example.com')
    print(user.model_dump_json())
except ValidationError as e:
    print(e)
```

Pydantic ensures that data conforms to the expected schema at runtime, raising clear errors when it doesn't.
