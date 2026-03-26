# Python Style

Python files in this project MUST follow:

- Line length: 120 characters
- Quotes: double quotes (enforced by Ruff)
- Import order: first-party (rag_solution, core, auth, vectordbs) -> third-party -> stdlib
- Type hints on all function parameters and return types
- Formatting: `poetry run ruff format` with `pyproject.toml` config
- Linting: `poetry run ruff check` with `pyproject.toml` config
