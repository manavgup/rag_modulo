#!/usr/bin/env python3
"""Script to run the token tracking E2E test with detailed logging."""

import logging
import os
import sys

# Add the backend directory to sys.path
backend_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, backend_dir)


def setup_logging():
    """Set up detailed logging for the test."""
    # Create a custom formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # Set up specific loggers for our services
    service_loggers = [
        "rag_solution.services.conversation_service",
        "rag_solution.services.search_service",
        "rag_solution.services.chain_of_thought_service",
        "rag_solution.services.token_tracking_service",
        "rag_solution.router.chat_router",
        "rag_solution.router.search_router",
        "tests.e2e.test_token_tracking_e2e_tdd",
    ]

    for logger_name in service_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.addHandler(console_handler)


def run_test():
    """Run the specific token tracking test."""
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting token tracking E2E test...")

    try:
        import pytest

        # Run the specific test with verbose output
        test_path = "tests/e2e/test_token_tracking_e2e_tdd.py::TestTokenTrackingE2ETDD::test_conversation_process_message_returns_token_usage"

        logger.info(f"📋 Running test: {test_path}")

        # Run pytest with specific options
        exit_code = pytest.main(
            [
                test_path,
                "-v",  # verbose
                "-s",  # don't capture output (show print statements)
                "--tb=short",  # shorter traceback
                "--log-cli-level=INFO",  # show INFO level logs
                "--log-cli-format=%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
                "--log-cli-date-format=%Y-%m-%d %H:%M:%S",
            ]
        )

        if exit_code == 0:
            logger.info("✅ Test completed successfully!")
        else:
            logger.error(f"❌ Test failed with exit code: {exit_code}")

        return exit_code

    except Exception as e:
        logger.error(f"❌ Error running test: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = run_test()
    sys.exit(exit_code)
