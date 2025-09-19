# Development and Testing Tools

This directory contains development utilities, manual test scripts, and experimental code that is NOT part of the official test suite.

## Structure

### `/manual/`
Manual test scripts for testing specific features or debugging issues:
- `test_cot_comparison.py` - Compare Chain of Thought vs regular search
- `test_cot_llm_integration.py` - Test CoT with LLM provider integration
- `test_cot_manual.py` - Manual CoT testing
- `test_cot_with_documents.py` - Test CoT with document retrieval
- `test_cot_workflow.py` - Complete CoT workflow testing
- `test_regular_search.py` - Regular search testing
- `test_settings_only.py` - Settings configuration testing

### `/examples/`
Example scripts demonstrating CLI and API usage:
- `/cli/` - CLI usage examples and interactive workflows

### `/experiments/`
Experimental code and prototypes:
- Various experimental scripts for testing new features
- Performance testing scripts
- Integration experiments

## Usage

These scripts are designed to be run manually from the backend directory:

```bash
cd backend

# Run a manual test
python dev_tests/manual/test_cot_comparison.py

# Run a CLI example
python dev_tests/examples/cli/test_workflow.py

# Run an experiment
python dev_tests/experiments/hello_milvus.py
```

## Important Notes

- These are NOT pytest tests - they are standalone scripts
- They may require specific environment variables or running services
- They are used for development, debugging, and feature exploration
- The official test suite is in the `tests/` directory
