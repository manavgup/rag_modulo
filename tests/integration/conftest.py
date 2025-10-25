"""Integration test fixtures and configuration."""


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")

# Made with Bob
