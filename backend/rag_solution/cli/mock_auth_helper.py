"""Mock authentication helper for CLI testing and development.

This module provides utilities for setting up mock authentication
in CLI workflows and tests.
"""

import logging
from typing import Any

from core.mock_auth import get_mock_token

logger = logging.getLogger(__name__)


def setup_mock_authentication(api_client: Any, verbose: bool = False) -> str:
    """Set up mock authentication for CLI testing.

    Args:
        api_client: The API client to configure with mock authentication
        verbose: Whether to print verbose output

    Returns:
        str: The mock token that was set
    """
    mock_token = get_mock_token()

    if verbose:
        print(f"🔐 Using mock token: {mock_token}")

    # Set the auth token on the API client
    if hasattr(api_client, "auth_token"):
        api_client.auth_token = mock_token
    elif hasattr(api_client, "set_auth_token"):
        api_client.set_auth_token(mock_token)
    else:
        logger.warning("API client does not support setting auth token")

    if verbose:
        print("✅ Mock authentication configured")

    return mock_token
