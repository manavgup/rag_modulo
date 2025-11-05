"""Unit tests for vector database embedding utilities.

This module tests the shared embedding utility used across all vector stores,
ensuring proper functionality of the get_embeddings_for_vector_store helper.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.vectordbs.utils.embeddings import get_embeddings_for_vector_store
from core.config import Settings
from core.custom_exceptions import LLMProviderError


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.llm_provider_name = "watsonx"
    settings.embedding_dim = 768
    return settings


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    session.close = Mock()
    return session


@pytest.fixture
def mock_session_factory(mock_db_session):
    """Create a mock session factory that returns the mock session."""
    factory = Mock()
    factory.return_value = mock_db_session
    return factory


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = Mock()
    # Mock embeddings: [[embedding1], [embedding2]] for list of texts
    provider.get_embeddings.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    return provider


@pytest.fixture
def mock_factory(mock_provider):
    """Create a mock LLMProviderFactory."""
    factory = Mock()
    factory.get_provider.return_value = mock_provider
    return factory


class TestGetEmbeddingsForVectorStore:
    """Test suite for get_embeddings_for_vector_store utility function."""

    def test_successful_embedding_generation_single_text(
        self, mock_settings, mock_session_factory, mock_factory, mock_db_session
    ):
        """Test successful embedding generation for a single text string."""
        with (
            patch("backend.vectordbs.utils.embeddings.create_session_factory", return_value=mock_session_factory),
            patch("backend.vectordbs.utils.embeddings.LLMProviderFactory", return_value=mock_factory),
        ):
            result = get_embeddings_for_vector_store("test query", mock_settings)

            # Verify result
            assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

            # Verify factory was called with correct provider
            mock_factory.get_provider.assert_called_once_with("watsonx")

            # Verify provider was called with text
            mock_factory.get_provider.return_value.get_embeddings.assert_called_once_with("test query")

            # Verify session was closed
            mock_db_session.close.assert_called_once()

    def test_successful_embedding_generation_list_of_texts(
        self, mock_settings, mock_session_factory, mock_factory, mock_db_session
    ):
        """Test successful embedding generation for a list of text strings."""
        with (
            patch("backend.vectordbs.utils.embeddings.create_session_factory", return_value=mock_session_factory),
            patch("backend.vectordbs.utils.embeddings.LLMProviderFactory", return_value=mock_factory),
        ):
            texts = ["query1", "query2"]
            result = get_embeddings_for_vector_store(texts, mock_settings)

            # Verify result
            assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

            # Verify provider was called with list
            mock_factory.get_provider.return_value.get_embeddings.assert_called_once_with(texts)

            # Verify session was closed
            mock_db_session.close.assert_called_once()

    def test_custom_provider_name(self, mock_settings, mock_session_factory, mock_factory, mock_db_session):
        """Test using a custom provider name instead of default."""
        with (
            patch("backend.vectordbs.utils.embeddings.create_session_factory", return_value=mock_session_factory),
            patch("backend.vectordbs.utils.embeddings.LLMProviderFactory", return_value=mock_factory),
        ):
            result = get_embeddings_for_vector_store("test query", mock_settings, provider_name="openai")

            # Verify factory was called with custom provider
            mock_factory.get_provider.assert_called_once_with("openai")

            # Verify result
            assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

            # Verify session was closed
            mock_db_session.close.assert_called_once()

    def test_provider_name_fallback_to_settings(
        self, mock_settings, mock_session_factory, mock_factory, mock_db_session
    ):
        """Test provider name falls back to settings.llm_provider_name."""
        mock_settings.llm_provider_name = "anthropic"

        with (
            patch("backend.vectordbs.utils.embeddings.create_session_factory", return_value=mock_session_factory),
            patch("backend.vectordbs.utils.embeddings.LLMProviderFactory", return_value=mock_factory),
        ):
            result = get_embeddings_for_vector_store("test query", mock_settings)

            # Verify factory was called with settings provider
            mock_factory.get_provider.assert_called_once_with("anthropic")

            # Verify result
            assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    def test_provider_name_default_to_watsonx(self, mock_session_factory, mock_factory, mock_db_session):
        """Test provider name defaults to watsonx when not in settings."""
        # Create settings without llm_provider_name attribute
        mock_settings = Mock(spec=Settings)
        del mock_settings.llm_provider_name  # Remove the attribute

        with (
            patch("backend.vectordbs.utils.embeddings.create_session_factory", return_value=mock_session_factory),
            patch("backend.vectordbs.utils.embeddings.LLMProviderFactory", return_value=mock_factory),
        ):
            result = get_embeddings_for_vector_store("test query", mock_settings)

            # Verify factory was called with default watsonx
            mock_factory.get_provider.assert_called_once_with("watsonx")

            # Verify result
            assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    def test_llm_provider_error_handling(self, mock_settings, mock_session_factory, mock_factory, mock_db_session):
        """Test proper handling of LLMProviderError."""
        # Configure provider to raise LLMProviderError
        mock_factory.get_provider.return_value.get_embeddings.side_effect = LLMProviderError("Provider error")

        with (
            patch("backend.vectordbs.utils.embeddings.create_session_factory", return_value=mock_session_factory),
            patch("backend.vectordbs.utils.embeddings.LLMProviderFactory", return_value=mock_factory),
            pytest.raises(LLMProviderError, match="Provider error"),
        ):
            get_embeddings_for_vector_store("test query", mock_settings)

        # Verify session was still closed even on error
        mock_db_session.close.assert_called_once()

    def test_sqlalchemy_error_handling(self, mock_settings, mock_session_factory, mock_db_session):
        """Test proper handling of SQLAlchemyError."""
        with (
            patch("backend.vectordbs.utils.embeddings.create_session_factory", return_value=mock_session_factory),
            patch(
                "backend.vectordbs.utils.embeddings.LLMProviderFactory",
                side_effect=SQLAlchemyError("Database error"),
            ),
            pytest.raises(SQLAlchemyError, match="Database error"),
        ):
            get_embeddings_for_vector_store("test query", mock_settings)

        # Verify session was still closed even on error
        mock_db_session.close.assert_called_once()

    def test_unexpected_exception_handling(self, mock_settings, mock_session_factory, mock_factory, mock_db_session):
        """Test proper handling of unexpected exceptions."""
        # Configure provider to raise generic exception
        mock_factory.get_provider.return_value.get_embeddings.side_effect = Exception("Unexpected error")

        with (
            patch("backend.vectordbs.utils.embeddings.create_session_factory", return_value=mock_session_factory),
            patch("backend.vectordbs.utils.embeddings.LLMProviderFactory", return_value=mock_factory),
            pytest.raises(Exception, match="Unexpected error"),
        ):
            get_embeddings_for_vector_store("test query", mock_settings)

        # Verify session was still closed even on error
        mock_db_session.close.assert_called_once()

    def test_session_lifecycle_management(self, mock_settings, mock_session_factory, mock_factory, mock_db_session):
        """Test proper session creation and cleanup."""
        with (
            patch("backend.vectordbs.utils.embeddings.create_session_factory", return_value=mock_session_factory),
            patch("backend.vectordbs.utils.embeddings.LLMProviderFactory", return_value=mock_factory),
        ):
            get_embeddings_for_vector_store("test query", mock_settings)

            # Verify session factory was called to create session
            mock_session_factory.assert_called_once()

            # Verify session was closed (cleanup)
            mock_db_session.close.assert_called_once()

    def test_factory_initialization_with_correct_parameters(
        self, mock_settings, mock_session_factory, mock_db_session
    ):
        """Test that LLMProviderFactory is initialized with correct parameters."""
        with (
            patch("backend.vectordbs.utils.embeddings.create_session_factory", return_value=mock_session_factory),
            patch("backend.vectordbs.utils.embeddings.LLMProviderFactory") as factory_class_mock,
        ):
            # Configure mock factory instance
            factory_instance = Mock()
            factory_instance.get_provider.return_value.get_embeddings.return_value = [[0.1, 0.2]]
            factory_class_mock.return_value = factory_instance

            get_embeddings_for_vector_store("test query", mock_settings)

            # Verify factory was initialized with correct parameters
            factory_class_mock.assert_called_once_with(mock_db_session, mock_settings)

    def test_empty_text_handling(self, mock_settings, mock_session_factory, mock_factory, mock_db_session):
        """Test handling of empty text input."""
        with (
            patch("backend.vectordbs.utils.embeddings.create_session_factory", return_value=mock_session_factory),
            patch("backend.vectordbs.utils.embeddings.LLMProviderFactory", return_value=mock_factory),
        ):
            result = get_embeddings_for_vector_store("", mock_settings)

            # Verify provider was called with empty string
            mock_factory.get_provider.return_value.get_embeddings.assert_called_once_with("")

            # Verify result
            assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

            # Verify session was closed
            mock_db_session.close.assert_called_once()

    def test_empty_list_handling(self, mock_settings, mock_session_factory, mock_factory, mock_db_session):
        """Test handling of empty list input."""
        with (
            patch("backend.vectordbs.utils.embeddings.create_session_factory", return_value=mock_session_factory),
            patch("backend.vectordbs.utils.embeddings.LLMProviderFactory", return_value=mock_factory),
        ):
            result = get_embeddings_for_vector_store([], mock_settings)

            # Verify provider was called with empty list
            mock_factory.get_provider.return_value.get_embeddings.assert_called_once_with([])

            # Verify result
            assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

            # Verify session was closed
            mock_db_session.close.assert_called_once()
