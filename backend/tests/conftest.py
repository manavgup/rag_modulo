"""Pytest configuration file.

This file serves as the main pytest configuration, handling:
1. Logging setup and configuration
2. Importing fixtures from the fixtures package
"""

import logging

import pytest

from core.logging_utils import get_logger, setup_logging

logger = get_logger("tests.conftest")

# Define collect_ignore at module level
collect_ignore = ["backend/tests.bak", "backend/tests_backup"]
collect_ignore_glob = ["tests.bak/*", "tests_backup/*"]


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
    setup_logging()

    # Set root logger to DEBUG for tests
    logging.getLogger().setLevel(logging.DEBUG)

    # Configure specific loggers
    loggers_config = {
        # Database loggers - keep at CRITICAL to reduce noise
        "sqlalchemy": logging.CRITICAL,
        "sqlalchemy.engine": logging.CRITICAL,
        "sqlalchemy.engine.base.Engine": logging.CRITICAL,
        "sqlalchemy.dialects": logging.CRITICAL,
        "sqlalchemy.pool": logging.CRITICAL,
        "sqlalchemy.orm": logging.CRITICAL,
        # Network loggers - keep at CRITICAL to reduce noise
        "urllib3": logging.CRITICAL,
        "asyncio": logging.CRITICAL,
        "aiohttp": logging.CRITICAL,
        # Application loggers - set to DEBUG for detailed info
        "ibm_watsonx_ai": logging.DEBUG,
        "llm.providers": logging.DEBUG,
        "tests.conftest": logging.DEBUG,
        "tests.fixtures": logging.DEBUG,
    }

    for logger_name, level in loggers_config.items():
        logging.getLogger(logger_name).setLevel(level)

    logger.info("Test logging configured")
