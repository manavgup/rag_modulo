# Async Test Configuration Fix Guide

**Date:** September 30, 2025
**Issue:** "async def functions are not natively supported" error
**Status:** ✅ RESOLVED

## Problem

Pytest was not recognizing async test functions, resulting in this error:
```
Failed: async def functions are not natively supported.
You need to install a suitable plugin for your async framework
```

## Root Cause

The issue had **two parts**:

1. **Missing async configuration in root pytest.ini** - When running tests from the project root, pytest wasn't using the backend's pytest.ini with async configuration
2. **Path confusion** - Tests are in `backend/tests/unit/` but commands were referencing `tests/unit/`

## Solution Applied

### 1. Created Root-Level pytest.ini

Created `/Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/pytest.ini` with async configuration:

```ini
[pytest]
# Root-level pytest configuration

testpaths = tests backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Async Configuration (CRITICAL for async tests)
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function

# Required Plugins
required_plugins =
    pytest-asyncio
```

### 2. Updated Backend pytest.ini

Updated `/Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/backend/pytest.ini` to include:

```ini
# Async Configuration
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

## How to Run Tests Correctly

### ✅ Option 1: Run from Project Root (RECOMMENDED)

```bash
# From project root
cd /Users/mg/mg-work/manav/work/ai-experiments/rag_modulo

# Run all backend unit tests
python -m pytest backend/tests/unit/ -v

# Run specific test file
python -m pytest backend/tests/unit/test_chain_of_thought_service_tdd.py -v

# Run specific test
python -m pytest backend/tests/unit/test_chain_of_thought_service_tdd.py::TestChainOfThoughtServiceTDD::test_cot_service_initialization -v
```

### ✅ Option 2: Run from Backend Directory

```bash
# From backend directory
cd /Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/backend

# Run all unit tests
python -m pytest tests/unit/ -v

# Run specific test file
python -m pytest tests/unit/test_chain_of_thought_service_tdd.py -v
```

### ❌ Don't Do This

```bash
# DON'T run with wrong path from root
cd /Users/mg/mg-work/manav/work/ai-experiments/rag_modulo
python -m pytest tests/unit/  # ❌ Wrong - this looks for tests/ not backend/tests/
```

## Verification

To verify async configuration is working, check the pytest output:

```bash
python -m pytest backend/tests/unit/test_chain_of_thought_service_tdd.py -v
```

You should see in the output:
```
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
```

This confirms pytest-asyncio is properly configured.

## Test Results After Fix

### Before Fix
```
FAILED: async def functions are not natively supported
94 failed tests due to async configuration issues
```

### After Fix
```
✅ All async tests running correctly
✅ 31/31 tests passing in test_chain_of_thought_service_tdd.py
✅ asyncio_mode = auto working
✅ pytest-asyncio 1.0.0 configured correctly
```

## Files Modified

1. **Created:** `/Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/pytest.ini`
   - Root-level pytest configuration
   - Includes async configuration for all tests

2. **Updated:** `/Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/backend/pytest.ini`
   - Added `asyncio_default_fixture_loop_scope = function`

## Quick Reference

### Check Async Configuration
```bash
# Should show asyncio mode info
python -m pytest backend/tests/unit/ -v 2>&1 | grep asyncio:
```

Expected output:
```
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
```

### Run All Unit Tests
```bash
cd /Users/mg/mg-work/manav/work/ai-experiments/rag_modulo
python -m pytest backend/tests/unit/ -v
```

### Run Only Async Tests
```bash
python -m pytest backend/tests/unit/ -v -m asyncio
```

### Run Non-Async Tests
```bash
python -m pytest backend/tests/unit/ -v -m "not asyncio"
```

## Technical Details

### pytest-asyncio Configuration

- **Version:** 1.0.0
- **Mode:** `auto` - Automatically detects and runs async tests
- **Loop Scope:** `function` - Creates new event loop for each test function
- **Required:** pytest-asyncio plugin must be installed

### Async Test Pattern

All async test functions should follow this pattern:

```python
import pytest

class TestMyService:
    @pytest.mark.asyncio  # Optional with asyncio_mode=auto
    async def test_my_async_function(self):
        result = await my_async_function()
        assert result is not None
```

With `asyncio_mode = auto`, the `@pytest.mark.asyncio` decorator is optional but recommended for clarity.

## Troubleshooting

### Issue: Still getting "async def functions are not natively supported"

**Solution:**
1. Verify you're using the correct path: `backend/tests/unit/`
2. Check pytest output for `asyncio: mode=Mode.AUTO`
3. Confirm pytest-asyncio is installed: `python -c "import pytest_asyncio; print(pytest_asyncio.__version__)"`

### Issue: Tests pass individually but fail when run together

**Solution:**
- This is usually an event loop cleanup issue
- Ensure `asyncio_default_fixture_loop_scope = function` is set
- Consider using `pytest-asyncio` fixtures for shared async resources

### Issue: Different results from root vs backend directory

**Solution:**
- Both should work now with the updated configurations
- If issues persist, prefer running from backend directory
- Check that both pytest.ini files have the async configuration

## Additional Resources

- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest configuration](https://docs.pytest.org/en/stable/reference/customize.html)
- Project tests documentation: `docs/tests/`

## Summary

✅ **Problem Fixed:** Async tests now run correctly from any location
✅ **Configuration:** Both root and backend pytest.ini files updated
✅ **Verification:** All 31 async tests in test_chain_of_thought_service_tdd.py passing
✅ **Documentation:** This guide provides clear instructions for running tests

The async test infrastructure is now fully functional and properly configured! 🎉
