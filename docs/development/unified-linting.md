# Unified Linting Configuration

## Overview

All linting and code quality tools across the RAG Modulo project use **backend/pyproject.toml** as the single source of truth for configuration and version specifications.

This ensures consistency across:
- Local development (Makefile)
- Pre-commit hooks (.pre-commit-config.yaml)
- CI/CD pipelines (.github/workflows/01-lint.yml)

## Tool Versions

All tool versions are defined in `backend/pyproject.toml` under `[tool.poetry.group.dev.dependencies]`:

| Tool | Version | Purpose |
|------|---------|---------|
| **Ruff** | ^0.14.0 | Fast linting + formatting (replaces Black, isort, Flake8) |
| **MyPy** | ^1.15.0 | Static type checking |
| **Pylint** | ^3.3.8 | Code quality analysis |
| **Pydocstyle** | ^6.3.0 | Docstring style checking |

## Configuration Files

### Primary Configuration: `backend/pyproject.toml`

This file contains ALL tool configurations:

```toml
[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "YTT", "ASYNC", "S", "B", "A", "COM", "C4", "DTZ", "T10", "EM", "EXE", "FA", "ISC", "ICN", "G", "INP", "PIE", "T20", "PYI", "PT", "Q", "RSE", "RET", "SLF", "SLOT", "SIM", "TID", "TCH", "INT", "ARG", "PTH", "TD", "FIX", "ERA", "PD", "PGH", "PL", "TRY", "FLY", "NPY", "AIR", "PERF", "FURB", "LOG", "RUF"]

[tool.ruff.lint.isort]
known-first-party = ["main", "rag_solution", "core", "auth", "vectordbs"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true

[tool.pylint.main]
py-version = "3.12"

[tool.pydocstyle]
convention = "google"
```

### Secondary Files (Reference pyproject.toml)

#### `.pre-commit-config.yaml`
```yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.14.0  # Matches pyproject.toml version
  hooks:
    - id: ruff
      args: ['--fix', '--config', 'backend/pyproject.toml']
    - id: ruff-format
      args: ['--config', 'backend/pyproject.toml']
```

#### `Makefile`
```makefile
lint-ruff: venv
	@cd backend && $(POETRY) run ruff check . --config pyproject.toml
	@cd backend && $(POETRY) run ruff format --check . --config pyproject.toml
```

#### `.github/workflows/01-lint.yml`
```yaml
- name: Ruff (Lint + Format)
  run: |
    poetry install --only dev
    poetry run ruff check . --config pyproject.toml
    poetry run ruff format --check . --config pyproject.toml
```

## Usage

### Local Development

```bash
# Check all linting (Ruff + MyPy + Pylint)
make lint

# Quick check (Ruff only)
make lint-ruff

# Fix formatting issues
make format

# Run pre-commit hooks
make pre-commit-run
```

### Pre-Commit Hooks

Pre-commit hooks run automatically on `git commit`:

```bash
# Install hooks (one-time setup)
make setup-pre-commit

# Run manually on all files
pre-commit run --all-files

# Update hook versions
make pre-commit-update
```

### CI/CD

CI/CD runs automatically on pull requests and pushes to main:

- **Blocking checks**: Ruff (lint + format), YAML, JSON, TOML
- **Informational checks**: MyPy, Pylint, Pydocstyle

## Consistency Verification

To verify all configurations are aligned:

```bash
# Run the same checks locally as CI/CD
make ci-local

# Verify tool versions match
python scripts/verify_tool_versions.py
```

## Adding New Rules

When adding new linting rules:

1. **Update `backend/pyproject.toml`** with the new rule configuration
2. **Test locally**: `make lint`
3. **Verify pre-commit**: `pre-commit run --all-files`
4. **Check CI/CD**: The updated pyproject.toml will be used automatically

## Troubleshooting

### Pre-commit and Local Results Differ

**Cause**: Pre-commit hooks may use cached versions

**Solution**:
```bash
# Update pre-commit hooks to latest versions
make pre-commit-update

# Clean pre-commit cache
pre-commit clean
pre-commit install --install-hooks
```

### CI/CD and Local Results Differ

**Cause**: Different Poetry or Python versions

**Solution**:
```bash
# Use exact Python version
pyenv install 3.12
pyenv local 3.12

# Update Poetry to latest
poetry self update

# Re-install dependencies
poetry install --sync
```

### Import Sorting Issues

**Cause**: Ruff's `known-first-party` configuration

**Current setting**: `["main", "rag_solution", "core", "auth", "vectordbs"]`

**Fix imports**:
```bash
make format-imports
```

## Benefits of Unified Configuration

1. **Consistency**: Same results locally, in pre-commit, and in CI/CD
2. **Maintainability**: One file to update tool configurations
3. **Transparency**: Clear which version and config is being used
4. **Speed**: Ruff handles most checks in milliseconds
5. **Developer Experience**: No surprises between environments

## Migration History

- **October 2025**: Unified all linting configurations to use pyproject.toml
- **September 2025**: Migrated from Black + isort to Ruff
- **August 2025**: Added comprehensive Ruff rule set

## References

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Configuration](https://mypy.readthedocs.io/en/stable/config_file.html)
- [Pylint Documentation](https://pylint.pycqa.org/en/latest/)
- [Pre-commit Documentation](https://pre-commit.com/)
