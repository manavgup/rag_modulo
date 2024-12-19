import logging
import uuid
from io import BytesIO

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile
from rag_solution.repository.collection_repository import CollectionRepository
from rag_solution.repository.user_repository import UserRepository
from rag_solution.schemas.collection_schema import (CollectionInput, CollectionOutput)
from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.user_collection_service import UserCollectionService
from rag_solution.services.user_service import UserService
from sqlalchemy.orm import Session
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def collection_input(user_input):
    return CollectionInput(
        name="Test_Collection",
        is_private=True,
        users=[uuid.UUID(user_input.ibm_id)]
    )

@pytest.fixture
def user_repository(db_session):
    return UserRepository(db_session)

@pytest.fixture
def collection_repository(db_session):
    return CollectionRepository(db_session)

@pytest.fixture
def user_service(db_session: Session):
    return UserService(db_session)

@pytest.fixture
def file_management_service(db_session):
    return FileManagementService(db_session)

@pytest.fixture
def user_collection_service(db_session):
    return UserCollectionService(db_session)

@pytest.fixture
def collection_service(db_session):
    logger.debug("Initializing CollectionService")
    service = CollectionService(db_session)
    logger.debug("CollectionService initialized successfully")
    return service

def test_create_collection(user_service: UserService, collection_service: CollectionService):
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    collection_input = CollectionInput(name="Test Collection", is_private=True, users=[user.id])
    created_collection = collection_service.create_collection(collection_input)
    assert created_collection.name == collection_input.name
    assert created_collection.is_private == collection_input.is_private
    assert user.id in created_collection.user_ids
    assert created_collection.vector_db_name.startswith("collection_")

def test_get_collection(user_service: UserService, collection_service: CollectionService, collection_input: CollectionInput):
    # Create a user first
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    collection_input = CollectionInput(name="Test Collection", is_private=True, users=[user.id])
    created_collection = collection_service.create_collection(collection_input)

    retrieved_collection = collection_service.get_collection(created_collection.id)
    assert retrieved_collection is not None
    assert retrieved_collection.id == created_collection.id

def test_update_collection(collection_service: CollectionService, collection_input: CollectionInput,
                           user_service: UserService, user_input: UserInput):
    # Create the user using the user_input fixture
    user = user_service.create_user(user_input)
    collection_input = CollectionInput(name="Test Collection", is_private=True, users=[user.id])
    created_collection = collection_service.create_collection(collection_input)

    update_data = CollectionInput(
        name="Updated Collection",
        is_private=False,
        users=[user.id]
    )
    updated_collection = collection_service.update_collection(created_collection.id, update_data)
    assert updated_collection.name == "Updated Collection"
    assert updated_collection.is_private is False

def test_delete_collection(collection_service: CollectionService, collection_input: CollectionInput,
                           user_service: UserService, user_input: UserInput):
    # Create a user
    user = user_service.create_user(user_input)

    # Create a collection for that user
    collection_input = CollectionInput(name="Test Collection", is_private=True, users=[user.id])
    created_collection = collection_service.create_collection(collection_input)

    # Delete the collection
    assert collection_service.delete_collection(created_collection.id) is True
    with pytest.raises(HTTPException) as exc_info:
        collection_service.get_collection(created_collection.id)
    assert exc_info.value.status_code == 404

    # Verify user-collection association is removed
    user_collections = collection_service.get_user_collections(user.id)
    assert len(user_collections) == 0

def test_create_collection_with_documents(
    collection_service: CollectionService,
    collection_input: CollectionInput,
    user_service: UserService,
    user_input: UserInput,
    file_management_service: FileManagementService
):
    # Create the user using the user_input fixture
    user = user_service.create_user(user_input)

    file_content_1 = b"This is a test file content for file 1"
    file_content_2 = b"This is a test file content for file 2"
    files = [
        UploadFile(filename="test_file_1.txt", file=BytesIO(file_content_1)),
        UploadFile(filename="test_file_2.txt", file=BytesIO(file_content_2))
    ]
    background_tasks = BackgroundTasks()
    created_collection = collection_service.create_collection_with_documents(
        collection_input.name,
        collection_input.is_private,
        user.id,
        files,
        background_tasks
    )
    assert created_collection.name.startswith("Test_Collection")
    assert created_collection.is_private == collection_input.is_private
    assert len(created_collection.user_ids) == 1
    assert user.id in created_collection.user_ids
    collection_files = file_management_service.get_files(created_collection.id)
    assert len(collection_files) == 2
    assert "test_file_1.txt" in collection_files
    assert "test_file_2.txt" in collection_files
    for file in files:
        file_path = file_management_service.get_file_path(created_collection.id, file.filename)
        assert file_path.exists()
        with open(file_path, "rb") as f:
            content = f.read()
            if file.filename == "test_file_1.txt":
                assert content == file_content_1
            elif file.filename == "test_file_2.txt":
                assert content == file_content_2
    file_management_service.delete_files(created_collection.id, ["test_file_1.txt", "test_file_2.txt"])
    collection_service.delete_collection(created_collection.id)
    user_service.delete_user(user.id)

def test_get_user_collections(collection_service: CollectionService,
                              user_service: UserService,
                              collection_input: CollectionInput):
    created_user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    collection_input.users = [created_user.id]
    collection_service.create_collection(collection_input)
    user_collections = collection_service.get_user_collections(created_user.id)
    assert len(user_collections) == 1
    assert user_collections[0].name == collection_input.name
