# Pre-PR Check

Run the full pre-PR validation checklist for the current branch.

Execute these checks in order, stopping on first failure:

1. `make quick-check` - Format and lint check
2. `make test-unit-fast` - Unit tests
3. `poetry run mypy backend/rag_solution/ --config-file pyproject.toml --ignore-missing-imports` - Type check
4. Check for any files that shouldn't be committed:
   - .env files
   - __pycache__ directories
   - .pyc files
   - Large binary files
5. `git diff --stat main...HEAD` - Show summary of all changes vs main

Report a clear PASS/FAIL for each step.
At the end, summarize: ready to PR or list what needs fixing.
