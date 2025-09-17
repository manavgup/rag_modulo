# Project-Level Tests

This directory contains tests for project-level functionality, including Makefile targets and CLI testing.

## Quick Start

### Recommended: Use the Smart Test Runner
```bash
./tests/run_makefile_tests.sh
```

### Or Run Direct Tests (macOS/Local Development)
```bash
pytest tests/test_makefile_targets_direct.py -v
```

## Test Files

- **`test_makefile_targets_direct.py`** ⭐ - Direct host testing (recommended for macOS)
- **`test_makefile_targets.py`** - Container-based testing (for CI/CD)
- **`run_makefile_tests.sh`** - Smart test runner script

## Documentation

For comprehensive testing documentation, see:
- **[Makefile Testing Guide](../docs/testing/makefile-testing.md)** - Detailed testing strategies
- **[Testing Strategy](../docs/testing/TESTING_STRATEGY.md)** - Overall testing approach
- **[Comprehensive Testing Guide](../docs/testing/COMPREHENSIVE_TESTING_GUIDE.md)** - Full test suite documentation

## Common Commands

```bash
# Check Docker requirements
make check-docker

# Run fast tests only
pytest tests/test_makefile_targets_direct.py -k "not slow" -v

# Skip Docker-in-Docker tests if they fail
export SKIP_DOCKER_IN_DOCKER_TESTS=true
pytest tests/test_makefile_targets.py -v
```

## Need Help?

1. **Permission issues**: Use `test_makefile_targets_direct.py`
2. **Docker problems**: Run `make check-docker`
3. **General guidance**: Use `./run_makefile_tests.sh`
4. **Detailed docs**: See `docs/testing/` directory
