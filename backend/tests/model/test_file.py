from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from sqlalchemy.orm import Session

from core.custom_exceptions import NotFoundError
from rag_solution.repository.file_repository import FileRepository
from rag_solution.repository.user_team_repository import UserTeamRepository
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput
from rag_solution.schemas.file_schema import FileInput, FileMetadata, FileOutput
from rag_solution.schemas.user_schema import UserInput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.user_collection_service import UserCollectionService
from rag_solution.services.user_service import UserService
from rag_solution.services.user_team_service import UserTeamService


@pytest.fixture
def file_repository(db_session: Session) -> FileRepository:
    return FileRepository(db_session)


@pytest.fixture
def file_management_service(db_session: Session) -> FileManagementService:
    return FileManagementService(db_session)


@pytest.fixture
def user_team_repository(db_session: Session) -> UserTeamRepository:
    return UserTeamRepository(db_session)


@pytest.fixture
def user_team_service(db_session: Session) -> UserTeamService:
    return UserTeamService(db_session)


@pytest.fixture
def user_collection_service(db_session: Session) -> UserCollectionService:
    return UserCollectionService(db_session)


@pytest.fixture
def collection_service(db_session: Session) -> CollectionService:
    return CollectionService(db_session)


@pytest.fixture
def user_service(db_session: Session) -> UserService:
    return UserService(db_session)


@pytest.fixture
def collection(collection_service: CollectionService, user_service: UserService) -> CollectionOutput:
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    collection_input = CollectionInput(name="Test Collection", is_private=True, users=[user.id])
    return collection_service.create_collection(collection_input)


@pytest.fixture
def mock_upload_file() -> UploadFile:
    return UploadFile(filename="test_file.txt", file=BytesIO(b"Test content"))


@pytest.fixture
def mock_metadata() -> FileMetadata:
    return FileMetadata(
        title="Test File",
        author="John Doe",
        subject="Testing",
        keywords={"tag": "value"},
        creator="Test Suite",
        producer="Pytest",
        creation_date=datetime.now(),
        mod_date=datetime.now(),
        total_pages=1,
    )


@pytest.mark.atomic
def test_create_file_record(file_management_service: FileManagementService, collection: CollectionOutput, mock_upload_file: UploadFile) -> None:
    file_record = file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id")
    assert isinstance(file_record, FileOutput)
    assert file_record.filename == mock_upload_file.filename
    assert file_record.file_type == "text/plain"


def test_get_file_by_id(file_management_service: FileManagementService, collection: CollectionOutput, mock_upload_file: UploadFile) -> None:
    file_record = file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id")
    retrieved_file = file_management_service.get_file_by_id(file_record.id)
    assert retrieved_file.id == file_record.id
    assert retrieved_file.filename == file_record.filename


def test_get_file_by_name(file_management_service: FileManagementService, collection: CollectionOutput, mock_upload_file: UploadFile) -> None:
    file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id")
    retrieved_file = file_management_service.get_file_by_name(collection.id, "test_file.txt")
    assert retrieved_file.filename == "test_file.txt"


def test_update_file(
    file_management_service: FileManagementService,
    collection: CollectionOutput,
    mock_upload_file: UploadFile,
    mock_metadata: FileMetadata,
) -> None:
    file_record = file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id", metadata=mock_metadata)
    updated_file_input = FileInput(
        collection_id=collection.id,
        filename="updated_file.txt",
        file_path=file_record.file_path,
        file_type=file_record.file_type,
        metadata=FileMetadata(title="Updated File", author="Jane Doe"),
    )
    updated_file = file_management_service.update_file(file_record.id, updated_file_input)
    assert updated_file.filename == "updated_file.txt"
    assert updated_file.metadata.author == "Jane Doe"


def test_get_files(file_management_service: FileManagementService, collection: CollectionOutput, mock_upload_file: UploadFile) -> None:
    file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id")
    files = file_management_service.get_files(collection.id)
    assert len(files) == 1
    assert files[0] == "test_file.txt"


def test_get_file_path(file_management_service: FileManagementService, collection: CollectionOutput, mock_upload_file: UploadFile) -> None:
    file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id")
    file_path = file_management_service.get_file_path(collection.id, "test_file.txt")
    assert isinstance(file_path, Path)
    assert file_path.name == "test_file.txt"


def test_delete_file(file_management_service: FileManagementService, collection: CollectionOutput, mock_upload_file: UploadFile) -> None:
    file_record = file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id")
    file_management_service.delete_file(file_record.id)
    with pytest.raises(NotFoundError):
        file_management_service.get_file_by_id(file_record.id)


def test_delete_files(file_management_service: FileManagementService, collection: CollectionOutput, mock_upload_file: UploadFile) -> None:
    file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id")
    assert file_management_service.delete_files(collection.id, ["test_file.txt"]) is True
    files = file_management_service.get_files(collection.id)
    assert len(files) == 0


def test_get_files_by_collection(file_management_service: FileManagementService, collection: CollectionOutput, mock_upload_file: UploadFile) -> None:
    file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id")
    files = file_management_service.get_files_by_collection(collection.id)
    assert len(files) == 1
    assert isinstance(files[0], FileOutput)
    assert files[0].filename == "test_file.txt"


def test_create_file_record_with_metadata(
    file_management_service: FileManagementService,
    collection: CollectionOutput,
    mock_upload_file: UploadFile,
    mock_metadata: FileMetadata,
) -> None:
    file_record = file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id", metadata=mock_metadata)
    assert isinstance(file_record, FileOutput)
    assert file_record.filename == mock_upload_file.filename
    assert file_record.file_type == "text/plain"
    assert file_record.metadata == mock_metadata


def test_get_file_by_id_with_metadata(
    file_management_service: FileManagementService,
    collection: CollectionOutput,
    mock_upload_file: UploadFile,
    mock_metadata: FileMetadata,
) -> None:
    file_record = file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id", metadata=mock_metadata)
    retrieved_file = file_management_service.get_file_by_id(file_record.id)
    assert retrieved_file.id == file_record.id
    assert retrieved_file.filename == file_record.filename
    assert retrieved_file.metadata == mock_metadata


def test_update_file_metadata(
    file_management_service: FileManagementService,
    collection: CollectionOutput,
    mock_upload_file: UploadFile,
    mock_metadata: FileMetadata,
) -> None:
    file_record = file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id", metadata=mock_metadata)
    updated_metadata = FileMetadata(
        title="Updated Test File",
        author="Jane Doe",
        subject="Updated Testing",
        keywords={"tag": "updated_value"},
        creator="Test Suite",
        producer="Pytest",
        creation_date=datetime.now(),
        mod_date=datetime.now(),
        total_pages=2,
    )
    updated_file = file_management_service.update_file_metadata(collection.id, file_record.id, updated_metadata)
    assert updated_file.metadata == updated_metadata


def test_get_files_by_collection_with_metadata(
    file_management_service: FileManagementService,
    collection: CollectionOutput,
    mock_upload_file: UploadFile,
    mock_metadata: FileMetadata,
) -> None:
    file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id", metadata=mock_metadata)
    files = file_management_service.get_files_by_collection(collection.id)
    assert len(files) == 1
    assert isinstance(files[0], FileOutput)
    assert files[0].filename == "test_file.txt"
    assert files[0].metadata == mock_metadata


def test_delete_file_with_metadata(
    file_management_service: FileManagementService,
    collection: CollectionOutput,
    mock_upload_file: UploadFile,
    mock_metadata: FileMetadata,
) -> None:
    file_record = file_management_service.upload_and_create_file_record(mock_upload_file, collection.user_ids[0], collection.id, "test_document_id", metadata=mock_metadata)
    file_management_service.delete_file(file_record.id)
    with pytest.raises(NotFoundError):
        file_management_service.get_file_by_id(file_record.id)
