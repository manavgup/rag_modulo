"""User fixtures for tests."""

from datetime import datetime
from uuid import uuid4

import pytest

from rag_solution.schemas.user_schema import UserOutput


@pytest.fixture(scope="function")
def base_user() -> UserOutput:
    """Create a base user for tests."""
    return UserOutput(id=uuid4(), email="test@example.com", ibm_id="test_user_123", name="Test User", role="user", preferred_provider_id=None, created_at=datetime.now(), updated_at=datetime.now())
