"""Unit tests for MCP resources module.

Tests for all RAG resources exposed via MCP.
"""

import json
import sys
from datetime import datetime
from enum import Enum
from unittest.mock import MagicMock, patch
from uuid import UUID

from backend.mcp_server.resources import register_rag_resources


class FileStatus(str, Enum):
    """Mock file status enum."""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class CollectionStatus(str, Enum):
    """Mock collection status enum."""

    ACTIVE = "active"
    PENDING = "pending"


class TestRegisterRagResources:
    """Tests for register_rag_resources function."""

    def test_register_resources(self) -> None:
        """Test that resources are registered with MCP server."""
        mock_mcp = MagicMock()

        register_rag_resources(mock_mcp)

        # Verify resource decorator was called 3 times
        assert mock_mcp.resource.call_count == 3


class TestGetCollectionDocumentsResource:
    """Tests for get_collection_documents resource."""

    def test_get_documents_success(self) -> None:
        """Test successful document listing."""
        mock_file = MagicMock()
        mock_file.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_file.filename = "test.pdf"
        mock_file.file_type = "pdf"
        mock_file.file_size = 1024
        mock_file.created_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_file.updated_at = datetime(2024, 1, 2, 12, 0, 0)
        mock_file.status = FileStatus.PROCESSED

        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource

        # Register resources first (no mocking needed during registration)
        register_rag_resources(mock_mcp)

        # Mock for when the function is called (local imports happen here)
        mock_db = MagicMock()
        mock_file_service = MagicMock()
        mock_file_service.get_files_by_collection.return_value = [mock_file]

        # Create mock modules for local imports
        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db])

        mock_file_service_module = MagicMock()
        mock_file_service_module.FileManagementService.return_value = mock_file_service

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database_module,
                "backend.rag_solution.services.file_management_service": mock_file_service_module,
            },
        ):
            result = resource_functions["rag://collection/{collection_id}/documents"](
                collection_id="12345678-1234-5678-1234-567812345678"
            )

        data = json.loads(result)
        assert data["total"] == 1
        assert data["documents"][0]["filename"] == "test.pdf"
        assert data["documents"][0]["status"] == "processed"
        mock_db.close.assert_called_once()

    def test_get_documents_invalid_collection_id(self) -> None:
        """Test document listing with invalid collection ID."""
        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        result = resource_functions["rag://collection/{collection_id}/documents"](collection_id="not-a-uuid")

        data = json.loads(result)
        assert "error" in data
        assert "Invalid collection_id" in data["error"]

    def test_get_documents_empty_collection(self) -> None:
        """Test document listing for empty collection."""
        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        mock_db = MagicMock()
        mock_file_service = MagicMock()
        mock_file_service.get_files_by_collection.return_value = []

        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db])

        mock_file_service_module = MagicMock()
        mock_file_service_module.FileManagementService.return_value = mock_file_service

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database_module,
                "backend.rag_solution.services.file_management_service": mock_file_service_module,
            },
        ):
            result = resource_functions["rag://collection/{collection_id}/documents"](
                collection_id="12345678-1234-5678-1234-567812345678"
            )

        data = json.loads(result)
        assert data["total"] == 0
        assert data["documents"] == []

    def test_get_documents_service_error(self) -> None:
        """Test document listing with service error."""
        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        mock_db = MagicMock()
        mock_file_service = MagicMock()
        mock_file_service.get_files_by_collection.side_effect = Exception("DB error")

        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db])

        mock_file_service_module = MagicMock()
        mock_file_service_module.FileManagementService.return_value = mock_file_service

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database_module,
                "backend.rag_solution.services.file_management_service": mock_file_service_module,
            },
        ):
            result = resource_functions["rag://collection/{collection_id}/documents"](
                collection_id="12345678-1234-5678-1234-567812345678"
            )

        data = json.loads(result)
        assert "error" in data

    def test_get_documents_null_dates(self) -> None:
        """Test document listing with null dates."""
        mock_file = MagicMock()
        mock_file.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_file.filename = "test.pdf"
        mock_file.file_type = "pdf"
        mock_file.file_size = 1024
        mock_file.created_at = None
        mock_file.updated_at = None
        mock_file.status = FileStatus.PENDING

        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        mock_db = MagicMock()
        mock_file_service = MagicMock()
        mock_file_service.get_files_by_collection.return_value = [mock_file]

        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db])

        mock_file_service_module = MagicMock()
        mock_file_service_module.FileManagementService.return_value = mock_file_service

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database_module,
                "backend.rag_solution.services.file_management_service": mock_file_service_module,
            },
        ):
            result = resource_functions["rag://collection/{collection_id}/documents"](
                collection_id="12345678-1234-5678-1234-567812345678"
            )

        data = json.loads(result)
        assert data["documents"][0]["created_at"] is None
        assert data["documents"][0]["updated_at"] is None


class TestGetCollectionStatsResource:
    """Tests for get_collection_stats resource."""

    def test_get_stats_success(self) -> None:
        """Test successful stats retrieval."""
        mock_collection = MagicMock()
        mock_collection.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_collection.name = "Test Collection"
        mock_collection.description = "Test description"
        mock_collection.status = CollectionStatus.ACTIVE
        mock_collection.created_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_collection.updated_at = datetime(2024, 1, 2, 12, 0, 0)
        mock_collection.total_chunks = 100
        mock_collection.total_documents = 10

        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        mock_db = MagicMock()
        mock_coll_service = MagicMock()
        mock_coll_service.get_collection.return_value = mock_collection
        mock_settings = MagicMock()

        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db])

        mock_collection_service_module = MagicMock()
        mock_collection_service_module.CollectionService.return_value = mock_coll_service

        mock_config_module = MagicMock()
        mock_config_module.get_settings.return_value = mock_settings

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database_module,
                "backend.rag_solution.services.collection_service": mock_collection_service_module,
                "backend.core.config": mock_config_module,
            },
        ):
            result = resource_functions["rag://collection/{collection_id}/stats"](
                collection_id="12345678-1234-5678-1234-567812345678"
            )

        data = json.loads(result)
        assert data["name"] == "Test Collection"
        assert data["status"] == "active"
        assert data["total_chunks"] == 100
        assert data["total_documents"] == 10

    def test_get_stats_collection_not_found(self) -> None:
        """Test stats retrieval for non-existent collection."""
        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        mock_db = MagicMock()
        mock_coll_service = MagicMock()
        mock_coll_service.get_collection.return_value = None
        mock_settings = MagicMock()

        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db])

        mock_collection_service_module = MagicMock()
        mock_collection_service_module.CollectionService.return_value = mock_coll_service

        mock_config_module = MagicMock()
        mock_config_module.get_settings.return_value = mock_settings

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database_module,
                "backend.rag_solution.services.collection_service": mock_collection_service_module,
                "backend.core.config": mock_config_module,
            },
        ):
            result = resource_functions["rag://collection/{collection_id}/stats"](
                collection_id="12345678-1234-5678-1234-567812345678"
            )

        data = json.loads(result)
        assert "error" in data
        assert "not found" in data["error"]

    def test_get_stats_invalid_collection_id(self) -> None:
        """Test stats retrieval with invalid collection ID."""
        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        result = resource_functions["rag://collection/{collection_id}/stats"](collection_id="not-a-uuid")

        data = json.loads(result)
        assert "error" in data

    def test_get_stats_without_chunk_attributes(self) -> None:
        """Test stats retrieval when collection has no chunk attributes."""
        mock_collection = MagicMock(spec=["id", "name", "description", "status", "created_at", "updated_at"])
        mock_collection.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_collection.name = "Test Collection"
        mock_collection.description = "Test"
        mock_collection.status = CollectionStatus.ACTIVE
        mock_collection.created_at = None
        mock_collection.updated_at = None

        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        mock_db = MagicMock()
        mock_coll_service = MagicMock()
        mock_coll_service.get_collection.return_value = mock_collection
        mock_settings = MagicMock()

        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db])

        mock_collection_service_module = MagicMock()
        mock_collection_service_module.CollectionService.return_value = mock_coll_service

        mock_config_module = MagicMock()
        mock_config_module.get_settings.return_value = mock_settings

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database_module,
                "backend.rag_solution.services.collection_service": mock_collection_service_module,
                "backend.core.config": mock_config_module,
            },
        ):
            result = resource_functions["rag://collection/{collection_id}/stats"](
                collection_id="12345678-1234-5678-1234-567812345678"
            )

        data = json.loads(result)
        # Should not have chunk-related fields
        assert "total_chunks" not in data
        assert "total_documents" not in data


class TestGetUserCollectionsResource:
    """Tests for get_user_collections resource."""

    def test_get_user_collections_success(self) -> None:
        """Test successful user collections retrieval."""
        mock_collection = MagicMock()
        mock_collection.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_collection.name = "User Collection"
        mock_collection.description = "Test description"
        mock_collection.status = CollectionStatus.ACTIVE
        mock_collection.created_at = datetime(2024, 1, 1, 12, 0, 0)

        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        mock_db = MagicMock()
        mock_coll_service = MagicMock()
        mock_coll_service.get_user_collections.return_value = [mock_collection]
        mock_settings = MagicMock()

        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db])

        mock_collection_service_module = MagicMock()
        mock_collection_service_module.CollectionService.return_value = mock_coll_service

        mock_config_module = MagicMock()
        mock_config_module.get_settings.return_value = mock_settings

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database_module,
                "backend.rag_solution.services.collection_service": mock_collection_service_module,
                "backend.core.config": mock_config_module,
            },
        ):
            result = resource_functions["rag://user/{user_id}/collections"](
                user_id="12345678-1234-5678-1234-567812345679"
            )

        data = json.loads(result)
        assert data["total"] == 1
        assert data["collections"][0]["name"] == "User Collection"
        assert data["user_id"] == "12345678-1234-5678-1234-567812345679"

    def test_get_user_collections_empty(self) -> None:
        """Test user collections retrieval with no collections."""
        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        mock_db = MagicMock()
        mock_coll_service = MagicMock()
        mock_coll_service.get_user_collections.return_value = []
        mock_settings = MagicMock()

        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db])

        mock_collection_service_module = MagicMock()
        mock_collection_service_module.CollectionService.return_value = mock_coll_service

        mock_config_module = MagicMock()
        mock_config_module.get_settings.return_value = mock_settings

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database_module,
                "backend.rag_solution.services.collection_service": mock_collection_service_module,
                "backend.core.config": mock_config_module,
            },
        ):
            result = resource_functions["rag://user/{user_id}/collections"](
                user_id="12345678-1234-5678-1234-567812345679"
            )

        data = json.loads(result)
        assert data["total"] == 0
        assert data["collections"] == []

    def test_get_user_collections_invalid_user_id(self) -> None:
        """Test user collections retrieval with invalid user ID."""
        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        result = resource_functions["rag://user/{user_id}/collections"](user_id="not-a-uuid")

        data = json.loads(result)
        assert "error" in data
        assert "Invalid user_id" in data["error"]

    def test_get_user_collections_service_error(self) -> None:
        """Test user collections retrieval with service error."""
        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        mock_db = MagicMock()
        mock_coll_service = MagicMock()
        mock_coll_service.get_user_collections.side_effect = Exception("Service error")
        mock_settings = MagicMock()

        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db])

        mock_collection_service_module = MagicMock()
        mock_collection_service_module.CollectionService.return_value = mock_coll_service

        mock_config_module = MagicMock()
        mock_config_module.get_settings.return_value = mock_settings

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database_module,
                "backend.rag_solution.services.collection_service": mock_collection_service_module,
                "backend.core.config": mock_config_module,
            },
        ):
            result = resource_functions["rag://user/{user_id}/collections"](
                user_id="12345678-1234-5678-1234-567812345679"
            )

        data = json.loads(result)
        assert "error" in data

    def test_get_user_collections_null_created_at(self) -> None:
        """Test user collections with null created_at."""
        mock_collection = MagicMock()
        mock_collection.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_collection.name = "Test"
        mock_collection.description = "Test"
        mock_collection.status = CollectionStatus.PENDING
        mock_collection.created_at = None

        mock_mcp = MagicMock()
        resource_functions = {}

        def capture_resource(uri):
            def decorator(func):
                resource_functions[uri] = func
                return func

            return decorator

        mock_mcp.resource = capture_resource
        register_rag_resources(mock_mcp)

        mock_db = MagicMock()
        mock_coll_service = MagicMock()
        mock_coll_service.get_user_collections.return_value = [mock_collection]
        mock_settings = MagicMock()

        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db])

        mock_collection_service_module = MagicMock()
        mock_collection_service_module.CollectionService.return_value = mock_coll_service

        mock_config_module = MagicMock()
        mock_config_module.get_settings.return_value = mock_settings

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database_module,
                "backend.rag_solution.services.collection_service": mock_collection_service_module,
                "backend.core.config": mock_config_module,
            },
        ):
            result = resource_functions["rag://user/{user_id}/collections"](
                user_id="12345678-1234-5678-1234-567812345679"
            )

        data = json.loads(result)
        assert data["collections"][0]["created_at"] is None


class TestResourceURIPatterns:
    """Tests for resource URI patterns."""

    def test_collection_documents_uri_pattern(self) -> None:
        """Test collection documents URI pattern."""
        mock_mcp = MagicMock()
        register_rag_resources(mock_mcp)

        calls = mock_mcp.resource.call_args_list
        patterns = [call[0][0] for call in calls]

        assert "rag://collection/{collection_id}/documents" in patterns

    def test_collection_stats_uri_pattern(self) -> None:
        """Test collection stats URI pattern."""
        mock_mcp = MagicMock()
        register_rag_resources(mock_mcp)

        calls = mock_mcp.resource.call_args_list
        patterns = [call[0][0] for call in calls]

        assert "rag://collection/{collection_id}/stats" in patterns

    def test_user_collections_uri_pattern(self) -> None:
        """Test user collections URI pattern."""
        mock_mcp = MagicMock()
        register_rag_resources(mock_mcp)

        calls = mock_mcp.resource.call_args_list
        patterns = [call[0][0] for call in calls]

        assert "rag://user/{user_id}/collections" in patterns
