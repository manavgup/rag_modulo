"""Pytest configuration file.

This file serves as the main pytest configuration, handling:
1. Test environment setup
2. Basic test fixtures
3. Avoiding main application imports during test setup
"""

import logging
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient
from pathlib import Path

# Set up test environment before any imports
os.environ["TESTING"] = "true"
os.environ["CONTAINER_ENV"] = "false"

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("tests.conftest")

# Define collect_ignore at module level
collect_ignore = ["tests.bak", "tests_backup"]
collect_ignore_glob = ["tests.bak/*", "tests_backup/*"]

@pytest.fixture(scope="session")
def app():
    """Create a test application instance.
    
    This fixture creates the FastAPI app only when needed,
    avoiding import-time side effects.
    """
    # Import here to avoid side effects during test collection
    from backend.main import app
    return app

@pytest_asyncio.fixture
async def client(app):
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture(autouse=True)
def capture_logs(caplog):
    """Capture logs during tests."""
    caplog.set_level(logging.INFO)

@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for tests.
    
    This fixture:
    - Sets up basic logging configuration
    - Configures log levels for different components
    - Runs automatically at the start of test session
    """
    # Set root logger to DEBUG for tests
    logging.getLogger().setLevel(logging.DEBUG)
    
    # Configure specific loggers
    loggers_config = {
        # Database loggers - keep at CRITICAL to reduce noise
        'sqlalchemy': logging.CRITICAL,
        'sqlalchemy.engine': logging.CRITICAL,
        'sqlalchemy.engine.base.Engine': logging.CRITICAL,
        'sqlalchemy.dialects': logging.CRITICAL,
        'sqlalchemy.pool': logging.CRITICAL,
        'sqlalchemy.orm': logging.CRITICAL,
        
        # Network loggers - keep at CRITICAL to reduce noise
        'urllib3': logging.CRITICAL,
        'asyncio': logging.CRITICAL,
        'aiohttp': logging.CRITICAL,
        
        # Application loggers - set to DEBUG for detailed info
        'ibm_watsonx_ai': logging.DEBUG,
        'llm.providers': logging.DEBUG,
        'tests.conftest': logging.DEBUG,
    }
    
    for logger_name, level in loggers_config.items():
        logging.getLogger(logger_name).setLevel(level)
        
    logger.info("Test logging configured")

@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "data"

@pytest.fixture(scope="session")
def test_files_dir():
    """Provide path to test files directory."""
    return Path(__file__).parent / "test_files"
