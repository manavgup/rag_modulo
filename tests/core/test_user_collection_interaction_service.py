"""Integration tests for UserCollectionInteractionService."""

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from rag_solution.services.user_collection_interaction_service import UserCollectionInteractionService
from rag_solution.schemas.user_collection_schema import UserCollectionsOutput, UserCollectionDetailOutput
from rag_solution.schemas.collection_schema import FileInfo
from rag_solution.models.user import User
from rag_solution.models.collection import Collection
from rag_solution.models.file import File
from rag_solution.models.user_collection import UserCollection

@pytest.fixture
def test_files(db_session: Session, test_collection: Collection) -> list[File]:
    """Create test files."""
    files = [
        File(
            collection_id=test_collection.id,
            filename=f"file{i}.txt",
            file_path=f"/path/to/file{i}.txt",
            file_type="txt",
            document_id=f"doc{i}",
            metadata={
                "total_pages": 1,
                "total_chunks": 1,
                "keywords": {"test": True}
            }
        )
        for i in range(3)
    ]
    db_session.add_all(files)
    db_session.commit()
    for file in files:
        db_session.refresh(file)
    return files

@pytest.fixture
def test_collection_with_files(
    db_session: Session,
    base_user: User
) -> Collection:
    """Create a test collection with files."""
    collection = Collection(
        name="Test Collection with Files",
        is_private=False,
        vector_db_name=f"collection_{uuid4().hex}",
        status="created"
    )
    db_session.add(collection)
    db_session.flush()
    
    # Add files to collection
    files = [
        File(
            collection_id=collection.id,
            filename=f"file{i}.txt",
            file_path=f"/path/to/file{i}.txt",
            file_type="txt",
            document_id=f"doc{i}",
            metadata={
                "total_pages": 1,
                "total_chunks": 1,
                "keywords": {"test": True}
            }
        )
        for i in range(3)
    ]
    db_session.add_all(files)
    
    # Add user to collection
    user_collection = UserCollection(
        user_id=base_user.id,
        collection_id=collection.id
    )
    db_session.add(user_collection)
    
    db_session.commit()
    db_session.refresh(collection)
    return collection

@pytest.mark.atomic
def test_get_user_collections_with_files(
    db_session: Session,
    base_user: User,
    test_collection_with_files: Collection
):
    """Test fetching user collections with files."""
    service = UserCollectionInteractionService(db_session)
    
    result = service.get_user_collections_with_files(base_user.id)
    
    assert isinstance(result, UserCollectionsOutput)
    assert result.user_id == base_user.id
    assert len(result.collections) > 0
    
    collection = next(c for c in result.collections if c.collection_id == test_collection_with_files.id)
    assert isinstance(collection, UserCollectionDetailOutput)
    assert collection.name == test_collection_with_files.name
    assert collection.is_private == test_collection_with_files.is_private
    assert len(collection.files) == 3
    for file in collection.files:
        assert isinstance(file, FileInfo)
        assert file.filename.startswith("file")
        assert file.file_type == "txt"

@pytest.mark.atomic
def test_get_user_collections_with_files_no_collections(
    db_session: Session,
    base_user: User
):
    """Test fetching user collections when user has no collections."""
    service = UserCollectionInteractionService(db_session)
    
    result = service.get_user_collections_with_files(base_user.id)
    
    assert isinstance(result, UserCollectionsOutput)
    assert result.user_id == base_user.id
    assert len(result.collections) == 0

@pytest.mark.atomic
def test_get_user_collections_with_files_multiple_collections(
    db_session: Session,
    base_user: User
):
    """Test fetching multiple collections with files."""
    # Create multiple collections with files
    collections = []
    for i in range(3):
        collection = Collection(
            name=f"Test Collection {i}",
            is_private=False,
            vector_db_name=f"collection_{uuid4().hex}",
            status="created"
        )
        db_session.add(collection)
        db_session.flush()
        
        # Add files to collection
        files = [
            File(
                collection_id=collection.id,
                filename=f"collection{i}_file{j}.txt",
                file_path=f"/path/to/collection{i}/file{j}.txt",
                file_type="txt",
                document_id=f"doc{i}{j}",
                metadata={"test": True}
            )
            for j in range(2)  # 2 files per collection
        ]
        db_session.add_all(files)
        
        # Add user to collection
        user_collection = UserCollection(
            user_id=base_user.id,
            collection_id=collection.id
        )
        db_session.add(user_collection)
        collections.append(collection)
    
    db_session.commit()
    
    service = UserCollectionInteractionService(db_session)
    result = service.get_user_collections_with_files(base_user.id)
    
    assert isinstance(result, UserCollectionsOutput)
    assert result.user_id == base_user.id
    assert len(result.collections) == 3
    
    for i, collection in enumerate(result.collections):
        assert collection.name == f"Test Collection {i}"
        assert len(collection.files) == 2
        for file in collection.files:
            assert file.filename.startswith(f"collection{i}_file")

@pytest.mark.atomic
def test_get_user_collections_with_files_nonexistent_user(db_session: Session):
    """Test fetching collections for nonexistent user."""
    service = UserCollectionInteractionService(db_session)
    
    result = service.get_user_collections_with_files(uuid4())
    
    assert isinstance(result, UserCollectionsOutput)
    assert len(result.collections) == 0

@pytest.mark.atomic
def test_get_user_collections_with_files_empty_collections(
    db_session: Session,
    base_user: User
):
    """Test fetching collections that have no files."""
    # Create collection without files
    collection = Collection(
        name="Empty Collection",
        is_private=False,
        vector_db_name=f"collection_{uuid4().hex}",
        status="created"
    )
    db_session.add(collection)
    db_session.flush()
    
    # Add user to collection
    user_collection = UserCollection(
        user_id=base_user.id,
        collection_id=collection.id
    )
    db_session.add(user_collection)
    db_session.commit()
    
    service = UserCollectionInteractionService(db_session)
    result = service.get_user_collections_with_files(base_user.id)
    
    assert isinstance(result, UserCollectionsOutput)
    assert len(result.collections) == 1
    assert len(result.collections[0].files) == 0

if __name__ == "__main__":
    pytest.main([__file__])
