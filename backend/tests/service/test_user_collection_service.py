"""Integration tests for UserCollectionService."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from rag_solution.models.collection import Collection
from rag_solution.models.user import User
from rag_solution.models.user_collection import UserCollection
from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.schemas.user_collection_schema import UserCollectionOutput
from rag_solution.services.user_collection_service import UserCollectionService


@pytest.fixture
def test_collection(db_session: Session) -> Collection:
    """Create a test collection."""
    collection = Collection(name="Test Collection", is_private=False, vector_db_name=f"collection_{uuid4().hex}", status="created")
    db_session.add(collection)
    db_session.commit()
    db_session.refresh(collection)
    return collection


def test_get_user_collections(db_session: Session, base_user: User, test_collection: Collection) -> None:
    """Test fetching user collections."""
    # Add user to collection
    user_collection = UserCollection(user_id=base_user.id, collection_id=test_collection.id)
    db_session.add(user_collection)
    db_session.commit()

    service = UserCollectionService(db_session)
    result = service.get_user_collections(base_user.id)

    assert len(result) == 1
    assert isinstance(result[0], CollectionOutput)
    assert result[0].id == test_collection.id
    assert result[0].name == test_collection.name


def test_add_user_to_collection(db_session: Session, base_user: User, test_collection: Collection) -> None:
    """Test adding user to collection."""
    service = UserCollectionService(db_session)

    result = service.add_user_to_collection(base_user.id, test_collection.id)

    assert result is True
    # Verify relationship exists
    user_collection = db_session.query(UserCollection).filter_by(user_id=base_user.id, collection_id=test_collection.id).first()
    assert user_collection is not None


def test_add_user_to_collection_duplicate(db_session: Session, base_user: User, test_collection: Collection) -> None:
    """Test adding user to collection when already added."""
    service = UserCollectionService(db_session)

    # First addition should succeed
    service.add_user_to_collection(base_user.id, test_collection.id)

    # Second addition should fail
    with pytest.raises(HTTPException) as exc_info:
        service.add_user_to_collection(base_user.id, test_collection.id)
    assert exc_info.value.status_code == 400
    assert "User already has access to collection" in str(exc_info.value.detail)


def test_add_user_to_nonexistent_collection(db_session: Session, base_user: User) -> None:
    """Test adding user to nonexistent collection."""
    service = UserCollectionService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.add_user_to_collection(base_user.id, uuid4())
    assert exc_info.value.status_code == 404
    assert "Collection not found" in str(exc_info.value.detail)


def test_remove_user_from_collection(db_session: Session, base_user: User, test_collection: Collection) -> None:
    """Test removing user from collection."""
    # First add user to collection
    user_collection = UserCollection(user_id=base_user.id, collection_id=test_collection.id)
    db_session.add(user_collection)
    db_session.commit()

    service = UserCollectionService(db_session)
    result = service.remove_user_from_collection(base_user.id, test_collection.id)

    assert result is True
    # Verify relationship is removed
    removed_user_collection: UserCollection | None = db_session.query(UserCollection).filter_by(user_id=base_user.id, collection_id=test_collection.id).first()
    assert removed_user_collection is None


def test_remove_user_not_in_collection(db_session: Session, base_user: User, test_collection: Collection) -> None:
    """Test removing user that's not in collection."""
    service = UserCollectionService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.remove_user_from_collection(base_user.id, test_collection.id)
    assert exc_info.value.status_code == 404
    assert "User does not have access to collection" in str(exc_info.value.detail)


def test_get_collection_users(db_session: Session, base_user: User, test_collection: Collection) -> None:
    """Test fetching users for a collection."""
    # Add user to collection
    user_collection = UserCollection(user_id=base_user.id, collection_id=test_collection.id)
    db_session.add(user_collection)
    db_session.commit()

    service = UserCollectionService(db_session)
    result = service.get_collection_users(test_collection.id)

    assert len(result) == 1
    assert isinstance(result[0], UserCollectionOutput)
    assert result[0].user_id == base_user.id
    assert result[0].name == base_user.name


def test_get_users_nonexistent_collection(db_session: Session) -> None:
    """Test fetching users for nonexistent collection."""
    service = UserCollectionService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.get_collection_users(uuid4())
    assert exc_info.value.status_code == 404
    assert "Collection not found" in str(exc_info.value.detail)


def test_remove_all_users_from_collection(db_session: Session, base_user: User, test_collection: Collection) -> None:
    """Test removing all users from a collection."""
    # Add multiple users
    user1 = User(ibm_id="test1", email="test1@example.com", name="Test User 1")
    user2 = User(ibm_id="test2", email="test2@example.com", name="Test User 2")
    db_session.add_all([user1, user2])
    db_session.flush()

    # Add users to collection
    user_collections = [
        UserCollection(user_id=base_user.id, collection_id=test_collection.id),
        UserCollection(user_id=user1.id, collection_id=test_collection.id),
        UserCollection(user_id=user2.id, collection_id=test_collection.id),
    ]
    db_session.add_all(user_collections)
    db_session.commit()

    service = UserCollectionService(db_session)
    result = service.remove_all_users_from_collection(test_collection.id)

    assert result is True
    # Verify all relationships are removed
    count = db_session.query(UserCollection).filter_by(collection_id=test_collection.id).count()
    assert count == 0


def test_remove_all_users_nonexistent_collection(db_session: Session) -> None:
    """Test removing all users from nonexistent collection."""
    service = UserCollectionService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.remove_all_users_from_collection(uuid4())
    assert exc_info.value.status_code == 404
    assert "Collection not found" in str(exc_info.value.detail)


if __name__ == "__main__":
    pytest.main([__file__])
