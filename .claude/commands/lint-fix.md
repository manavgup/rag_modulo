# Lint Fix

Format and lint-fix all changed Python files.

1. Run `git diff --name-only` to find changed .py files
2. Run `poetry run ruff format <files> --config pyproject.toml`
3. Run `poetry run ruff check <files> --config pyproject.toml --fix`
4. Report what was changed
5. If there are remaining unfixable issues, list them clearly
