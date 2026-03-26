# Search Test

Run search-related tests specifically.

Execute:

1. `poetry run pytest tests/unit/services/test_search_service.py -v --tb=short`
2. `poetry run pytest tests/unit/services/test_mcp_gateway_client.py -v --tb=short`
3. If integration infra is running (`docker compose ps` shows healthy):
   `poetry run pytest tests/integration/ -k search -v --tb=short`

Report results for each test file.
