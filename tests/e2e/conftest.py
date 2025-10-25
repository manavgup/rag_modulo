"""End-to-end test fixtures and configuration."""


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "critical: mark test as critical for daily CI runs")

# Made with Bob
