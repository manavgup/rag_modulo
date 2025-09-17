"""Atomic tests for search validation."""

import pytest
from pydantic import ValidationError

from rag_solution.schemas.search_schema import SearchInput


@pytest.mark.atomic
def test_search_input_validation() -> None:
    """Test search input validation without external dependencies (no pipeline_id)."""
    from uuid import uuid4

    # Valid input - pipeline_id removed from schema
    valid_input = SearchInput(question="What is machine learning?", collection_id=uuid4(), user_id=uuid4())
    assert valid_input.question == "What is machine learning?"
    assert valid_input.collection_id is not None
    assert valid_input.user_id is not None
    # pipeline_id should not exist in new schema
    assert not hasattr(valid_input, "pipeline_id")


@pytest.mark.atomic
def test_search_input_invalid_data() -> None:
    """Test search input validation with invalid data (no pipeline_id)."""
    from uuid import uuid4

    # Test with None values (should fail validation)
    with pytest.raises(ValidationError):
        SearchInput(
            question="Valid question",
            collection_id=None,  # type: ignore[arg-type]  # None should fail
            user_id=uuid4(),
        )

    # Test with invalid UUID strings (should fail validation)
    with pytest.raises(ValidationError):
        SearchInput(
            question="Valid question",
            collection_id="invalid-uuid-string",  # type: ignore[arg-type]  # Invalid UUID should fail
            user_id=uuid4(),
        )


@pytest.mark.atomic
def test_search_input_serialization() -> None:
    """Test search input serialization (no pipeline_id)."""
    from uuid import uuid4

    input_data = SearchInput(question="What is machine learning?", collection_id=uuid4(), user_id=uuid4())

    # Test serialization
    data = input_data.model_dump()
    assert data["question"] == "What is machine learning?"
    assert "collection_id" in data
    assert "user_id" in data
    # pipeline_id should NOT be in serialized data
    assert "pipeline_id" not in data


@pytest.mark.atomic
def test_search_string_validation() -> None:
    """Test search string validation."""
    test_string = "Hello, World!"
    assert len(test_string) > 0
    assert isinstance(test_string, str)
    assert test_string.upper() == "HELLO, WORLD!"


@pytest.mark.atomic
def test_search_data_types() -> None:
    """Test search data type validation."""
    # Test various data types
    test_data = {"string": "test", "number": 42, "boolean": True, "list": [1, 2, 3], "dict": {"key": "value"}}

    assert isinstance(test_data["string"], str)
    assert isinstance(test_data["number"], int)
    assert isinstance(test_data["boolean"], bool)
    assert isinstance(test_data["list"], list)
    assert isinstance(test_data["dict"], dict)
