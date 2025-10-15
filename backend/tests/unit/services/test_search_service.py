from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import Settings
from core.custom_exceptions import (
    ConfigurationError,
    LLMProviderError,
    NotFoundError,
    ValidationError,
)
from rag_solution.services.search_service import SearchService, handle_search_errors


@pytest.fixture
def db_session():
    """Fixture for a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def settings():
    """Fixture for a mock settings object."""
    return MagicMock(spec=Settings)


@pytest.fixture
def search_service(db_session, settings):
    """Fixture for a SearchService instance."""
    service = SearchService(db=db_session, settings=settings)
    service._reranker = None
    return service


class TestSearchService:
    """Unit tests for the SearchService class."""

    def test_initialization(self, search_service: SearchService, db_session: Session, settings: Settings):
        """Test that the SearchService initializes correctly."""
        assert search_service.db == db_session
        assert search_service.settings == settings
        assert search_service._file_service is None
        assert search_service._collection_service is None
        assert search_service._pipeline_service is None
        assert search_service._llm_provider_service is None
        assert search_service._chain_of_thought_service is None
        assert search_service._token_tracking_service is None
        assert search_service._reranker is None

    def test_lazy_initialization_of_services(self, search_service: SearchService):
        """Test that the services are lazily initialized."""
        with patch("rag_solution.services.search_service.FileManagementService") as mock_file_service:
            assert search_service.file_service is not None
            mock_file_service.assert_called_once()

        with patch("rag_solution.services.search_service.CollectionService") as mock_collection_service:
            assert search_service.collection_service is not None
            mock_collection_service.assert_called_once()

        with patch("rag_solution.services.search_service.PipelineService") as mock_pipeline_service:
            assert search_service.pipeline_service is not None
            mock_pipeline_service.assert_called_once()

        with patch("rag_solution.services.search_service.LLMProviderService") as mock_llm_provider_service:
            assert search_service.llm_provider_service is not None
            mock_llm_provider_service.assert_called_once()

        with (
            patch("rag_solution.services.chain_of_thought_service.ChainOfThoughtService") as mock_cot_service,
            patch("rag_solution.generation.providers.factory.LLMProviderFactory") as mock_llm_factory,
        ):
            mock_llm_provider = MagicMock()
            mock_llm_provider.name = "test_provider"
            search_service.llm_provider_service.get_default_provider.return_value = mock_llm_provider
            mock_llm_factory.return_value.get_provider.return_value = MagicMock()
            assert search_service.chain_of_thought_service is not None
            mock_cot_service.assert_called_once()

        with patch("rag_solution.services.search_service.TokenTrackingService") as mock_token_tracking_service:
            assert search_service.token_tracking_service is not None
            mock_token_tracking_service.assert_called_once()


class TestGetReranker:
    """Unit tests for the get_reranker method."""

    @pytest.fixture
    def user_id(self):
        """Fixture for a user ID."""
        return uuid4()

    def test_get_reranker_disabled(self, search_service: SearchService, user_id):
        """Test that get_reranker returns None when reranking is disabled."""
        search_service.settings.enable_reranking = False
        assert search_service.get_reranker(user_id) is None

    @patch("rag_solution.retrieval.reranker.SimpleReranker")
    def test_get_reranker_simple(self, mock_simple_reranker, search_service: SearchService, user_id):
        """Test that get_reranker returns a SimpleReranker."""
        search_service.settings.enable_reranking = True
        search_service.settings.reranker_type = "simple"
        reranker = search_service.get_reranker(user_id)
        assert reranker is not None
        mock_simple_reranker.assert_called_once()

    @patch("rag_solution.retrieval.reranker.LLMReranker")
    @patch("rag_solution.services.prompt_template_service.PromptTemplateService")
    @patch("rag_solution.generation.providers.factory.LLMProviderFactory")
    def test_get_reranker_llm_success(
        self,
        mock_llm_factory,
        mock_prompt_service,
        mock_llm_reranker,
        search_service: SearchService,
        user_id,
    ):
        """Test that get_reranker returns an LLMReranker successfully."""
        search_service.settings.enable_reranking = True
        search_service.settings.reranker_type = "llm"
        search_service.settings.reranker_batch_size = 10
        search_service.settings.reranker_score_scale = (0, 1)

        # Mock the llm_provider_service property
        mock_provider = MagicMock()
        mock_provider.name = "test_provider"
        search_service._llm_provider_service = MagicMock()
        search_service._llm_provider_service.get_default_provider.return_value = mock_provider

        # Mock LLM factory and provider
        mock_llm_factory.return_value.get_provider.return_value = MagicMock()

        # Mock prompt service
        mock_prompt_service.return_value.get_by_type.return_value = MagicMock()

        reranker = search_service.get_reranker(user_id)

        assert reranker is not None
        mock_llm_reranker.assert_called_once()

    @patch("rag_solution.retrieval.reranker.SimpleReranker")
    def test_get_reranker_llm_no_provider(
        self, mock_simple_reranker, search_service: SearchService, user_id
    ):
        """Test that get_reranker falls back to SimpleReranker if no provider is found."""
        search_service.settings.enable_reranking = True
        search_service.settings.reranker_type = "llm"

        # Mock the llm_provider_service to return None
        search_service._llm_provider_service = MagicMock()
        search_service._llm_provider_service.get_default_provider.return_value = None

        reranker = search_service.get_reranker(user_id)

        assert reranker is not None
        mock_simple_reranker.assert_called_once()

    @patch("rag_solution.retrieval.reranker.SimpleReranker")
    @patch("rag_solution.services.prompt_template_service.PromptTemplateService")
    @patch("rag_solution.generation.providers.factory.LLMProviderFactory")
    def test_get_reranker_llm_no_template(
        self,
        mock_llm_factory,
        mock_prompt_service,
        mock_simple_reranker,
        search_service: SearchService,
        user_id,
    ):
        """Test that get_reranker falls back to SimpleReranker if no template is found."""
        search_service.settings.enable_reranking = True
        search_service.settings.reranker_type = "llm"

        # Mock the llm_provider_service property
        mock_provider = MagicMock()
        mock_provider.name = "test_provider"
        search_service._llm_provider_service = MagicMock()
        search_service._llm_provider_service.get_default_provider.return_value = mock_provider

        # Mock LLM factory
        mock_llm_factory.return_value.get_provider.return_value = MagicMock()

        # Mock prompt service to raise exception
        mock_prompt_service.return_value.get_by_type.side_effect = Exception("Template not found")

        reranker = search_service.get_reranker(user_id)

        assert reranker is not None
        mock_simple_reranker.assert_called_once()


@pytest.mark.asyncio
async def test_handle_search_errors_decorator():
    """Test the handle_search_errors decorator."""

    @handle_search_errors
    async def successful_function():
        return "Success"

    @handle_search_errors
    async def not_found_error_function():
        raise NotFoundError(resource_id="test_id", resource_type="test_type")

    @handle_search_errors
    async def validation_error_function():
        raise ValidationError("Invalid input")

    @handle_search_errors
    async def llm_provider_error_function():
        raise LLMProviderError("LLM provider failed")

    @handle_search_errors
    async def configuration_error_function():
        raise ConfigurationError("Configuration is invalid")

    @handle_search_errors
    async def generic_error_function():
        raise Exception("Something went wrong")

    assert await successful_function() == "Success"

    with pytest.raises(HTTPException) as excinfo:
        await not_found_error_function()
    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail

    with pytest.raises(HTTPException) as excinfo:
        await validation_error_function()
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Invalid input"

    with pytest.raises(HTTPException) as excinfo:
        await llm_provider_error_function()
    assert excinfo.value.status_code == 500
    assert excinfo.value.detail == "LLM provider failed"

    with pytest.raises(HTTPException) as excinfo:
        await configuration_error_function()
    assert excinfo.value.status_code == 500
    assert excinfo.value.detail == "Configuration is invalid"

    with pytest.raises(HTTPException) as excinfo:
        await generic_error_function()
    assert excinfo.value.status_code == 500
    assert "Error processing search" in excinfo.value.detail
