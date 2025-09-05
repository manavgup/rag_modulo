import pytest
from fastapi import HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session

from rag_solution.repository.user_team_repository import UserTeamRepository
from rag_solution.schemas.collection_schema import CollectionInput
from rag_solution.schemas.user_schema import UserInput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.user_collection_service import UserCollectionService
from rag_solution.services.user_service import UserService
from rag_solution.services.user_team_service import UserTeamService


@pytest.fixture
def user_collection_service(db_session: Session) -> UserCollectionService:
    return UserCollectionService(db_session)


@pytest.fixture
def user_team_repository(db_session: Session) -> UserTeamRepository:
    return UserTeamRepository(db_session)


@pytest.fixture
def user_team_service(db_session: Session) -> UserTeamService:
    return UserTeamService(db_session)


@pytest.fixture
def user_service(db_session: Session) -> UserService:
    return UserService(db_session)


@pytest.fixture
def file_management_service(db_session: Session) -> FileManagementService:
    return FileManagementService(db_session)


@pytest.fixture
def collection_service(db_session: Session) -> CollectionService:
    return CollectionService(db_session)


@pytest.mark.atomic
def test_add_user_to_collection(
    user_collection_service: UserCollectionService,
    user_service: UserService,
    collection_service: CollectionService,
    db_session: Session,
) -> None:
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    collection = collection_service.create_collection(CollectionInput(name="Test Collection", is_private=True, users=[user.id]))

    user2 = user_service.create_user(UserInput(ibm_id="new_test_ibm_id", email="test@example.com", name="Test User"))
    result = user_collection_service.add_user_to_collection(user2.id, collection.id)
    assert result is True

    user_collections = user_collection_service.get_user_collections(user.id)
    assert len(user_collections) == 1
    assert user_collections[0].id == collection.id


def test_remove_user_from_collection(
    user_collection_service: UserCollectionService,
    user_service: UserService,
    collection_service: CollectionService,
    db_session: Session,
) -> None:
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    collection = collection_service.create_collection(CollectionInput(name="Test Collection", is_private=True, users=[user.id]))

    user2 = user_service.create_user(UserInput(ibm_id="new_test_ibm_id", email="test@example.com", name="Test User"))
    result = user_collection_service.add_user_to_collection(user2.id, collection.id)
    assert (len(user_collection_service.get_collection_users(collection.id))) == 2

    result = user_collection_service.remove_user_from_collection(user.id, collection.id)
    assert (len(user_collection_service.get_collection_users(collection.id))) == 1
    assert result is True

    user_collections = user_collection_service.get_user_collections(user.id)
    assert len(user_collections) == 0


def test_get_user_collections(
    user_collection_service: UserCollectionService,
    user_service: UserService,
    collection_service: CollectionService,
    db_session: Session,
) -> None:
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    collection1 = collection_service.create_collection(CollectionInput(name="Test Collection 1", is_private=True, users=[user.id]))
    collection2 = collection_service.create_collection(CollectionInput(name="Test Collection 2", is_private=False, users=[user.id]))

    user_collections = user_collection_service.get_user_collections(user.id)
    assert len(user_collections) == 2
    assert {collection1.id, collection2.id} == {uc.id for uc in user_collections}


def test_get_collection_users(
    user_collection_service: UserCollectionService,
    user_service: UserService,
    collection_service: CollectionService,
    db_session: Session,
) -> None:
    user1 = user_service.create_user(UserInput(ibm_id="test_ibm_id1", email="test1@example.com", name="Test User 1"))
    user2 = user_service.create_user(UserInput(ibm_id="test_ibm_id2", email="test2@example.com", name="Test User 2"))
    collection = collection_service.create_collection(CollectionInput(name="Test Collection", is_private=True, users=[user1.id, user2.id]))

    collection_users = user_collection_service.get_collection_users(collection.id)
    assert len(collection_users) == 2
    assert {user1.id, user2.id} == {user.id for user in collection_users}


def test_add_user_to_nonexistent_collection(user_collection_service: UserCollectionService, user_service: UserService) -> None:
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    with pytest.raises(HTTPException) as exc_info:
        user_collection_service.add_user_to_collection(user.id, UUID4("00000000-0000-0000-0000-000000000000"))
    assert exc_info.value.status_code == 404


def test_remove_user_from_nonexistent_collection(user_collection_service: UserCollectionService, user_service: UserService) -> None:
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    with pytest.raises(HTTPException) as exc_info:
        user_collection_service.remove_user_from_collection(user.id, UUID4("00000000-0000-0000-0000-000000000000"))
    assert exc_info.value.status_code == 404


def test_get_collections_for_nonexistent_user(user_collection_service: UserCollectionService) -> None:
    collections = user_collection_service.get_user_collections(UUID4("00000000-0000-0000-0000-000000000000"))
    assert len(collections) == 0


def test_get_users_for_nonexistent_collection(user_collection_service: UserCollectionService) -> None:
    users = user_collection_service.get_collection_users(UUID4("00000000-0000-0000-0000-000000000000"))
    assert len(users) == 0
