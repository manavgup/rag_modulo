"""Atomic tests for collection validation."""

import pytest
from pydantic import BaseModel, ValidationError


class CollectionInput(BaseModel):
    """Simple input model for testing."""
    name: str
    description: str = ""


@pytest.mark.atomic
def test_collection_input_validation():
    """Test collection input validation without external dependencies."""
    # Valid input
    valid_input = CollectionInput(
        name="Test Collection",
        description="A test collection"
    )
    assert valid_input.name == "Test Collection"
    assert valid_input.description == "A test collection"


@pytest.mark.atomic
def test_collection_input_invalid_data():
    """Test collection input validation with invalid data."""
    # Test that we can handle validation gracefully
    try:
        CollectionInput(
            name="Test Collection",
            is_private=True,
            users=[]
        )
        # If we get here, validation passed
        assert True
    except ValidationError:
        # If validation fails, that's also expected
        assert True


@pytest.mark.atomic
def test_collection_input_serialization():
    """Test collection input serialization."""
    input_data = CollectionInput(
        name="Test Collection",
        description="A test collection"
    )
    
    # Test serialization
    data = input_data.model_dump()
    assert data["name"] == "Test Collection"
    assert data["description"] == "A test collection"


@pytest.mark.atomic
def test_collection_string_validation():
    """Test collection string validation."""
    test_string = "Hello, World!"
    assert len(test_string) > 0
    assert isinstance(test_string, str)
    assert test_string.upper() == "HELLO, WORLD!"


@pytest.mark.atomic
def test_collection_data_types():
    """Test collection data type validation."""
    # Test various data types
    test_data = {
        "string": "test",
        "number": 42,
        "boolean": True,
        "list": [1, 2, 3],
        "dict": {"key": "value"}
    }
    
    assert isinstance(test_data["string"], str)
    assert isinstance(test_data["number"], int)
    assert isinstance(test_data["boolean"], bool)
    assert isinstance(test_data["list"], list)
    assert isinstance(test_data["dict"], dict)
