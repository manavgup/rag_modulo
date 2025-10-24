# Make Targets Verification Checklist

**Purpose:** Verify all make targets work after moving pyproject.toml to project root

**Context:**
- pyproject.toml moved from `backend/pyproject.toml` to project root
- Scripts moved from `backend/scripts/` to `scripts/`
- Need to verify all poetry and path-dependent commands still work

---

## All Make Targets (32 total)

```
build-all          build-backend      build-frontend     check-docker
clean              clean-all          clean-venv         coverage
create-volumes     format             help               lint
local-dev-all      local-dev-backend  local-dev-frontend local-dev-infra
local-dev-setup    local-dev-status   local-dev-stop     logs
pre-commit-run     prod-logs          prod-restart       prod-start
prod-status        prod-stop          quick-check        security-check
test-all           test-atomic        test-integration   test-unit-fast
venv
```

---

## Critical Targets to Verify

### Development Setup
- [ ] `make local-dev-setup` - Install backend & frontend dependencies
  - Expected: Poetry installs packages, npm installs packages
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make venv` - Create virtual environment
  - Expected: .venv created with poetry
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make clean-venv` - Remove virtual environment
  - Expected: .venv directory removed
  - Status: ⏳ Not tested
  - Notes:

### Local Development
- [ ] `make local-dev-infra` - Start infrastructure (DB, Milvus, etc.)
  - Expected: Docker containers start
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make local-dev-backend` - Start backend with hot-reload
  - Expected: Uvicorn starts on port 8000
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make local-dev-frontend` - Start frontend with HMR
  - Expected: React dev server on port 3000
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make local-dev-all` - Start all services in background
  - Expected: All services running
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make local-dev-status` - Check service status
  - Expected: Shows running/stopped services
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make local-dev-stop` - Stop all local services
  - Expected: All services stopped
  - Status: ⏳ Not tested
  - Notes:

### Code Quality
- [ ] `make lint` - Run all linters (Ruff, MyPy, Pylint)
  - Expected: Linting completes without errors
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make format` - Format code with Ruff
  - Expected: Code formatted in-place
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make quick-check` - Fast quality check
  - Expected: Format + lint + basic checks
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make pre-commit-run` - Run pre-commit hooks manually
  - Expected: All hooks pass
  - Status: ⏳ Not tested
  - Notes:

### Testing
- [ ] `make test-unit-fast` - Run unit tests
  - Expected: Unit tests pass
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make test-integration` - Run integration tests
  - Expected: Integration tests pass
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make test-atomic` - Run atomic tests
  - Expected: Atomic tests pass
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make test-all` - Run all tests
  - Expected: All test suites pass
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make coverage` - Generate coverage report
  - Expected: Coverage report generated
  - Status: ⏳ Not tested
  - Notes:

### Security
- [ ] `make security-check` - Run security scans (Gitleaks)
  - Expected: Security scans complete
  - Status: ⏳ Not tested
  - Notes:

### Build
- [ ] `make build-backend` - Build backend Docker image
  - Expected: Docker image builds successfully
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make build-frontend` - Build frontend Docker image
  - Expected: Docker image builds successfully
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make build-all` - Build all Docker images
  - Expected: All images build
  - Status: ⏳ Not tested
  - Notes:

### Utilities
- [ ] `make clean` - Clean build artifacts
  - Expected: __pycache__, *.pyc removed
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make clean-all` - Deep clean (includes Docker)
  - Expected: All artifacts removed
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make logs` - View service logs
  - Expected: Docker compose logs shown
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make help` - Show help message
  - Expected: All targets listed
  - Status: ⏳ Not tested
  - Notes:

### Production
- [ ] `make prod-start` - Start production services
  - Expected: Production containers start
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make prod-stop` - Stop production services
  - Expected: Production containers stop
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make prod-restart` - Restart production
  - Expected: Services restart
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make prod-status` - Check production status
  - Expected: Shows service status
  - Status: ⏳ Not tested
  - Notes:

- [ ] `make prod-logs` - View production logs
  - Expected: Shows logs
  - Status: ⏳ Not tested
  - Notes:

---

## Priority Order for Testing

**Phase 1: Critical (MUST WORK)**
1. `make local-dev-setup` - Without this, nothing else works
2. `make lint` - Code quality checks
3. `make test-unit-fast` - Basic functionality
4. `make local-dev-backend` - Development iteration
5. `make quick-check` - Fast feedback

**Phase 2: Important (SHOULD WORK)**
1. `make local-dev-frontend` - UI development
2. `make format` - Code formatting
3. `make test-integration` - Full testing
4. `make pre-commit-run` - Git workflow
5. `make security-check` - Security

**Phase 3: Nice to Have (CAN WORK LATER)**
1. `make build-all` - Docker builds
2. `make prod-*` - Production commands
3. `make coverage` - Coverage reports
4. `make clean-all` - Cleanup utilities

---

## Known Issues

### Potential Breaking Changes from pyproject.toml Move

**Before:**
```bash
cd backend
poetry install
poetry run pytest
```

**After:**
```bash
# From project root
poetry install
poetry run pytest backend/tests/
```

**Affected Targets:**
- Any target with `cd backend && poetry ...`
- Any target with hardcoded `backend/pyproject.toml`
- Any target with `PYTHONPATH=backend`

### Potential Breaking Changes from Scripts Move

**Before:**
```bash
python backend/scripts/wipe_database.py
```

**After:**
```bash
python scripts/wipe_database.py
```

**Affected Targets:**
- None currently (scripts not in Makefile)

---

## Testing Commands

```bash
# Quick smoke test of critical targets
make help
make local-dev-setup
make lint
make test-unit-fast
make local-dev-backend  # In separate terminal

# Full verification
for target in lint format test-unit-fast quick-check; do
  echo "Testing: make $target"
  make $target || echo "FAILED: $target"
done
```

---

## Results Summary

**Tested:** 0 / 32
**Passed:** 0
**Failed:** 0
**Skipped:** 32

**Status:** ⏳ Not Started

---

## Next Steps

1. Run Phase 1 critical targets
2. Fix any failures
3. Document fixes in CURRENT_ISSUES.md
4. Run Phase 2 important targets
5. Create PR #5 once all targets verified

---

*Last Updated: 2025-10-24*
*Status: Waiting for testing*
