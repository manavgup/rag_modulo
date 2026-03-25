---
name: Testing Conventions
description: RAG Modulo test patterns, markers, fixtures, and mock conventions. Trigger when writing new tests, fixing test failures, or adding test coverage.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Testing Conventions

## Test File Location

- Unit: `tests/unit/services/test_<name>.py`, `tests/unit/models/test_<name>.py`
- Integration: `tests/integration/test_<name>_integration.py`
- API: `tests/api/test_<name>.py`
- Schema: `tests/unit/schemas/test_<name>.py`

## Required Marker

Every test file MUST have the appropriate marker:

```python
import pytest
pytestmark = pytest.mark.unit  # or integration, e2e, atomic
```

## Mock Patterns

- Use `unittest.mock.patch` and `MagicMock` for service dependencies
- Mock at the import path where the dependency is used, not where defined
- Use `conftest.py` fixtures for shared mocks within a directory
- Async tests: use `pytest.mark.asyncio` (asyncio_mode = "auto")

## Assertions

- Prefer specific assertions: `assert result.status == "success"` over `assert result`
- Test both success and error paths
- Test edge cases: empty input, None values, boundary conditions
