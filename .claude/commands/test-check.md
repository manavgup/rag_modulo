# Test Check

Run the fastest relevant tests for the current work. Usage: /test-check [path]

If a path is provided, run tests for that specific file or directory.
If no path is provided, detect what changed and run the appropriate test tier:

1. Check `git diff --name-only` for changed files
2. If only schema files changed: `make test-atomic`
3. If service/repository/model files changed: `poetry run pytest tests/unit/services/ -v --tb=short`
4. If router files changed: `poetry run pytest tests/api/ -v --tb=short`
5. If frontend files changed: `cd frontend && npm test`
6. If unsure: `make test-unit-fast`

Always show the test command before running it.
Report pass/fail count and any failures clearly.
