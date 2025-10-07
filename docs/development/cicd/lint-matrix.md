# Lint Matrix Strategy

!!! success "Status"
    **Implementation**: ✅ Complete (Phase 1)
    **File**: `.github/workflows/01-lint.yml`
    **Last Updated**: October 6, 2025

## Overview

The Lint Matrix strategy replaces monolithic linting with parallel, independent linter jobs for better visibility and faster feedback.

---

## Benefits

### 1. **Parallel Execution** ⚡

All linters run simultaneously, reducing total time:

```
Before: Monolithic Lint (Sequential)
├─ yamllint      (30s)
├─ ruff check    (45s)
├─ mypy          (60s)
├─ pylint        (90s)
└─ eslint        (40s)
Total: ~4.5 minutes

After: Matrix Lint (Parallel)
├─ yamllint      (30s) ┐
├─ ruff check    (45s) │
├─ mypy          (60s) ├─ All run in parallel
├─ pylint        (90s) │
└─ eslint        (40s) ┘
Total: ~1.5 minutes (longest job)
```

**Result**: ~3x faster! 🚀

### 2. **Clear Visibility** 👀

Each linter is a separate job in GitHub UI:

```
✅ YAML Lint
✅ JSON Lint
❌ Ruff Check         ← Exactly which linter failed
✅ MyPy Type Check
✅ Pylint Quality
```

Before: Had to read logs to find which linter failed
After: Click directly on failing job

### 3. **Fail-Fast: False** 📊

See **all** linter failures, not just the first:

```yaml
strategy:
  fail-fast: false  # Don't stop on first failure
```

**Why this matters**:

- Fix 5 issues in one PR, not 5 separate PRs
- Better developer experience
- Faster iteration

### 4. **Easy Retry** 🔄

Failed linter? Re-run just that job:

```
GitHub UI: "Re-run job" → Only runs that specific linter
```

Before: Had to re-run entire monolithic lint
After: Re-run individual linter (30-90s vs 4.5min)

---

## Linter Matrix

### Configuration Files

#### 1. YAML Lint

**Tool**: `yamllint`
**Target**: `.github/` workflows
**Duration**: ~30s

```bash
pip install yamllint
yamllint .github/
```

**What it checks**:

- YAML syntax errors
- Indentation consistency
- Line length
- Trailing spaces

#### 2. JSON Lint

**Tool**: `jq`
**Target**: All `*.json` files
**Duration**: ~15s

```bash
find . -name '*.json' -not -path './node_modules/*' -exec jq empty {} \;
```

**What it checks**:

- JSON syntax errors
- Valid structure

#### 3. TOML Lint

**Tool**: Python `toml` module
**Target**: `backend/pyproject.toml`
**Duration**: ~10s

```bash
python -c "import toml; toml.load(open('backend/pyproject.toml'))"
```

**What it checks**:

- TOML syntax errors
- Valid structure

---

### Python Backend Linting

#### 4. Ruff Check

**Tool**: `ruff check`
**Target**: `backend/rag_solution/`
**Duration**: ~45s

```bash
poetry run ruff check rag_solution/ --line-length 120
```

**What it checks**:

- PEP 8 style violations
- Import sorting
- Unused imports/variables
- Complexity issues
- 100+ rules enabled

**Why Ruff**: 10-100x faster than Flake8/Pylint for style checks

#### 5. Ruff Format

**Tool**: `ruff format`
**Target**: `backend/rag_solution/`
**Duration**: ~30s

```bash
poetry run ruff format --check rag_solution/
```

**What it checks**:

- Code formatting (Black-compatible)
- Consistent style across codebase

**Why Ruff Format**: Faster alternative to Black

#### 6. MyPy Type Check

**Tool**: `mypy`
**Target**: `backend/rag_solution/`
**Duration**: ~60s

```bash
poetry run mypy rag_solution/ --ignore-missing-imports
```

**What it checks**:

- Type hint correctness
- Type consistency
- Type safety violations

**Why MyPy**: Catch type-related bugs before runtime

#### 7. Pylint Quality

**Tool**: `pylint`
**Target**: `backend/rag_solution/`
**Duration**: ~90s
**Mode**: Non-blocking (`--exit-zero`)

```bash
poetry run pylint rag_solution/ --exit-zero
```

**What it checks**:

- Code smells
- Complexity metrics
- Design issues
- Best practices

**Why Non-Blocking**: Currently informational, not enforced

#### 8. Pydocstyle

**Tool**: `pydocstyle`
**Target**: `backend/rag_solution/`
**Duration**: ~20s

```bash
poetry run pydocstyle rag_solution/ --count
```

**What it checks**:

- Docstring presence
- Docstring format (Google/NumPy style)
- Missing documentation

---

### Frontend Linting

#### 9. ESLint

**Tool**: `eslint`
**Target**: `frontend/src/`
**Duration**: ~40s

```bash
npm ci
npm run lint
```

**What it checks**:

- JavaScript/TypeScript errors
- React best practices
- Code style violations
- Potential bugs

#### 10. Prettier

**Tool**: `prettier`
**Target**: `frontend/src/`
**Duration**: ~20s

```bash
npm ci
npm run format:check
```

**What it checks**:

- Code formatting consistency
- Style violations

---

## Workflow Configuration

### Matrix Definition

```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - id: yamllint
        name: "YAML Lint"
        cmd: |
          pip install yamllint
          yamllint .github/

      - id: ruff-check
        name: "Ruff Check"
        working-directory: backend
        cmd: |
          pip install poetry
          poetry install --only dev
          poetry run ruff check rag_solution/ --line-length 120

      # ... (9 more linters)
```

### Conditional Setup

```yaml
- name: 🐍 Set up Python 3.12
  if: contains(matrix.id, 'ruff') || contains(matrix.id, 'mypy')
  uses: actions/setup-python@v4

- name: 🟢 Set up Node.js
  if: contains(matrix.id, 'eslint') || contains(matrix.id, 'prettier')
  uses: actions/setup-node@v4
```

**Why Conditional**: Don't install Python for frontend linters (faster)

---

## Comparison

### Before: Monolithic Lint

```yaml
- name: Run all linters
  run: make lint  # Black box, no visibility
```

**Problems**:

- ❌ Sequential execution (slow)
- ❌ First failure stops everything
- ❌ No visibility into which linter failed
- ❌ Must re-run entire suite to retry

### After: Matrix Lint

```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - {id: ruff, ...}
      - {id: mypy, ...}
      # ...
```

**Benefits**:

- ✅ Parallel execution (fast)
- ✅ See all failures
- ✅ Clear visibility per linter
- ✅ Retry individual linters

---

## Usage Examples

### Local Development

Run linters locally before pushing:

```bash
# Quick check (all linters)
make quick-check

# Specific linters
cd backend
poetry run ruff check rag_solution/
poetry run mypy rag_solution/

# Frontend linters
cd frontend
npm run lint
npm run format:check
```

### CI/CD

Linters run automatically on:

- Every pull request to `main`
- Every push to `main`

### Fixing Issues

#### Python Style Issues (Ruff)

```bash
# Auto-fix most issues
cd backend
poetry run ruff check rag_solution/ --fix

# Format code
poetry run ruff format rag_solution/
```

#### Type Issues (MyPy)

```bash
# See type errors
cd backend
poetry run mypy rag_solution/

# Fix by adding type hints
def my_function(arg: str) -> int:
    return len(arg)
```

#### Frontend Issues (ESLint)

```bash
# Auto-fix
cd frontend
npm run lint -- --fix

# Format
npm run format
```

---

## Performance Optimization

### Caching

```yaml
- uses: actions/setup-python@v4
  with:
    cache: 'pip'  # Cache pip dependencies

- uses: actions/setup-node@v4
  with:
    cache: 'npm'  # Cache npm dependencies
```

**Result**: 30-60s saved on cache hits

### Parallel Execution

```yaml
jobs:
  lint:
    strategy:
      matrix:
        include: [...10 linters...]
```

**Result**: All linters run simultaneously (GitHub provides 5-10 concurrent runners)

---

## Troubleshooting

### Common Issues

#### 1. Poetry Install Fails

**Error**: `poetry: command not found`

**Solution**:

```yaml
- name: Install Poetry
  run: pip install poetry
```

#### 2. Ruff Not Found

**Error**: `ruff: command not found`

**Solution**:

```yaml
- name: Install dependencies
  run: |
    cd backend
    poetry install --only dev
```

#### 3. ESLint Fails

**Error**: `Module not found`

**Solution**:

```yaml
- name: Install frontend dependencies
  run: |
    cd frontend
    npm ci  # Use 'ci' instead of 'install' for CI
```

### Debugging Tips

1. **Check job logs**: Each linter has its own log
2. **Run locally**: Test the exact command from workflow
3. **Check cache**: Clear cache if dependencies are stale
4. **Verify paths**: Ensure `working-directory` is correct

---

## Future Enhancements

### Phase 2 Additions

- [ ] Add `bandit` (security linting for Python)
- [ ] Add `hadolint` (Dockerfile linting)
- [ ] Add `shellcheck` (shell script linting)

### Coverage Integration

- [ ] Add coverage gates to each linter
- [ ] Report coverage per linter type
- [ ] Trend analysis over time

---

## References

- **Ruff**: https://docs.astral.sh/ruff/
- **MyPy**: https://mypy.readthedocs.io/
- **ESLint**: https://eslint.org/
- **Prettier**: https://prettier.io/

---

## Related Documentation

- [CI/CD Overview](index.md) - Complete pipeline architecture
- [Contributing](../contributing.md) - Code quality guidelines
- [Development Workflow](../workflow.md) - Local development practices

---

!!! tip "Adding New Linters"
    To add a new linter, add an entry to the `matrix.include` array in `01-lint.yml`. Each entry needs:

    - `id`: Unique identifier
    - `name`: Display name
    - `cmd`: Command to run
    - `working-directory`: (optional) Directory to run in

    Example:
    ```yaml
    - id: new-linter
      name: "New Linter"
      working-directory: backend
      cmd: |
        pip install new-linter
        new-linter check rag_solution/
    ```

