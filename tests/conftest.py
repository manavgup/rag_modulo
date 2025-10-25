"""Global test fixtures and configuration."""


# Add pytest markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "error: mark test as error handling test")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "service: mark test as service layer test")
    config.addinivalue_line("markers", "repository: mark test as repository layer test")
    config.addinivalue_line("markers", "schema: mark test as schema validation test")
    config.addinivalue_line("markers", "router: mark test as API endpoint test")
    config.addinivalue_line("markers", "auth: mark test as authentication test")
    config.addinivalue_line("markers", "watsonx: mark test as WatsonX integration test")
    config.addinivalue_line("markers", "pipeline: mark test as RAG pipeline test")
    config.addinivalue_line("markers", "config: mark test as configuration test")
    config.addinivalue_line("markers", "slow: mark test as long-running test")
    config.addinivalue_line("markers", "critical: mark test as critical for daily CI runs")

# Import fixtures from subdirectories
# Import fixtures from subdirectories
pytest_plugins = [
    "tests.fixtures.auth",
    "tests.fixtures.integration",
    "tests.fixtures.user",
]
