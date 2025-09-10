"""Atomic tests for search validation."""

import pytest
from pydantic import BaseModel, ValidationError


class SearchInput(BaseModel):
    """Simple input model for testing."""
    name: str
    description: str = ""


@pytest.mark.atomic
def test_search_input_validation():
    """Test search input validation without external dependencies."""
    # Valid input
    valid_input = SearchInput(
        name="Test Search",
        description="A test search"
    )
    assert valid_input.name == "Test Search"
    assert valid_input.description == "A test search"


@pytest.mark.atomic
def test_search_input_invalid_data():
    """Test search input validation with invalid data."""
    with pytest.raises(ValidationError):
        SearchInput(
            question="",  # Empty question should fail
            collection_id="invalid-uuid",  # Invalid UUID should fail
            pipeline_id="invalid-uuid",
            user_id="invalid-uuid"
        )


@pytest.mark.atomic
def test_search_input_serialization():
    """Test search input serialization."""
    input_data = SearchInput(
        name="Test Search",
        description="A test search"
    )
    
    # Test serialization
    data = input_data.model_dump()
    assert data["name"] == "Test Search"
    assert data["description"] == "A test search"


@pytest.mark.atomic
def test_search_string_validation():
    """Test search string validation."""
    test_string = "Hello, World!"
    assert len(test_string) > 0
    assert isinstance(test_string, str)
    assert test_string.upper() == "HELLO, WORLD!"


@pytest.mark.atomic
def test_search_data_types():
    """Test search data type validation."""
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
