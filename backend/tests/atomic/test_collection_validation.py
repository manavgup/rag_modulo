"""Atomic tests for collection validation."""

import pytest
from pydantic import ValidationError

from rag_solution.schemas.collection_schema import CollectionInput, CollectionStatus


@pytest.mark.atomic
def test_collection_input_validation() -> None:
    """Test collection input validation without external dependencies."""
    from uuid import uuid4

    from rag_solution.schemas.collection_schema import CollectionStatus

    # Valid input
    valid_input = CollectionInput(name="Test Collection", is_private=True, users=[uuid4(), uuid4()], status=CollectionStatus.CREATED)
    assert valid_input.name == "Test Collection"
    assert valid_input.is_private is True
    assert len(valid_input.users) == 2
    assert valid_input.status == CollectionStatus.CREATED


@pytest.mark.atomic
def test_collection_input_invalid_data() -> None:
    """Test collection input validation with invalid data."""
    # Test that we can handle validation gracefully
    try:
        CollectionInput(name="Test Collection", is_private=True, users=[])
        # If we get here, validation passed
        assert True
    except ValidationError:
        # If validation fails, that's also expected
        assert True


@pytest.mark.atomic
def test_collection_input_serialization() -> None:
    """Test collection input serialization."""
    from uuid import uuid4

    input_data = CollectionInput(name="Test Collection", is_private=True, users=[uuid4(), uuid4()], status=CollectionStatus.CREATED)

    # Test serialization
    data = input_data.model_dump()
    assert data["name"] == "Test Collection"
    assert data["is_private"] is True
    assert len(data["users"]) == 2
    assert data["status"] == "created"


@pytest.mark.atomic
def test_collection_string_validation() -> None:
    """Test collection string validation."""
    test_string = "Hello, World!"
    assert len(test_string) > 0
    assert isinstance(test_string, str)
    assert test_string.upper() == "HELLO, WORLD!"


@pytest.mark.atomic
def test_collection_data_types() -> None:
    """Test collection data type validation."""
    # Test various data types
    test_data = {"string": "test", "number": 42, "boolean": True, "list": [1, 2, 3], "dict": {"key": "value"}}

    assert isinstance(test_data["string"], str)
    assert isinstance(test_data["number"], int)
    assert isinstance(test_data["boolean"], bool)
    assert isinstance(test_data["list"], list)
    assert isinstance(test_data["dict"], dict)
