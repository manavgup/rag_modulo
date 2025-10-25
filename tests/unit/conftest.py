"""Unit test fixtures and configuration."""


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")

# Made with Bob
