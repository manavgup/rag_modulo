"""File management fixtures for pytest."""

from uuid import uuid4
import pytest
from rag_solution.schemas.file_schema import FileInput
from rag_solution.schemas.user_schema import UserOutput

@pytest.fixture
def base_file(file_service, base_collection, base_user: UserOutput):
    """Create a base file using service."""
    file_input = FileInput(
        collection_id=base_collection.id,
        filename="test.txt",
        file_path="/tmp/test.txt",
        file_type="text/plain",
        metadata=None,
        document_id=str(uuid4())
    )
    return file_service.create_file(file_input, base_user.id)

@pytest.fixture
def base_file_with_content(file_service, base_collection, base_user: UserOutput, sample_content: str):
    """Create a base file with content using service."""
    file_input = FileInput(
        collection_id=base_collection.id,
        filename="test.txt",
        file_path="/tmp/test.txt",
        file_type="text/plain",
        metadata={
            "total_pages": 1,
            "total_chunks": 1,
            "keywords": {"test": True}
        },
        document_id=str(uuid4())
    )
    return file_service.create_file(file_input, base_user.id)