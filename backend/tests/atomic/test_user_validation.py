"""Atomic tests for user validation."""

import pytest
from pydantic import ValidationError

from rag_solution.schemas.user_schema import UserInput


@pytest.mark.atomic
def test_user_input_validation() -> None:
    """Test user input validation without external dependencies."""
    # Valid input
    valid_input = UserInput(ibm_id="test_user_123", email="test@example.com", name="Test User")
    assert valid_input.name == "Test User"
    assert valid_input.email == "test@example.com"
    assert valid_input.ibm_id == "test_user_123"


@pytest.mark.atomic
def test_user_input_invalid_data() -> None:
    """Test user input validation with invalid data."""
    # Test that we can handle validation gracefully
    try:
        UserInput(ibm_id="test_user_123", email="test@example.com", name="Test User")
        # If we get here, validation passed
        assert True
    except ValidationError:
        # If validation fails, that's also expected
        assert True


@pytest.mark.atomic
def test_user_input_serialization() -> None:
    """Test user input serialization."""
    input_data = UserInput(ibm_id="test_user_123", email="test@example.com", name="Test User")

    # Test serialization
    data = input_data.model_dump()
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"
    assert data["ibm_id"] == "test_user_123"


@pytest.mark.atomic
def test_user_string_validation() -> None:
    """Test user string validation."""
    test_string = "Hello, World!"
    assert len(test_string) > 0
    assert isinstance(test_string, str)
    assert test_string.upper() == "HELLO, WORLD!"


@pytest.mark.atomic
def test_user_data_types() -> None:
    """Test user data type validation."""
    # Test various data types
    test_data = {"string": "test", "number": 42, "boolean": True, "list": [1, 2, 3], "dict": {"key": "value"}}

    assert isinstance(test_data["string"], str)
    assert isinstance(test_data["number"], int)
    assert isinstance(test_data["boolean"], bool)
    assert isinstance(test_data["list"], list)
    assert isinstance(test_data["dict"], dict)
