"""Integration tests for UserCollectionService."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException

from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.schemas.user_collection_schema import UserCollectionOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.user_collection_service import UserCollectionService


# -------------------------------------------
# 🧪 Collection Access Tests
# -------------------------------------------
def test_get_user_collections(user_collection_service: UserCollectionService, base_user: UserOutput, base_collection: CollectionOutput) -> None:
    """Test fetching user collections."""
    result = user_collection_service.get_user_collections(base_user.id)

    assert len(result) == 1
    assert isinstance(result[0], CollectionOutput)
    assert result[0].id == base_collection.id
    assert result[0].name == base_collection.name


def test_get_user_collections_empty(user_collection_service: UserCollectionService, base_user: UserOutput) -> None:
    """Test fetching collections for user with no collections."""
    # First remove user from any existing collections
    existing_collections = user_collection_service.get_user_collections(base_user.id)
    for collection in existing_collections:
        user_collection_service.remove_user_from_collection(base_user.id, collection.id)

    result = user_collection_service.get_user_collections(base_user.id)
    assert len(result) == 0


# -------------------------------------------
# 🧪 Collection Membership Tests
# -------------------------------------------
def test_add_user_to_collection(user_collection_service: UserCollectionService, base_user: UserOutput, base_collection: CollectionOutput) -> None:
    """Test adding user to collection."""
    result = user_collection_service.add_user_to_collection(base_user.id, base_collection.id)

    assert result is True

    # Verify user was added
    collections = user_collection_service.get_user_collections(base_user.id)
    assert any(c.id == base_collection.id for c in collections)


def test_add_user_to_collection_duplicate(user_collection_service: UserCollectionService, base_user: UserOutput, base_collection: CollectionOutput) -> None:
    """Test adding user to collection when already added."""
    # First addition should succeed
    user_collection_service.add_user_to_collection(base_user.id, base_collection.id)

    # Second addition should fail
    with pytest.raises(HTTPException) as exc_info:
        user_collection_service.add_user_to_collection(base_user.id, base_collection.id)
    assert exc_info.value.status_code == 400
    assert "User already has access to collection" in str(exc_info.value.detail)


def test_add_user_to_nonexistent_collection(user_collection_service: UserCollectionService, base_user: UserOutput) -> None:
    """Test adding user to nonexistent collection."""
    with pytest.raises(HTTPException) as exc_info:
        user_collection_service.add_user_to_collection(base_user.id, uuid4())
    assert exc_info.value.status_code == 404
    assert "User or collection not found" in str(exc_info.value.detail)


def test_remove_user_from_collection(user_collection_service: UserCollectionService, base_user: UserOutput, base_collection: CollectionOutput) -> None:
    """Test removing user from collection."""
    # First add user to collection
    user_collection_service.add_user_to_collection(base_user.id, base_collection.id)

    result = user_collection_service.remove_user_from_collection(base_user.id, base_collection.id)

    assert result is True

    # Verify user was removed
    collections = user_collection_service.get_user_collections(base_user.id)
    assert not any(c.id == base_collection.id for c in collections)


def test_remove_user_not_in_collection(user_collection_service: UserCollectionService, base_user: UserOutput, base_collection: CollectionOutput) -> None:
    """Test removing user that's not in collection."""
    with pytest.raises(HTTPException) as exc_info:
        user_collection_service.remove_user_from_collection(base_user.id, base_collection.id)
    assert exc_info.value.status_code == 404
    assert "User does not have access to collection" in str(exc_info.value.detail)


# -------------------------------------------
# 🧪 Collection Users Tests
# -------------------------------------------
def test_get_collection_users(user_collection_service: UserCollectionService, base_user: UserOutput, base_collection: CollectionOutput) -> None:
    """Test fetching users for a collection."""
    # Add user to collection
    user_collection_service.add_user_to_collection(base_user.id, base_collection.id)

    result = user_collection_service.get_collection_users(base_collection.id)

    assert len(result) == 1
    assert isinstance(result[0], UserCollectionOutput)
    assert result[0].user_id == base_user.id


def test_get_users_nonexistent_collection(user_collection_service: UserCollectionService) -> None:
    """Test fetching users for nonexistent collection."""
    with pytest.raises(HTTPException) as exc_info:
        user_collection_service.get_collection_users(uuid4())
    assert exc_info.value.status_code == 404
    assert "Collection not found" in str(exc_info.value.detail)


def test_remove_all_users_from_collection(
    user_collection_service: UserCollectionService,
    user_service: Any,
    base_user: UserOutput,
    base_collection: CollectionOutput,
) -> None:
    """Test removing all users from a collection."""
    # Add multiple users
    users = [base_user]
    for i in range(2):
        user = user_service.create_user_by_fields(ibm_id=f"test{i}", email=f"test{i}@example.com", name=f"Test User {i}")
        users.append(user)
        user_collection_service.add_user_to_collection(user.id, base_collection.id)

    # Remove all users
    result = user_collection_service.remove_all_users_from_collection(base_collection.id)
    assert result is True

    # Verify all users were removed
    for user in users:
        collections = user_collection_service.get_user_collections(user.id)
        assert not any(c.id == base_collection.id for c in collections)


def test_remove_all_users_nonexistent_collection(user_collection_service: UserCollectionService) -> None:
    """Test removing all users from nonexistent collection."""
    with pytest.raises(HTTPException) as exc_info:
        user_collection_service.remove_all_users_from_collection(uuid4())
    assert exc_info.value.status_code == 404
    assert "Collection not found" in str(exc_info.value.detail)


if __name__ == "__main__":
    pytest.main([__file__])
