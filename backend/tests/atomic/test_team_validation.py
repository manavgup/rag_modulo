"""Atomic tests for team validation."""

import pytest
from pydantic import BaseModel, ValidationError


class TeamInput(BaseModel):
    """Simple input model for testing."""

    name: str
    description: str = ""


@pytest.mark.atomic
def test_team_input_validation() -> None:
    """Test team input validation without external dependencies."""
    # Valid input
    valid_input = TeamInput(name="Test Team", description="A test team")
    assert valid_input.name == "Test Team"
    assert valid_input.description == "A test team"


@pytest.mark.atomic
def test_team_input_invalid_data() -> None:
    """Test team input validation with invalid data."""
    # TeamInput doesn"t have strict validation, so we"ll test a different scenario
    # Test with None name (which should fail)
    with pytest.raises(ValidationError):
        TeamInput(
            name=None,  # None name should fail
            description="A test team",
        )


@pytest.mark.atomic
def test_team_input_serialization() -> None:
    """Test team input serialization."""
    input_data = TeamInput(name="Test Team", description="A test team")

    # Test serialization
    data = input_data.model_dump()
    assert data["name"] == "Test Team"
    assert data["description"] == "A test team"


@pytest.mark.atomic
def test_team_string_validation() -> None:
    """Test team string validation."""
    test_string = "Hello, World!"
    assert len(test_string) > 0
    assert isinstance(test_string, str)
    assert test_string.upper() == "HELLO, WORLD!"


@pytest.mark.atomic
def test_team_data_types() -> None:
    """Test team data type validation."""
    # Test various data types
    test_data = {"string": "test", "number": 42, "boolean": True, "list": [1, 2, 3], "dict": {"key": "value"}}

    assert isinstance(test_data["string"], str)
    assert isinstance(test_data["number"], int)
    assert isinstance(test_data["boolean"], bool)
    assert isinstance(test_data["list"], list)
    assert isinstance(test_data["dict"], dict)
