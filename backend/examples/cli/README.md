# CLI Examples

This directory contains example scripts demonstrating how to use the RAG Modulo CLI.

## test_workflow.py

A comprehensive test script that demonstrates the complete CLI workflow:

1. **Authentication Setup**: Configures mock authentication for testing
2. **Collection Creation**: Creates a new collection
3. **Document Upload**: Uploads a PDF document to the collection
4. **Processing Wait**: Polls collection status until processing completes
5. **Search Execution**: Performs a search query on the processed documents

### Usage

```bash
# Run the test workflow
python backend/examples/cli/test_workflow.py

# Prerequisites:
# 1. Backend server running on http://localhost:8000
# 2. TESTING=true or SKIP_AUTH=true environment variable set
# 3. A PDF file at the path specified in the script
```

### Features Demonstrated

- Mock authentication setup
- Collection management
- Document upload with status monitoring
- Search with automatic user context and pipeline resolution
- Error handling and retry logic

### Environment Variables

- `TESTING=true` - Enable mock authentication
- `SKIP_AUTH=true` - Bypass authentication checks
- `MOCK_TOKEN` - Custom mock token (default: dev-0000-0000-0000)

This script is particularly useful for:
- Testing CLI functionality after code changes
- Demonstrating the CLI workflow to new developers
- Validating the complete document processing pipeline
- Debugging authentication and search issues
