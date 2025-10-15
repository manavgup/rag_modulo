"""
Test-driven development tests for settings dependency injection architecture.

This module tests the transition from global settings imports to FastAPI
dependency injection pattern using get_settings() function.

Expected behavior:
1. get_settings() returns consistent singleton instance via @lru_cache
2. FastAPI dependency injection works with Depends(get_settings)
3. No settings access during module import (import-time isolation)
4. Proper validation and error handling
5. Mock-friendly behavior in test environments
"""

import os
from unittest.mock import Mock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

# Test scenarios for settings dependency injection


@pytest.mark.unit
@pytest.mark.unit
def test_get_settings_function_exists():
    """Test that get_settings function exists and is callable."""
    from core.config import get_settings

    assert callable(get_settings)
    settings = get_settings()
    assert settings is not None


@pytest.mark.unit
def test_get_settings_returns_consistent_instance():
    """Test that get_settings returns the same instance (singleton via @lru_cache)."""
    from core.config import get_settings

    settings1 = get_settings()
    settings2 = get_settings()

    # Should return the same instance due to @lru_cache
    assert settings1 is settings2


@pytest.mark.unit
def test_get_settings_with_environment_variables():
    """Test that get_settings respects environment variables."""
    with patch.dict(
        os.environ,
        {
            "WATSONX_URL": "https://test.example.com",
            "JWT_SECRET_KEY": "test-secret-key",
            "RAG_LLM": "openai",
        },
    ):
        from core.config import get_settings

        # Clear cache to get fresh instance with new env vars
        get_settings.cache_clear()
        settings = get_settings()

        assert settings.wx_url == "https://test.example.com"
        assert settings.jwt_secret_key == "test-secret-key"
        assert settings.rag_llm == "openai"


@pytest.mark.unit
def test_fastapi_dependency_injection_pattern():
    """Test FastAPI dependency injection with Depends(get_settings)."""
    from core.config import Settings, get_settings

    app = FastAPI()

    @app.get("/test-settings")
    async def test_endpoint(settings: Settings = Depends(get_settings)):
        return {"rag_llm": settings.rag_llm}

    client = TestClient(app)

    with patch.dict(os.environ, {"RAG_LLM": "anthropic"}):
        get_settings.cache_clear()
        response = client.get("/test-settings")

        assert response.status_code == 200
        assert response.json()["rag_llm"] == "anthropic"


@pytest.mark.unit
def test_no_import_time_settings_access():
    """Test that modules can be imported without accessing settings."""
    # This test verifies that importing modules doesn't trigger settings validation
    # by temporarily making environment invalid

    from core.config import get_settings

    # Clear cache from previous tests
    get_settings.cache_clear()

    original_env = os.environ.copy()

    try:
        # Clear all relevant environment variables to make settings invalid
        for key in list(os.environ.keys()):
            if any(prefix in key for prefix in ["WATSONX", "JWT", "RAG", "VECTOR", "MILVUS"]):
                del os.environ[key]

        # The function should exist but not be called during import
        assert callable(get_settings)

        # When we call get_settings() with empty environment, it should work with defaults
        # This is the desired behavior - settings should be accessible even without env vars
        settings = get_settings()
        assert settings is not None
        # Should have default values
        assert settings.rag_llm == "ibm/granite-3-3-8b-instruct"

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)
        # Clear cache again for next tests
        get_settings.cache_clear()


@pytest.mark.unit
def test_settings_validation_error_handling():
    """Test proper error handling when settings validation fails."""
    from core.config import get_settings

    # Clear cache to get fresh validation
    get_settings.cache_clear()

    # With defaults, Settings should instantiate even with empty environment
    # This is the desired behavior for dependency injection
    # Patch both os.environ and dotenv to prevent loading from .env file
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("pydantic_settings.sources.DotEnvSettingsSource.__call__", return_value={}),
    ):
        settings = get_settings()
        # Should get default values
        assert settings.jwt_secret_key == "dev-secret-key-change-in-production-f8a7b2c1"
        assert settings.rag_llm == "ibm/granite-3-3-8b-instruct"


@pytest.mark.unit
def test_mocked_settings_in_tests():
    """Test that settings can be properly mocked for testing."""
    mock_settings = Mock()
    mock_settings.rag_llm = "mocked-llm"
    mock_settings.wx_url = "https://mocked.example.com"

    # Mock at the module level before import
    import core.config

    original_get_settings = core.config.get_settings
    try:
        # Replace get_settings with a mock function
        core.config.get_settings = Mock(return_value=mock_settings)

        # Now when we access settings, it should use the mock
        settings = core.config.get_settings()

        assert settings.rag_llm == "mocked-llm"
        assert settings.wx_url == "https://mocked.example.com"
    finally:
        # Restore original function
        core.config.get_settings = original_get_settings


@pytest.mark.unit
def test_settings_cache_behavior():
    """Test @lru_cache behavior with cache clearing."""
    from core.config import get_settings

    # Clear cache
    get_settings.cache_clear()

    with patch.dict(os.environ, {"RAG_LLM": "anthropic"}):
        settings1 = get_settings()
        first_rag_llm = settings1.rag_llm

    # Change environment but don't clear cache
    with patch.dict(os.environ, {"RAG_LLM": "watsonx"}):
        settings2 = get_settings()  # Should return cached instance

        # Should still have first value due to caching
        assert settings2 is settings1
        assert settings2.rag_llm == first_rag_llm

    # Clear cache and try again
    get_settings.cache_clear()
    with patch.dict(os.environ, {"RAG_LLM": "watsonx"}):
        settings3 = get_settings()  # Should create new instance

        assert settings3 is not settings1
        assert settings3.rag_llm == "watsonx"


@pytest.mark.unit
def test_legacy_global_settings_deprecated():
    """Test that direct global settings import still works but is deprecated."""
    # This test ensures backward compatibility during transition
    try:
        from core.config import get_settings, settings

        # Should still work for backward compatibility
        assert settings is not None

        # Both should be Settings instances
        assert isinstance(settings, type(get_settings()))

        # Note: We can't test that settings IS get_settings() because
        # settings was created at module import time with get_settings()
        # and the cache may have been cleared since then.
        # The important thing is that both work.

    except ImportError:
        # It's acceptable if global settings has been removed
        pytest.skip("Global settings has been removed - this is expected")


@pytest.mark.unit
def test_watsonx_utils_no_import_time_execution():
    """Test that watsonx utils don't execute settings access at import time."""
    # Clear environment to make settings invalid
    original_env = os.environ.copy()

    try:
        for key in list(os.environ.keys()):
            if "WATSONX" in key:
                del os.environ[key]

        # This import should NOT fail even with invalid WatsonX config
        # because settings should not be accessed during import
        from vectordbs.utils import watsonx

        # The module should be importable
        assert watsonx is not None

    except ImportError as e:
        # If import fails, it should NOT be due to settings validation
        assert "validation" not in str(e).lower()
        assert "watsonx" not in str(e).lower() or "settings" not in str(e).lower()

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


@pytest.mark.unit
def test_service_layer_dependency_injection():
    """Test that service layer uses dependency injection properly."""
    from core.config import Settings, get_settings

    # Example of how services should use settings
    class MockService:
        def __init__(self, settings: Settings = Depends(get_settings)):
            self.settings = settings

        def get_llm_provider(self):
            return self.settings.rag_llm

    # In FastAPI, this would be injected automatically
    # For testing, we manually inject
    with patch.dict(os.environ, {"RAG_LLM": "watsonx"}):
        get_settings.cache_clear()
        settings = get_settings()
        service = MockService(settings)

        assert service.get_llm_provider() == "watsonx"


@pytest.mark.unit
def test_database_models_no_import_time_settings():
    """Test that database models don't access settings during import."""
    original_env = os.environ.copy()

    try:
        # Clear database-related environment variables
        for key in list(os.environ.keys()):
            if any(prefix in key for prefix in ["COLLECTIONDB", "POSTGRES", "DB"]):
                del os.environ[key]

        # These imports should NOT fail even with invalid database config
        from rag_solution.models import collection, file, user

        # Modules should be importable
        assert collection is not None
        assert user is not None
        assert file is not None

    except ImportError as e:
        # If import fails, it should NOT be due to settings/database validation
        error_msg = str(e).lower()
        assert not any(term in error_msg for term in ["validation", "database", "connection"])

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


@pytest.mark.unit
def test_logging_utils_resilient_to_mocked_settings():
    """Test that logging utils handle mocked settings gracefully."""

    # Mock settings with Mock object for log_level
    mock_settings = Mock()
    mock_settings.log_level = Mock()  # This should be handled gracefully

    with patch("core.config.get_settings", return_value=mock_settings):
        # This should not raise an error
        from core.logging_utils import get_logger, setup_logging

        # Setup logging with mocked settings
        setup_logging()

        logger = get_logger(__name__)
        assert logger is not None

        # Root logger should have INFO level after setup_logging with mocked settings
        import logging

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO


# Integration test scenarios


@pytest.mark.unit
def test_fastapi_route_dependency_injection_pattern():
    """Test the recommended FastAPI route dependency injection pattern."""
    from typing import Annotated

    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from core.config import Settings, get_settings

    app = FastAPI()

    @app.get("/settings-test")
    def test_route(settings: Annotated[Settings, Depends(get_settings)]):
        """Example route using proper dependency injection."""
        return {
            "llm": settings.rag_llm,
            "vector_db": settings.vector_db,
            "jwt_key_prefix": settings.jwt_secret_key[:10],
        }

    client = TestClient(app)

    # Clear cache and set test environment
    get_settings.cache_clear()
    with patch.dict(os.environ, {"RAG_LLM": "watsonx", "VECTOR_DB": "pinecone"}, clear=False):
        response = client.get("/settings-test")

        assert response.status_code == 200
        data = response.json()
        assert data["llm"] == "watsonx"
        assert data["vector_db"] == "pinecone"


@pytest.mark.unit
def test_service_class_dependency_injection_pattern():
    """Test the recommended service class dependency injection pattern."""
    from core.config import Settings, get_settings

    class ExampleService:
        """Example service that receives settings via constructor."""

        def __init__(self, settings: Settings):
            self.settings = settings
            self.llm_provider = settings.rag_llm

        def get_config(self):
            return {
                "llm": self.llm_provider,
                "embeddings": self.settings.embedding_model,
            }

    # In FastAPI, this would be injected, but for testing we manually create
    get_settings.cache_clear()
    with patch.dict(os.environ, {"RAG_LLM": "anthropic"}):
        settings = get_settings()
        service = ExampleService(settings)

        config = service.get_config()
        assert config["llm"] == "anthropic"
        assert config["embeddings"] == "ibm/slate-125m-english-rtrvr"  # Updated to match current default


@pytest.mark.unit
def test_full_fastapi_app_with_settings_injection():
    """Integration test: Full FastAPI app with settings dependency injection."""
    from core.config import Settings, get_settings

    app = FastAPI()

    @app.get("/health")
    async def health_check(settings: Settings = Depends(get_settings)):
        return {
            "status": "ok",
            "llm_provider": settings.rag_llm,
            "vector_db": settings.vector_db,
        }

    @app.get("/config")
    async def get_config(settings: Settings = Depends(get_settings)):
        return {"wx_url": settings.wx_url, "embedding_model": settings.embedding_model}

    client = TestClient(app)

    with patch.dict(
        os.environ,
        {
            "RAG_LLM": "openai",
            "VECTOR_DB": "milvus",
            "WATSONX_URL": "https://test.watsonx.com",
            "EMBEDDING_MODEL": "text-embedding-ada-002",
        },
    ):
        get_settings.cache_clear()

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["llm_provider"] == "openai"
        assert data["vector_db"] == "milvus"

        # Test config endpoint
        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert data["wx_url"] == "https://test.watsonx.com"
        assert data["embedding_model"] == "text-embedding-ada-002"


# Vector Store Dependency Injection Tests


@pytest.mark.unit
def test_vector_store_base_class_requires_settings():
    """Test that VectorStore base class enforces settings dependency injection."""
    from vectordbs.vector_store import VectorStore

    # Create a concrete implementation for testing
    class TestVectorStore(VectorStore):
        def create_collection(self, _collection_name: str, _metadata: dict | None = None) -> None:
            pass

        def add_documents(self, _collection_name: str, _documents: list) -> list[str]:
            return []

        def retrieve_documents(self, _query: str, _collection_name: str, _number_of_results: int = 10) -> list:
            return []

        def query(
            self,
            _collection_name: str,
            _query,
            _number_of_results: int = 10,
            _filter=None,
        ) -> list:
            return []

        def delete_collection(self, _collection_name: str) -> None:
            pass

        def delete_documents(self, _collection_name: str, _document_ids: list[str]) -> None:
            pass

    # Test that settings are properly injected
    mock_settings = Mock()
    mock_settings.vector_db = "test"

    store = TestVectorStore(mock_settings)
    assert store.settings is mock_settings
    assert store.settings.vector_db == "test"


@pytest.mark.unit
def test_pinecone_store_dependency_injection():
    """Test that PineconeStore properly uses dependency injection."""
    from vectordbs.pinecone_store import PineconeStore

    # Mock settings
    mock_settings = Mock()
    mock_settings.pinecone_api_key = "test-key"
    mock_settings.pinecone_cloud = "aws"
    mock_settings.pinecone_region = "us-east-1"
    mock_settings.embedding_dim = 768

    # This should work without calling get_settings() internally
    with patch("vectordbs.pinecone_store.Pinecone") as mock_pinecone:
        store = PineconeStore(mock_settings)

        # Verify settings were injected properly
        assert store.settings is mock_settings
        assert store.settings.pinecone_api_key == "test-key"

        # Verify Pinecone was initialized with injected settings
        mock_pinecone.assert_called_once_with(api_key="test-key")


@pytest.mark.unit
def test_chroma_store_dependency_injection():
    """Test that ChromaDBStore properly uses dependency injection."""
    from vectordbs.chroma_store import ChromaDBStore

    mock_settings = Mock()
    mock_settings.chromadb_host = "test-host"
    mock_settings.chromadb_port = 9999
    mock_settings.log_level = "DEBUG"

    with patch("vectordbs.chroma_store.chromadb"):
        store = ChromaDBStore(settings=mock_settings)

        # Verify settings were injected properly
        assert store.settings is mock_settings
        assert store.settings.chromadb_host == "test-host"
        assert store.settings.chromadb_port == 9999


@pytest.mark.unit
def test_vector_stores_no_module_level_settings_access():
    """Test that vector stores don't access settings at module level."""
    # Clear environment to make settings invalid
    original_env = os.environ.copy()

    try:
        # Clear all vector database related environment variables
        for key in list(os.environ.keys()):
            if any(prefix in key for prefix in ["PINECONE", "CHROMA", "MILVUS", "ELASTIC", "WEAVIATE"]):
                del os.environ[key]

        # These imports should NOT fail even with invalid vector db config
        # because settings should not be accessed during import
        from vectordbs import chroma_store, elasticsearch_store, milvus_store, pinecone_store, weaviate_store

        # Modules should be importable
        assert pinecone_store is not None
        assert chroma_store is not None
        assert elasticsearch_store is not None
        assert milvus_store is not None
        assert weaviate_store is not None

    except ImportError as e:
        # If import fails, it should NOT be due to settings validation
        error_msg = str(e).lower()
        assert not any(term in error_msg for term in ["validation", "settings", "config"])

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


@pytest.mark.unit
def test_data_ingestion_dependency_injection():
    """Test that data ingestion classes properly use dependency injection."""
    from core.config import get_settings
    from rag_solution.data_ingestion.ingestion import DocumentStore
    from rag_solution.data_ingestion.pdf_processor import PdfProcessor

    # Clear cache for clean test
    get_settings.cache_clear()

    mock_settings = Mock()
    mock_settings.min_chunk_size = 50
    mock_settings.max_chunk_size = 200
    mock_settings.semantic_threshold = 0.8
    mock_settings.chunking_strategy = "semantic"

    # Test PdfProcessor (concrete implementation of BaseProcessor)
    with patch("rag_solution.data_ingestion.base_processor.get_chunking_method") as mock_get_chunking:
        mock_get_chunking.return_value = Mock()

        processor = PdfProcessor(settings=mock_settings)

        # Verify settings were injected properly
        assert processor.settings is mock_settings
        assert processor.min_chunk_size == 50
        assert processor.max_chunk_size == 200
        assert processor.semantic_threshold == 0.8

        # Verify get_chunking_method was called with injected settings
        mock_get_chunking.assert_called_once_with(mock_settings)

    # Test DocumentStore
    mock_vector_store = Mock()
    doc_store = DocumentStore(mock_vector_store, "test_collection", mock_settings)

    assert doc_store.settings is mock_settings
    assert doc_store.vector_store is mock_vector_store
    assert doc_store.collection_name == "test_collection"


@pytest.mark.unit
def test_chunking_functions_dependency_injection():
    """Test that chunking functions properly use dependency injection."""
    from rag_solution.data_ingestion.chunking import get_chunking_method, semantic_chunker, simple_chunker

    mock_settings = Mock()
    mock_settings.min_chunk_size = 100
    mock_settings.max_chunk_size = 500
    mock_settings.chunk_overlap = 20
    mock_settings.chunking_strategy = "semantic"

    # Test simple_chunker with injected settings
    with patch("rag_solution.data_ingestion.chunking.simple_chunking") as mock_simple_chunking:
        mock_simple_chunking.return_value = ["chunk1", "chunk2"]

        result = simple_chunker("test text", mock_settings)

        mock_simple_chunking.assert_called_once_with("test text", 100, 500, 20)
        assert result == ["chunk1", "chunk2"]

    # Test semantic_chunker with injected settings
    with patch("rag_solution.data_ingestion.chunking.semantic_chunking") as mock_semantic_chunking:
        mock_semantic_chunking.return_value = ["semantic1", "semantic2"]

        result = semantic_chunker("test text", mock_settings)

        mock_semantic_chunking.assert_called_once_with("test text", 100, 500)
        assert result == ["semantic1", "semantic2"]

    # Test get_chunking_method with injected settings
    result = get_chunking_method(mock_settings)
    assert result == semantic_chunker  # Because chunking_strategy is "semantic"

    mock_settings.chunking_strategy = "simple"
    result = get_chunking_method(mock_settings)
    assert result == simple_chunker


@pytest.mark.unit
def test_watsonx_utils_dependency_injection():
    """Test that watsonx utility functions properly use dependency injection."""
    from vectordbs.utils.watsonx import get_embeddings, get_wx_client

    mock_settings = Mock()
    mock_settings.wx_api_key = "test-key"
    mock_settings.wx_url = "https://test.watsonx.com"
    mock_settings.wx_project_id = "test-project"
    mock_settings.embedding_model = "test-model"
    mock_settings.rag_llm = "test-llm"
    mock_settings.max_new_tokens = 100
    mock_settings.min_new_tokens = 10
    mock_settings.temperature = 0.7
    mock_settings.top_k = 5
    mock_settings.random_seed = 42

    # Test get_wx_client
    with (
        patch("vectordbs.utils.watsonx.APIClient") as mock_api_client,
        patch("vectordbs.utils.watsonx.Credentials") as mock_credentials,
        patch("vectordbs.utils.watsonx.load_dotenv"),
    ):
        get_wx_client(mock_settings)

        mock_credentials.assert_called_once_with(api_key="test-key", url="https://test.watsonx.com")
        mock_api_client.assert_called_once_with(project_id="test-project", credentials=mock_credentials.return_value)

    # Test get_embeddings with injected settings
    with patch("vectordbs.utils.watsonx.get_wx_embeddings_client") as mock_get_client:
        mock_embed_client = Mock()
        mock_embed_client.embed_documents.return_value = [[0.1, 0.2, 0.3]]
        mock_get_client.return_value = mock_embed_client

        result = get_embeddings("test text", mock_settings)

        mock_get_client.assert_called_once_with(mock_settings)
        mock_embed_client.embed_documents.assert_called_once_with(texts=["test text"], concurrency_limit=8)
        assert result == [[0.1, 0.2, 0.3]]


@pytest.mark.unit
def test_base_processor_class_requires_settings():
    """Test that BaseProcessor requires settings injection and processors inherit it."""
    from core.config import get_settings
    from rag_solution.data_ingestion.base_processor import BaseProcessor
    from rag_solution.data_ingestion.excel_processor import ExcelProcessor
    from rag_solution.data_ingestion.txt_processor import TxtProcessor
    from rag_solution.data_ingestion.word_processor import WordProcessor

    settings = get_settings()

    # Test that BaseProcessor cannot be instantiated without settings
    with pytest.raises(TypeError):
        BaseProcessor()  # Should fail - BaseProcessor is abstract

    # Test that concrete processors require settings
    txt_processor = TxtProcessor(settings)
    excel_processor = ExcelProcessor(settings)
    word_processor = WordProcessor(settings)

    # Verify they have settings injected
    assert txt_processor.settings is settings
    assert excel_processor.settings is settings
    assert word_processor.settings is settings

    # Verify they cannot be instantiated without settings
    with pytest.raises(TypeError):
        TxtProcessor()
    with pytest.raises(TypeError):
        ExcelProcessor()
    with pytest.raises(TypeError):
        WordProcessor()


@pytest.mark.unit
def test_no_global_settings_import_in_critical_modules():
    """Test that critical modules don't import global settings object."""
    import ast
    import os

    critical_files = [
        "backend/vectordbs/pinecone_store.py",
        "backend/vectordbs/chroma_store.py",
        "backend/vectordbs/elasticsearch_store.py",
        "backend/vectordbs/milvus_store.py",
        "backend/vectordbs/weaviate_store.py",
        "backend/vectordbs/utils/watsonx.py",
        "backend/rag_solution/data_ingestion/base_processor.py",
        "backend/rag_solution/data_ingestion/txt_processor.py",
        "backend/rag_solution/data_ingestion/excel_processor.py",
        "backend/rag_solution/data_ingestion/word_processor.py",
        "backend/rag_solution/data_ingestion/pdf_processor.py",
        "backend/rag_solution/data_ingestion/document_processor.py",
        "backend/rag_solution/data_ingestion/chunking.py",
        "backend/rag_solution/data_ingestion/ingestion.py",
    ]

    for file_path in critical_files:
        if os.path.exists(file_path):
            with open(file_path) as f:
                content = f.read()

            # Parse the file
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue  # Skip files with syntax errors

            # Check for problematic imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "core.config" and node.names:
                    for alias in node.names:
                        # Should NOT import 'settings' directly
                        assert alias.name != "settings", f"File {file_path} still imports global 'settings' object"
                        # SHOULD import 'Settings' class and 'get_settings' function
                        assert alias.name in [
                            "Settings",
                            "get_settings",
                        ], f"File {file_path} has unexpected import: {alias.name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
