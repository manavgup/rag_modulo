# CI/CD Workflows

## Structure (one workflow per purpose)

- `01-lint.yml` - Ruff, MyPy, Pylint, Pydocstyle (~60s)
- `02-security.yml` - Gitleaks + TruffleHog (~45s)
- `03-build-secure.yml` - Docker builds (path-filtered)
- `04-pytest.yml` - Unit tests with coverage (~90s)
- `05-ci.yml` - Integration tests (push to main only)
- `06-weekly-security-audit.yml` - Deep vulnerability scan (Monday 2AM UTC)
- `07-frontend-lint.yml` - ESLint (frontend changes only)

## Conventions

- Concurrency control: auto-cancels outdated runs
- Smart path filtering: Docker builds only when code/deps change
- All PR workflows run in parallel (~2-3 min total)
