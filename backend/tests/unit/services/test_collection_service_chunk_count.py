"""
Unit tests for chunk counting methods in CollectionService.

This module tests the _add_chunk_counts_to_collection and _get_batch_document_chunk_counts
methods to ensure accurate chunk counting from the vector store.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.schemas.collection_schema import CollectionOutput, CollectionStatus, FileInfo
from rag_solution.services.collection_service import CollectionService


@pytest.fixture
def db_session():
    """Fixture for a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def settings():
    """Fixture for a mock settings object."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.vector_db = "milvus"
    return mock_settings


@pytest.fixture
def collection_service(db_session, settings):
    """Fixture for a CollectionService instance with mocked dependencies."""
    with (
        patch("rag_solution.services.collection_service.CollectionRepository"),
        patch("rag_solution.services.collection_service.UserCollectionService"),
        patch("rag_solution.services.collection_service.FileManagementService"),
        patch("rag_solution.services.collection_service.VectorStoreFactory"),
        patch("rag_solution.services.collection_service.UserProviderService"),
        patch("rag_solution.services.collection_service.PromptTemplateService"),
        patch("rag_solution.services.collection_service.LLMParametersService"),
        patch("rag_solution.services.collection_service.QuestionService"),
        patch("rag_solution.services.collection_service.LLMModelService"),
    ):
        service = CollectionService(db=db_session, settings=settings)
        service.vector_store = MagicMock()
        return service


@pytest.fixture
def sample_collection_output():
    """Fixture for a sample CollectionOutput with files."""
    return CollectionOutput(
        id=uuid4(),
        name="Test Collection",
        vector_db_name="test_collection_123",
        is_private=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        user_ids=[uuid4()],
        files=[
            FileInfo(
                id=uuid4(),
                filename="document1.pdf",
                file_size_bytes=1024,
                chunk_count=0,
                document_id="doc_123",
            ),
            FileInfo(
                id=uuid4(),
                filename="document2.pdf",
                file_size_bytes=2048,
                chunk_count=0,
                document_id="doc_456",
            ),
        ],
        status=CollectionStatus.COMPLETED,
    )


@pytest.mark.unit
class TestAddChunkCountsToCollection:
    """Tests for the _add_chunk_counts_to_collection method."""

    def test_add_chunk_counts_with_valid_documents(self, collection_service, sample_collection_output):
        """Test that chunk counts are correctly added to files with valid document IDs."""
        # Mock _get_batch_document_chunk_counts to return specific counts
        with patch.object(collection_service, "_get_batch_document_chunk_counts") as mock_batch_count:
            mock_batch_count.return_value = {"doc_123": 5, "doc_456": 10}

            result = collection_service._add_chunk_counts_to_collection(sample_collection_output)

            # Verify _get_batch_document_chunk_counts was called correctly with all document IDs
            mock_batch_count.assert_called_once_with("test_collection_123", ["doc_123", "doc_456"])

            # Verify chunk counts are correctly added
            assert len(result.files) == 2
            assert result.files[0].chunk_count == 5
            assert result.files[1].chunk_count == 10

            # Verify other fields are preserved
            assert result.id == sample_collection_output.id
            assert result.name == sample_collection_output.name
            assert result.vector_db_name == sample_collection_output.vector_db_name
            assert result.is_private == sample_collection_output.is_private
            assert result.files[0].filename == "document1.pdf"
            assert result.files[1].filename == "document2.pdf"

    def test_add_chunk_counts_empty_collection(self, collection_service):
        """Test that empty collections are handled correctly without errors."""
        empty_collection = CollectionOutput(
            id=uuid4(),
            name="Empty Collection",
            vector_db_name="empty_collection_123",
            is_private=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_ids=[],
            files=[],
            status=CollectionStatus.COMPLETED,
        )

        with patch.object(collection_service, "_get_batch_document_chunk_counts") as mock_batch_count:
            result = collection_service._add_chunk_counts_to_collection(empty_collection)

            # Verify no chunk count queries were made (early return for empty files)
            mock_batch_count.assert_not_called()

            # Verify collection is returned unchanged
            assert result.id == empty_collection.id
            assert result.name == empty_collection.name
            assert len(result.files) == 0

    def test_add_chunk_counts_missing_document_ids(self, collection_service):
        """Test that files without document_ids get chunk_count of 0."""
        collection = CollectionOutput(
            id=uuid4(),
            name="Test Collection",
            vector_db_name="test_collection_123",
            is_private=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_ids=[uuid4()],
            files=[
                FileInfo(
                    id=uuid4(),
                    filename="document1.pdf",
                    file_size_bytes=1024,
                    chunk_count=0,
                    document_id=None,  # No document ID
                ),
                FileInfo(
                    id=uuid4(),
                    filename="document2.pdf",
                    file_size_bytes=2048,
                    chunk_count=0,
                    document_id="doc_456",  # Has document ID
                ),
            ],
            status=CollectionStatus.COMPLETED,
        )

        with patch.object(collection_service, "_get_batch_document_chunk_counts") as mock_batch_count:
            mock_batch_count.return_value = {"doc_456": 10}

            result = collection_service._add_chunk_counts_to_collection(collection)

            # Verify _get_batch_document_chunk_counts was only called with doc that has ID
            mock_batch_count.assert_called_once_with("test_collection_123", ["doc_456"])

            # Verify chunk counts
            assert result.files[0].chunk_count == 0  # No document_id, so 0 chunks
            assert result.files[1].chunk_count == 10  # Has document_id, got count from vector store

    def test_add_chunk_counts_all_files_missing_document_ids(self, collection_service):
        """Test that collections where all files have no document_ids are handled correctly."""
        collection = CollectionOutput(
            id=uuid4(),
            name="Test Collection",
            vector_db_name="test_collection_123",
            is_private=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_ids=[uuid4()],
            files=[
                FileInfo(
                    id=uuid4(),
                    filename="document1.pdf",
                    file_size_bytes=1024,
                    chunk_count=0,
                    document_id=None,
                ),
                FileInfo(
                    id=uuid4(),
                    filename="document2.pdf",
                    file_size_bytes=2048,
                    chunk_count=0,
                    document_id=None,
                ),
            ],
            status=CollectionStatus.COMPLETED,
        )

        with patch.object(collection_service, "_get_batch_document_chunk_counts") as mock_batch_count:
            result = collection_service._add_chunk_counts_to_collection(collection)

            # Verify no batch query was made (early return when no document_ids)
            mock_batch_count.assert_not_called()

            # Verify all files have chunk_count of 0
            assert result.files[0].chunk_count == 0
            assert result.files[1].chunk_count == 0

    def test_add_chunk_counts_batch_query_error(self, collection_service, sample_collection_output):
        """Test that errors during chunk counting are handled gracefully."""
        with patch.object(collection_service, "_get_batch_document_chunk_counts") as mock_batch_count:
            # Simulate an error in _get_batch_document_chunk_counts
            mock_batch_count.side_effect = Exception("Vector store connection failed")

            # The method should catch the exception and return original collection
            result = collection_service._add_chunk_counts_to_collection(sample_collection_output)

            # Verify original collection is returned (without chunk counts)
            assert result.id == sample_collection_output.id
            assert result.name == sample_collection_output.name
            assert result.files == sample_collection_output.files

    def test_add_chunk_counts_preserves_original_data(self, collection_service, sample_collection_output):
        """Test that all original collection data is preserved when adding chunk counts."""
        with patch.object(collection_service, "_get_batch_document_chunk_counts") as mock_batch_count:
            mock_batch_count.return_value = {"doc_123": 7, "doc_456": 7}

            result = collection_service._add_chunk_counts_to_collection(sample_collection_output)

            # Verify all original fields are preserved
            assert result.id == sample_collection_output.id
            assert result.name == sample_collection_output.name
            assert result.vector_db_name == sample_collection_output.vector_db_name
            assert result.is_private == sample_collection_output.is_private
            assert result.created_at == sample_collection_output.created_at
            assert result.updated_at == sample_collection_output.updated_at
            assert result.user_ids == sample_collection_output.user_ids
            assert result.status == sample_collection_output.status

            # Verify file-level data is preserved (except chunk_count which is updated)
            assert len(result.files) == len(sample_collection_output.files)
            for i, file_info in enumerate(result.files):
                original_file = sample_collection_output.files[i]
                assert file_info.id == original_file.id
                assert file_info.filename == original_file.filename
                assert file_info.file_size_bytes == original_file.file_size_bytes
                assert file_info.document_id == original_file.document_id

    def test_add_chunk_counts_partial_results(self, collection_service, sample_collection_output):
        """Test handling when batch query returns counts for only some documents."""
        with patch.object(collection_service, "_get_batch_document_chunk_counts") as mock_batch_count:
            # Return count for only first document
            mock_batch_count.return_value = {"doc_123": 5}

            result = collection_service._add_chunk_counts_to_collection(sample_collection_output)

            # Verify first file has count, second file has 0 (not found in results)
            assert result.files[0].chunk_count == 5
            assert result.files[1].chunk_count == 0


@pytest.mark.unit
class TestGetBatchDocumentChunkCounts:
    """Tests for the _get_batch_document_chunk_counts method."""

    def test_batch_count_success(self, collection_service):
        """Test that chunk counts are correctly retrieved for multiple documents using batch query."""
        # Mock pymilvus Collection.query to return chunk results
        mock_results = [
            {"document_id": "doc_123"},
            {"document_id": "doc_123"},
            {"document_id": "doc_123"},
            {"document_id": "doc_456"},
            {"document_id": "doc_456"},
        ]

        # Patch at the import location within the method
        with patch("pymilvus.Collection") as mock_collection_class:
            mock_collection = MagicMock()
            mock_collection.query.return_value = mock_results
            mock_collection_class.return_value = mock_collection

            counts = collection_service._get_batch_document_chunk_counts("test_collection", ["doc_123", "doc_456"])

            # Verify Milvus Collection was instantiated
            mock_collection_class.assert_called_once_with("test_collection")

            # Verify batch query was called with IN expression
            mock_collection.query.assert_called_once()
            call_args = mock_collection.query.call_args
            assert 'document_id in ["doc_123", "doc_456"]' == call_args[1]["expr"]
            assert call_args[1]["output_fields"] == ["document_id"]
            assert call_args[1]["limit"] == 100000

            # Verify correct counts are returned (3 for doc_123, 2 for doc_456)
            assert counts == {"doc_123": 3, "doc_456": 2}

    def test_batch_count_empty_document_ids(self, collection_service):
        """Test that empty document_ids list returns empty dict."""
        counts = collection_service._get_batch_document_chunk_counts("test_collection", [])

        # Verify empty dict is returned (early return)
        assert counts == {}

    def test_batch_count_single_document_error(self, collection_service):
        """Test that batch query errors return 0 counts for all documents."""
        with patch("pymilvus.Collection") as mock_collection_class:
            # Simulate batch query failure
            mock_collection_class.side_effect = Exception("Connection error")

            counts = collection_service._get_batch_document_chunk_counts("test_collection", ["doc_123", "doc_456"])

            # Verify all documents have 0 count due to batch query error
            assert counts == {"doc_123": 0, "doc_456": 0}

    def test_batch_count_all_documents_error(self, collection_service):
        """Test that errors for all documents are handled gracefully."""
        with patch("pymilvus.Collection") as mock_collection_class:
            # Simulate batch query failure
            mock_collection_class.side_effect = Exception("Connection error")

            counts = collection_service._get_batch_document_chunk_counts("test_collection", ["doc_123", "doc_456"])

            # Verify all documents have 0 count due to batch query error
            assert counts == {"doc_123": 0, "doc_456": 0}

    def test_batch_count_method_exception(self, collection_service):
        """Test that top-level exceptions return 0 counts for all documents."""
        # Simulate exception outside the loop (e.g., in the try block)
        with patch.object(collection_service, "_get_batch_document_chunk_counts") as mock_method:
            # Make the method raise an exception
            def side_effect(collection_name, document_ids):
                if not document_ids:
                    return {}
                # Simulate error
                return dict.fromkeys(document_ids, 0)

            mock_method.side_effect = side_effect

            counts = mock_method("test_collection", ["doc_123", "doc_456"])

            # Verify all documents have 0 count
            assert counts == {"doc_123": 0, "doc_456": 0}

    def test_batch_count_large_document_list(self, collection_service):
        """Test handling of large number of documents in a single batch query."""
        # Create 100 documents with varying chunk counts
        doc_ids = [f"doc_{i}" for i in range(100)]

        # Create mock results - each doc has chunks equal to its index
        mock_results = []
        for i, doc_id in enumerate(doc_ids):
            for _ in range(i):  # doc_0 has 0 chunks, doc_1 has 1 chunk, etc.
                mock_results.append({"document_id": doc_id})

        with patch("pymilvus.Collection") as mock_collection_class:
            mock_collection = MagicMock()
            mock_collection.query.return_value = mock_results
            mock_collection_class.return_value = mock_collection

            counts = collection_service._get_batch_document_chunk_counts("test_collection", doc_ids)

            # Verify batch query was called once with all document IDs
            mock_collection.query.assert_called_once()

            # Verify documents with chunks have correct counts (doc_0 won't be in dict since it has 0 chunks)
            assert len(counts) == 99  # doc_0 has 0 chunks, so it's not in the result
            for i in range(1, 100):  # Start from 1 since doc_0 has no chunks
                doc_id = f"doc_{i}"
                assert counts[doc_id] == i

    def test_batch_count_special_characters_in_doc_id(self, collection_service):
        """Test handling of document IDs with special characters using batch query."""
        # Test with various special characters
        doc_ids = [
            'doc_with"quotes',
            "doc-with-dashes",
            "doc.with.dots",
            "doc_with_underscores",
        ]

        # Create mock results - 5 chunks for each document
        mock_results = []
        for doc_id in doc_ids:
            for _ in range(5):
                mock_results.append({"document_id": doc_id})

        with patch("pymilvus.Collection") as mock_collection_class:
            mock_collection = MagicMock()
            mock_collection.query.return_value = mock_results
            mock_collection_class.return_value = mock_collection

            counts = collection_service._get_batch_document_chunk_counts("test_collection", doc_ids)

            # Verify batch query was called once
            mock_collection.query.assert_called_once()

            # Verify all documents were counted
            assert len(counts) == 4
            for doc_id in doc_ids:
                assert counts[doc_id] == 5

    def test_batch_count_json_escaping_sql_injection_prevention(self, collection_service):
        """Test that JSON escaping prevents SQL injection attacks."""
        import json

        # Malicious document IDs attempting SQL injection
        doc_ids = ["doc-1'; DROP TABLE collections; --", 'doc-2" OR 1=1; --', 'doc-3"; DELETE FROM files; --']

        mock_results = []
        for doc_id in doc_ids:
            mock_results.append({"document_id": doc_id})

        with patch("pymilvus.Collection") as mock_collection_class:
            mock_collection = MagicMock()
            mock_collection.query.return_value = mock_results
            mock_collection_class.return_value = mock_collection

            counts = collection_service._get_batch_document_chunk_counts("test_collection", doc_ids)

            # Verify batch query was called
            mock_collection.query.assert_called_once()
            call_args = mock_collection.query.call_args

            # Verify the expression uses json.dumps for proper escaping
            expr = call_args[1]["expr"]
            expected_expr = f"document_id in {json.dumps(doc_ids)}"
            assert expr == expected_expr

            # Verify malicious strings are properly escaped in JSON
            assert "DROP TABLE" in expr  # String should be present but escaped
            assert json.dumps(doc_ids) in expr  # Should contain properly escaped JSON array

            # Verify counts are returned correctly
            assert len(counts) == 3
            for doc_id in doc_ids:
                assert counts[doc_id] == 1

    def test_batch_count_handles_missing_document_id_field(self, collection_service):
        """Test handling when query results have missing document_id field."""
        doc_ids = ["doc_123", "doc_456"]

        # Simulate results with some missing document_id field
        mock_results = [
            {"document_id": "doc_123"},
            {"document_id": "doc_123"},
            {},  # Missing document_id field
            {"document_id": "doc_456"},
            {"other_field": "value"},  # Missing document_id field
        ]

        with patch("pymilvus.Collection") as mock_collection_class:
            mock_collection = MagicMock()
            mock_collection.query.return_value = mock_results
            mock_collection_class.return_value = mock_collection

            counts = collection_service._get_batch_document_chunk_counts("test_collection", doc_ids)

            # Verify only valid results are counted
            assert counts == {"doc_123": 2, "doc_456": 1}

    def test_batch_count_handles_empty_document_id(self, collection_service):
        """Test handling when query results have empty or None document_id."""
        doc_ids = ["doc_123", "doc_456"]

        # Simulate results with empty document_id values
        mock_results = [
            {"document_id": "doc_123"},
            {"document_id": ""},  # Empty string
            {"document_id": "doc_456"},
            {"document_id": None},  # None value
            {"document_id": "doc_123"},
        ]

        with patch("pymilvus.Collection") as mock_collection_class:
            mock_collection = MagicMock()
            mock_collection.query.return_value = mock_results
            mock_collection_class.return_value = mock_collection

            counts = collection_service._get_batch_document_chunk_counts("test_collection", doc_ids)

            # Verify only valid, non-empty document_ids are counted
            assert counts == {"doc_123": 2, "doc_456": 1}

    def test_batch_count_pymilvus_import_error(self, collection_service):
        """Test handling when pymilvus is not available (ImportError)."""
        doc_ids = ["doc_123", "doc_456", "doc_789"]

        # Simulate ImportError when trying to import Collection
        with patch("pymilvus.Collection", side_effect=ImportError("No module named 'pymilvus'")):
            counts = collection_service._get_batch_document_chunk_counts("test_collection", doc_ids)

            # Verify all documents get 0 count when pymilvus is unavailable
            assert counts == {"doc_123": 0, "doc_456": 0, "doc_789": 0}


@pytest.mark.unit
class TestChunkCountIntegration:
    """Integration tests for chunk counting workflow."""

    def test_get_collection_includes_chunk_counts(self, collection_service):
        """Test that get_collection enriches collection with chunk counts using batch query."""
        collection_id = uuid4()

        # Mock the repository to return a collection
        mock_collection = CollectionOutput(
            id=collection_id,
            name="Test Collection",
            vector_db_name="test_collection_123",
            is_private=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_ids=[uuid4()],
            files=[
                FileInfo(
                    id=uuid4(),
                    filename="test.pdf",
                    file_size_bytes=1024,
                    chunk_count=0,
                    document_id="doc_123",
                )
            ],
            status=CollectionStatus.COMPLETED,
        )

        collection_service.collection_repository.get.return_value = mock_collection

        # Mock pymilvus Collection.query to return 15 chunks for doc_123
        mock_results = [{"document_id": "doc_123"} for _ in range(15)]

        with patch("pymilvus.Collection") as mock_collection_class:
            mock_milvus_collection = MagicMock()
            mock_milvus_collection.query.return_value = mock_results
            mock_collection_class.return_value = mock_milvus_collection

            result = collection_service.get_collection(collection_id)

            # Verify chunk count was added
            assert result.files[0].chunk_count == 15

            # Verify batch query was called
            mock_collection_class.assert_called_once_with("test_collection_123")
            mock_milvus_collection.query.assert_called_once()

    def test_get_collection_handles_batch_query_failure(self, collection_service):
        """Test that get_collection handles batch query failures gracefully."""
        collection_id = uuid4()

        # Mock the repository to return a collection
        mock_collection = CollectionOutput(
            id=collection_id,
            name="Test Collection",
            vector_db_name="test_collection_123",
            is_private=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_ids=[uuid4()],
            files=[
                FileInfo(
                    id=uuid4(),
                    filename="test.pdf",
                    file_size_bytes=1024,
                    chunk_count=0,
                    document_id="doc_123",
                )
            ],
            status=CollectionStatus.COMPLETED,
        )

        collection_service.collection_repository.get.return_value = mock_collection

        with patch.object(collection_service, "_get_batch_document_chunk_counts") as mock_batch_count:
            # Simulate batch query failure
            mock_batch_count.side_effect = Exception("Batch query failed")

            result = collection_service.get_collection(collection_id)

            # Verify original collection is returned (without enriched chunk counts)
            assert result.id == collection_id
            assert result.files[0].chunk_count == 0  # Original value preserved
