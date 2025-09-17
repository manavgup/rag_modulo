# Makefile Testing Guide

## Overview

This guide covers testing strategies for RAG Modulo's Makefile targets, with specific focus on Docker-in-Docker alternatives for macOS development.

## Quick Start

### For macOS Users (Recommended)
```bash
# 1. Check Docker requirements
make check-docker

# 2. Run direct tests (avoids Docker-in-Docker issues)
python -m pytest tests/test_makefile_targets_direct.py -v

# 3. Or use the smart test runner
./tests/run_makefile_tests.sh
```

### For CI/CD Environments
```bash
# Container-based tests for full isolation
python -m pytest tests/test_makefile_targets.py -v
```

## Test Files

### `tests/test_makefile_targets_direct.py` ⭐ **Recommended**
**Direct Host Testing**
- Runs tests directly on host system
- Creates temporary project copies for isolation
- Uses host Docker daemon directly
- Avoids Docker-in-Docker permission issues
- Best for local development on macOS

### `tests/test_makefile_targets.py`
**Container-Based Testing**
- Runs tests inside isolated Ubuntu containers
- Full Docker-in-Docker setup
- Better for CI/CD environments
- May have permission issues on some systems

## Docker-in-Docker Alternatives on macOS

### Why Docker-in-Docker is Problematic on Mac
- Docker Desktop already runs in a Linux VM
- Socket permission complexities
- Requires privileged container mode
- Additional overhead and complexity

### Alternative Approaches

#### 1. **Direct Testing** (Implemented) ⭐
Use host Docker daemon directly through temporary project copies.

#### 2. **Lima/Colima**
```bash
brew install colima
colima start
# Provides more native Docker experience
```

#### 3. **Podman**
```bash
brew install podman
podman machine init
podman machine start
# Rootless containers with better permission handling
```

#### 4. **GitHub Actions**
Use CI/CD for comprehensive Docker-in-Docker testing:
```yaml
name: Makefile Tests
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run container tests
        run: pytest tests/test_makefile_targets.py -v
```

## Test Infrastructure

### Smart Test Runner
`tests/run_makefile_tests.sh` provides:
- Automatic Docker requirement checking
- Permission issue detection
- Test approach recommendations
- Interactive mode selection

### Docker Compose V2 Requirement
The project has standardized on Docker Compose V2:
- Legacy `docker-compose` (V1) is not supported
- Use `docker compose` command (V2)
- Run `make check-docker` to verify installation

### Environment Variables
- `SKIP_DOCKER_IN_DOCKER_TESTS=true`: Skip container-based tests
- Use when experiencing permission issues

## Common Issues and Solutions

### Permission Denied Errors
```bash
# Solution 1: Use direct tests
python -m pytest tests/test_makefile_targets_direct.py -v

# Solution 2: Skip Docker-in-Docker tests
export SKIP_DOCKER_IN_DOCKER_TESTS=true
python -m pytest tests/test_makefile_targets.py -v

# Solution 3: Use smart test runner
./tests/run_makefile_tests.sh
```

### Docker Compose V2 Not Found
```bash
# Check current setup
make check-docker

# macOS: Update Docker Desktop
# Ubuntu/Debian: sudo apt-get install docker-compose-plugin
```

### Test Timeouts
```bash
# Skip slow tests
python -m pytest tests/test_makefile_targets_direct.py -k "not slow" -v

# Or adjust timeout in test files
```

## Test Categories

Tests are organized by pytest markers:
- `@pytest.mark.makefile`: Makefile-specific tests
- `@pytest.mark.slow`: Long-running tests
- `@pytest.mark.docker`: Docker-dependent tests

## Integration with Development Workflow

### Before Committing Changes
```bash
# Validate Makefile changes
./tests/run_makefile_tests.sh

# Or specific test
python -m pytest tests/test_makefile_targets_direct.py::TestMakefileTargetsDirect::test_make_dev_init -v
```

### Adding New Makefile Targets
1. Add target to Makefile
2. Add corresponding test to `test_makefile_targets_direct.py`
3. Follow existing test patterns
4. Document any special requirements

## Best Practices

### For Test Development
1. **Use direct tests for development**: More reliable on macOS
2. **Test both success and failure cases**: Handle missing dependencies
3. **Provide clear error messages**: Help debugging
4. **Clean up resources**: Prevent test pollution

### For CI/CD
1. **Use both test approaches**: Comprehensive coverage
2. **Set appropriate timeouts**: Handle slow operations
3. **Cache Docker images**: Improve performance
4. **Fail fast on syntax errors**: Catch issues early

## Related Documentation

- [Comprehensive Testing Guide](COMPREHENSIVE_TESTING_GUIDE.md)
- [Manual Validation Checklist](MANUAL_VALIDATION_CHECKLIST.md)
- [Development Workflow](../development/workflow.md)
- [Environment Setup](../development/environment-setup.md)

## Future Improvements

### Planned Enhancements
- Cross-platform testing validation
- Performance benchmarking integration
- Automated test result reporting
- Enhanced CI/CD integration

### Contributing
When adding new Makefile targets or modifying existing ones:
1. Update corresponding tests
2. Test on multiple platforms if possible
3. Document any new requirements
4. Follow existing test patterns

This approach ensures reliable, maintainable testing of Makefile targets while providing alternatives for different development environments.
