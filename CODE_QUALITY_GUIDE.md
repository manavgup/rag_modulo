# 🔍 Comprehensive Code Quality and Linting Infrastructure

This guide explains how to use the enhanced code quality and linting infrastructure that matches the comprehensive standards from the mcp_auto_pr project.

## 🎯 Quick Start

### Fast Quality Check (Recommended for daily development)
```bash
make check-fast
```
This runs essential checks in ~30 seconds:
- Format checking (no changes)
- Basic linting with Ruff

### Comprehensive Quality Check
```bash
make check-quality
```
This runs comprehensive checks in ~2-3 minutes:
- Code formatting
- Basic linting
- Strict type checking with MyPy

### Strictest Quality Requirements
```bash
make strict
```
This runs all quality checks including:
- All formatting and linting
- Strict type checking
- 80% docstring coverage requirement
- Doctest execution

## 🛠️ Available Quality Targets

### 1. **Fast Quality Checks** (`make check-fast`)
- **Purpose**: Quick feedback during development
- **Time**: ~30 seconds
- **Use case**: Before committing, during development
- **Includes**: Format checking + basic linting

### 2. **Style Checks** (`make check-style`)
- **Purpose**: Check code style without making changes
- **Time**: ~15 seconds
- **Use case**: Verify formatting before committing
- **Includes**: Format checking only

### 3. **Comprehensive Quality** (`make check-quality`)
- **Purpose**: Thorough quality assessment
- **Time**: ~2-3 minutes
- **Use case**: Before major commits, PR reviews
- **Includes**: Formatting + linting + strict type checking

### 4. **Strictest Requirements** (`make strict`)
- **Purpose**: Highest quality standards
- **Time**: ~3-5 minutes
- **Use case**: Release preparation, quality gates
- **Includes**: All checks + docstring coverage + doctests

### 5. **Code Analysis** (`make analyze`)
- **Purpose**: Detailed code metrics and insights
- **Time**: ~1-2 minutes
- **Use case**: Code review, quality assessment
- **Includes**: Statistics and error context

## 🔍 Individual Tool Targets

### Ruff Linting and Formatting
```bash
# Check linting issues
make lint-ruff

# Auto-format code
make format-ruff

# Check formatting without changes
make format-check
```

### MyPy Type Checking
```bash
# Basic type checking (relaxed)
make lint-mypy

# Strict type checking
make lint-mypy-strict
```

### Docstring Quality
```bash
# Basic docstring coverage (50% threshold)
make lint-docstrings

# Strict docstring coverage (80% threshold)
make lint-docstrings-strict
```

### Documentation Testing
```bash
# Run doctest examples
make test-doctest
```

## 📊 Quality Standards

### Docstring Coverage
- **Basic**: 50% threshold (existing standard)
- **Strict**: 80% threshold (new standard)
- **Exclusions**: Tests, private methods, magic methods

### Type Checking
- **Basic**: Relaxed with missing import handling
- **Strict**: Full strict mode with explicit warnings
- **Configuration**: Comprehensive MyPy settings

### Code Formatting
- **Line length**: 120 characters
- **Style**: Black-compatible
- **Import sorting**: Automatic with Ruff

## 🚀 Development Workflow

### Daily Development
1. **During coding**: Use `make check-fast` for quick feedback
2. **Before commit**: Use `make check-quality` for thorough review
3. **For PRs**: Use `make strict` to meet quality gates

### Quality Improvement
1. **Start with**: `make analyze` to see current state
2. **Fix formatting**: `make format` to auto-fix issues
3. **Address linting**: Fix issues reported by `make lint`
4. **Improve types**: Use `make lint-mypy-strict` for guidance
5. **Add documentation**: Use `make lint-docstrings-strict` to identify gaps

### CI Integration
The new targets are designed to integrate with CI workflows:
- `check-fast`: Run on every commit (non-blocking)
- `check-quality`: Run on PR creation (quality gate)
- `strict`: Run on merge to main (strict gate)

## 📁 Configuration Files

### Ruff Configuration (`.ruff.toml`)
- Comprehensive linting rules
- Black-compatible formatting
- Import sorting configuration
- Python 3.12 target

### MyPy Configuration (`mypy.ini`)
- Strict type checking settings
- External package handling
- Comprehensive error reporting
- Pydantic plugin configuration

### Interrogate Configuration (`.interrogate`)
- 80% docstring coverage threshold
- Smart exclusions for tests and utilities
- Verbose output for detailed analysis

### Pydocstyle Configuration (`.pydocstyle`)
- Google docstring convention
- Comprehensive style checking
- Test and utility exclusions

## 🧪 Doctest Examples

The enhanced `doc_utils.py` demonstrates proper doctest usage:

```python
def clean_text(text: Optional[str]) -> str:
    """
    Clean and normalize text by removing special characters and extra whitespace.

    Examples:
        >>> clean_text("Hello, World! How are you?")
        'Hello World How are you'
        
        >>> clean_text("Text@#$%^&*()with!@#$%^&*()symbols")
        'Text with symbols'
    """
    # Implementation...
```

### Running Doctests
```bash
# Run all doctests
make test-doctest

# Run doctests for specific module
cd backend && poetry run pytest --doctest-modules rag_solution/doc_utils.py -v

# Run doctests directly
cd backend && python -m doctest rag_solution/doc_utils.py -v
```

## 🔧 Troubleshooting

### Common Issues

#### MyPy Strict Mode Fails
- **Solution**: Start with `make lint-mypy` to see basic issues
- **Gradual**: Fix type issues incrementally
- **Configuration**: Check `mypy.ini` for specific settings

#### Docstring Coverage Low
- **Solution**: Use `make lint-docstrings` to see current coverage
- **Focus**: Add docstrings to public functions and classes
- **Exclusions**: Check `.interrogate` configuration

#### Ruff Formatting Issues
- **Solution**: Use `make format` to auto-fix
- **Manual**: Check `.ruff.toml` for rule configuration
- **Line length**: Ensure 120 character limit

### Performance Tips
- **Fast feedback**: Use `make check-fast` during development
- **Incremental**: Fix issues in small batches
- **Parallel**: Some tools support parallel execution
- **Cache**: Tools cache results for faster subsequent runs

## 📈 Quality Metrics

### Coverage Targets
- **Docstrings**: 80% (vs previous 50%)
- **Type coverage**: Comprehensive with strict mode
- **Linting**: Zero issues with current rules
- **Formatting**: 100% consistent

### Success Indicators
- ✅ All quality targets pass
- ✅ Doctest examples execute successfully
- ✅ CI workflows complete without errors
- ✅ Code review time reduced
- ✅ Fewer runtime errors

## 🔗 References

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Strict Mode](https://mypy.readthedocs.io/en/stable/strict_mode.html)
- [Interrogate Documentation](https://interrogate.readthedocs.io/)
- [Pydocstyle Rules](https://www.pydocstyle.org/en/stable/error_codes.html)
- [Doctest Documentation](https://docs.python.org/3/library/doctest.html)

## 🎯 Next Steps

1. **Install dependencies**: `cd backend && poetry install`
2. **Test targets**: Try `make check-fast` to see current state
3. **Gradual improvement**: Use `make analyze` to identify areas for improvement
4. **Team adoption**: Share this guide with your team
5. **CI integration**: Add new targets to your CI workflows

---

*This enhanced infrastructure provides the same comprehensive code quality standards as the mcp_auto_pr project, with improved developer experience and clear quality gates.*
