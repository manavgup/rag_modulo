"""TDD Red Phase: Unit tests for SearchService token tracking integration.

Unit tests focus on SearchService behavior with token tracking functionality.
All tests should fail initially as the token tracking features don't exist yet.
"""

import time
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType, TokenWarning, TokenWarningType
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.search_service import SearchService


class TestSearchServiceTokenTrackingTDD:
    """Unit tests for SearchService token tracking functionality."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Create mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create mock settings."""
        return Mock()

    @pytest.fixture
    def search_service(self, mock_db: Mock, mock_settings: Mock) -> SearchService:
        """Create SearchService with mocked dependencies."""
        service = SearchService(db=mock_db, settings=mock_settings)

        # Mock internal services
        service._pipeline_service = Mock()
        service._collection_service = Mock()
        service._chain_of_thought_service = None

        return service

    @pytest.fixture
    def mock_llm_provider(self) -> Mock:
        """Create mock LLM provider with token tracking."""
        provider = Mock()

        # Mock the generate_text_with_usage method
        async def mock_generate_with_usage(
            prompt: str, service_type: ServiceType, user_id: str = None, session_id: str = None
        ):
            usage = LLMUsage(
                prompt_tokens=1200,
                completion_tokens=300,
                total_tokens=1500,
                model_name="gpt-3.5-turbo",
                service_type=service_type,
                timestamp=datetime.utcnow(),
                user_id=user_id,
                session_id=session_id,
            )
            return "Generated response text", usage

        provider.generate_text_with_usage = AsyncMock(side_effect=mock_generate_with_usage)
        return provider

    @pytest.fixture
    def mock_token_warning_service(self) -> Mock:
        """Create mock token warning service."""
        service = Mock()
        service.check_usage_warning = AsyncMock(return_value=None)  # No warning by default
        return service

    # ==================== REGULAR SEARCH WITH TOKEN TRACKING ====================

    @pytest.mark.skip(reason="TDD test - functionality not implemented yet")
    @pytest.mark.unit
    async def test_search_regular_includes_token_usage_in_metadata(
        self, search_service: SearchService, mock_llm_provider: Mock, mock_token_warning_service: Mock
    ) -> None:
        """Unit: Test regular search includes token usage in response metadata."""
        # Mock dependencies
        search_service._validate_search_input = Mock()  # type: ignore
        search_service._validate_collection_access = Mock()  # type: ignore
        search_service._resolve_user_default_pipeline = Mock(return_value=uuid4())  # type: ignore
        search_service.pipeline_service.get_pipeline_config = Mock(return_value=Mock())  # type: ignore
        # search_service._retrieve_documents = AsyncMock(return_value=[])  # Method doesn't exist
        # search_service._build_context_from_documents = Mock(return_value="test context")  # Method doesn't exist
        # search_service._build_generation_prompt = Mock(return_value="test prompt")  # Method doesn't exist
        # search_service._get_llm_provider = Mock(return_value=mock_llm_provider)  # Method doesn't exist
        search_service._token_tracking_service = mock_token_warning_service  # type: ignore

        search_input = SearchInput(
            question="What is AI?",
            collection_id=uuid4(),
            user_id=uuid4(),
            config_metadata={"session_id": "session_123"},
        )

        result = await search_service._search_regular_with_tokens(search_input, time.time())  # type: ignore

        # Verify token usage is included in metadata
        assert "token_usage" in result.metadata
        token_usage = result.metadata["token_usage"]
        assert token_usage["prompt_tokens"] == 1200
        assert token_usage["completion_tokens"] == 300
        assert token_usage["total_tokens"] == 1500
        assert token_usage["model_name"] == "gpt-3.5-turbo"

        # Verify LLM provider was called with correct parameters
        mock_llm_provider.generate_text_with_usage.assert_called_once()
        call_args = mock_llm_provider.generate_text_with_usage.call_args
        assert call_args[1]["service_type"] == ServiceType.SEARCH
        assert call_args[1]["user_id"] == str(search_input.user_id)
        assert call_args[1]["session_id"] == "session_123"

    @pytest.mark.skip(reason="TDD test - functionality not implemented yet")
    @pytest.mark.unit
    async def test_search_regular_includes_token_warning_in_metadata(
        self, search_service: SearchService, mock_llm_provider: Mock
    ) -> None:
        """Unit: Test regular search includes token warning in response metadata when present."""
        # Create a mock token warning
        warning = TokenWarning(
            warning_type=TokenWarningType.APPROACHING_LIMIT,
            current_tokens=3500,
            limit_tokens=4096,
            percentage_used=85.4,
            message="Context window is 85% full",
            severity="warning",
            suggested_action="consider_new_session",
        )

        # Mock token warning service to return warning
        mock_token_warning_service = Mock()
        mock_token_warning_service.check_usage_warning = AsyncMock(return_value=warning)

        # Mock other dependencies
        search_service._validate_search_input = Mock()  # type: ignore
        search_service._validate_collection_access = Mock()  # type: ignore
        search_service._resolve_user_default_pipeline = Mock(return_value=uuid4())  # type: ignore
        search_service.pipeline_service.get_pipeline_config = Mock(return_value=Mock())  # type: ignore
        # search_service._retrieve_documents = AsyncMock(return_value=[])  # Method doesn't exist
        # search_service._build_context_from_documents = Mock(return_value="test context")  # Method doesn't exist
        # search_service._build_generation_prompt = Mock(return_value="test prompt")  # Method doesn't exist
        # search_service._get_llm_provider = Mock(return_value=mock_llm_provider)  # Method doesn't exist
        search_service._token_tracking_service = mock_token_warning_service  # type: ignore

        search_input = SearchInput(
            question="What is AI?",
            collection_id=uuid4(),
            user_id=uuid4(),
        )

        result = await search_service._search_regular_with_tokens(search_input, time.time())  # type: ignore

        # Verify token warning is included in metadata
        assert "token_warning" in result.metadata
        token_warning = result.metadata["token_warning"]
        assert token_warning["type"] == "approaching_limit"
        assert token_warning["message"] == "Context window is 85% full"
        assert token_warning["percentage_used"] == 85.4
        assert token_warning["severity"] == "warning"
        assert token_warning["suggested_action"] == "consider_new_session"

    @pytest.mark.skip(reason="TDD test - functionality not implemented yet")
    @pytest.mark.unit
    async def test_search_regular_no_token_warning_when_none(
        self, search_service: SearchService, mock_llm_provider: Mock, mock_token_warning_service: Mock
    ) -> None:
        """Unit: Test regular search doesn't include token warning when none present."""
        # Mock dependencies (token warning service returns None by default)
        search_service._validate_search_input = Mock()  # type: ignore
        search_service._validate_collection_access = Mock()  # type: ignore
        search_service._resolve_user_default_pipeline = Mock(return_value=uuid4())  # type: ignore
        search_service.pipeline_service.get_pipeline_config = Mock(return_value=Mock())  # type: ignore
        # search_service._retrieve_documents = AsyncMock(return_value=[])  # Method doesn't exist
        # search_service._build_context_from_documents = Mock(return_value="test context")  # Method doesn't exist
        # search_service._build_generation_prompt = Mock(return_value="test prompt")  # Method doesn't exist
        # search_service._get_llm_provider = Mock(return_value=mock_llm_provider)  # Method doesn't exist
        search_service._token_tracking_service = mock_token_warning_service  # type: ignore

        search_input = SearchInput(
            question="What is AI?",
            collection_id=uuid4(),
            user_id=uuid4(),
        )

        result = await search_service._search_regular_with_tokens(search_input, time.time())  # type: ignore

        # Verify no token warning in metadata
        assert "token_warning" not in result.metadata
        assert "token_usage" in result.metadata  # But usage should still be there

    # ==================== CHAIN OF THOUGHT SEARCH WITH TOKEN TRACKING ====================

    @pytest.mark.skip(reason="TDD test - functionality not implemented yet")
    @pytest.mark.unit
    async def test_search_chain_of_thought_includes_aggregated_token_usage(
        self, search_service: SearchService, mock_llm_provider: Mock, mock_token_warning_service: Mock
    ) -> None:
        """Unit: Test CoT search includes aggregated token usage from all steps."""
        # Mock CoT service
        mock_cot_service = Mock()

        # Mock CoT result with token usage
        mock_cot_result = Mock()
        mock_cot_result.final_answer = "CoT generated answer"
        mock_cot_result.reasoning_steps = [
            Mock(
                step_type="classification",
                token_usage=LLMUsage(400, 100, 500, "gpt-3.5-turbo", ServiceType.CHAIN_OF_THOUGHT, datetime.utcnow()),
            ),
            Mock(
                step_type="generation",
                token_usage=LLMUsage(800, 200, 1000, "gpt-3.5-turbo", ServiceType.CHAIN_OF_THOUGHT, datetime.utcnow()),
            ),
            Mock(
                step_type="synthesis",
                token_usage=LLMUsage(600, 150, 750, "gpt-3.5-turbo", ServiceType.CHAIN_OF_THOUGHT, datetime.utcnow()),
            ),
        ]

        # Mock aggregate_token_usage method
        def mock_aggregate():
            return LLMUsage(
                prompt_tokens=1800,  # 400 + 800 + 600
                completion_tokens=450,  # 100 + 200 + 150
                total_tokens=2250,  # 500 + 1000 + 750
                model_name="gpt-3.5-turbo",
                service_type=ServiceType.CHAIN_OF_THOUGHT,
                timestamp=datetime.utcnow(),
            )

        mock_cot_result.aggregate_token_usage = mock_aggregate
        mock_cot_service.process_chain_of_thought_with_tokens = AsyncMock(return_value=mock_cot_result)

        # Mock other dependencies
        search_service._validate_search_input = Mock()  # type: ignore
        search_service._validate_collection_access = Mock()  # type: ignore
        search_service._resolve_user_default_pipeline = Mock(return_value=uuid4())  # type: ignore
        search_service.pipeline_service.get_pipeline_config = Mock(return_value=Mock())  # type: ignore
        # search_service._retrieve_documents = AsyncMock(return_value=[])  # Method doesn't exist
        # search_service._build_context_from_documents = Mock(return_value="test context")  # Method doesn't exist
        # search_service._get_llm_provider = Mock(return_value=mock_llm_provider)  # Method doesn't exist
        search_service.chain_of_thought_service = mock_cot_service  # type: ignore  # type: ignore
        search_service._token_tracking_service = mock_token_warning_service  # type: ignore  # type: ignore

        search_input = SearchInput(
            question="Complex question requiring CoT?",
            collection_id=uuid4(),
            user_id=uuid4(),
        )

        result = await search_service._search_with_chain_of_thought(search_input, time.time())  # type: ignore

        # Verify aggregated token usage is included
        assert "token_usage" in result.metadata
        token_usage = result.metadata["token_usage"]
        assert token_usage["prompt_tokens"] == 1800
        assert token_usage["completion_tokens"] == 450
        assert token_usage["total_tokens"] == 2250

        # Verify CoT token breakdown is included
        assert "cot_token_breakdown" in result.metadata
        breakdown = result.metadata["cot_token_breakdown"]
        assert len(breakdown) == 3
        assert breakdown[0]["step"] == "classification"
        assert breakdown[0]["total_tokens"] == 500
        assert breakdown[1]["step"] == "generation"
        assert breakdown[1]["total_tokens"] == 1000
        assert breakdown[2]["step"] == "synthesis"
        assert breakdown[2]["total_tokens"] == 750

    @pytest.mark.skip(reason="TDD test - functionality not implemented yet")
    @pytest.mark.unit
    async def test_search_cot_includes_token_warning(
        self, search_service: SearchService, mock_llm_provider: Mock
    ) -> None:
        """Unit: Test CoT search includes token warning based on aggregated usage."""
        # Create a mock token warning for high usage
        warning = TokenWarning(
            warning_type=TokenWarningType.AT_LIMIT,
            current_tokens=3900,
            limit_tokens=4096,
            percentage_used=95.2,
            message="Context window is 95% full",
            severity="critical",
            suggested_action="start_new_session",
        )

        # Mock token warning service
        mock_token_warning_service = Mock()
        mock_token_warning_service.check_usage_warning = AsyncMock(return_value=warning)

        # Mock CoT service with high token usage
        mock_cot_service = Mock()
        mock_cot_result = Mock()
        mock_cot_result.final_answer = "CoT answer"
        mock_cot_result.reasoning_steps = []

        def mock_aggregate():
            return LLMUsage(
                prompt_tokens=3700,  # High usage
                completion_tokens=200,
                total_tokens=3900,
                model_name="gpt-3.5-turbo",
                service_type=ServiceType.CHAIN_OF_THOUGHT,
                timestamp=datetime.utcnow(),
            )

        mock_cot_result.aggregate_token_usage = mock_aggregate
        mock_cot_service.process_chain_of_thought_with_tokens = AsyncMock(return_value=mock_cot_result)

        # Mock other dependencies
        search_service._validate_search_input = Mock()  # type: ignore
        search_service._validate_collection_access = Mock()  # type: ignore
        search_service._resolve_user_default_pipeline = Mock(return_value=uuid4())  # type: ignore
        search_service.pipeline_service.get_pipeline_config = Mock(return_value=Mock())  # type: ignore
        # search_service._retrieve_documents = AsyncMock(return_value=[])  # Method doesn't exist
        # search_service._build_context_from_documents = Mock(return_value="test context")  # Method doesn't exist
        # search_service._get_llm_provider = Mock(return_value=mock_llm_provider)  # Method doesn't exist
        search_service.chain_of_thought_service = mock_cot_service  # type: ignore  # type: ignore
        search_service._token_tracking_service = mock_token_warning_service  # type: ignore  # type: ignore

        search_input = SearchInput(
            question="Complex question?",
            collection_id=uuid4(),
            user_id=uuid4(),
        )

        result = await search_service._search_with_chain_of_thought(search_input, time.time())  # type: ignore

        # Verify token warning is included
        assert "token_warning" in result.metadata
        token_warning = result.metadata["token_warning"]
        assert token_warning["type"] == "at_limit"
        assert token_warning["severity"] == "critical"
        assert token_warning["suggested_action"] == "start_new_session"

    # ==================== SEARCH METHOD SELECTION TESTS ====================

    @pytest.mark.skip(reason="TDD test - functionality not implemented yet")
    @pytest.mark.unit
    async def test_search_uses_cot_when_should_use_chain_of_thought_returns_true(
        self, search_service: SearchService, mock_llm_provider: Mock, mock_token_warning_service: Mock
    ) -> None:
        """Unit: Test search uses CoT with token tracking when should_use_chain_of_thought returns true."""
        # Mock _should_use_chain_of_thought to return True
        search_service._should_use_chain_of_thought = Mock(return_value=True)  # type: ignore

        # Mock CoT search method
        expected_result = SearchOutput(
            answer="CoT answer",
            documents=[],
            query_results=[],
            execution_time=1.5,
            metadata={
                "search_method": "chain_of_thought",
                "token_usage": {"total_tokens": 2000},
            },
        )
        search_service._search_with_chain_of_thought = AsyncMock(return_value=expected_result)  # type: ignore

        search_input = SearchInput(
            question="Complex question?",
            collection_id=uuid4(),
            user_id=uuid4(),
        )

        result = await search_service.search(search_input)

        # Verify CoT method was called
        search_service._search_with_chain_of_thought.assert_called_once()  # type: ignore
        assert result.metadata["search_method"] == "chain_of_thought"

    @pytest.mark.skip(reason="TDD test - functionality not implemented yet")
    @pytest.mark.unit
    async def test_search_falls_back_to_regular_when_cot_fails(
        self, search_service: SearchService, mock_llm_provider: Mock, mock_token_warning_service: Mock
    ) -> None:
        """Unit: Test search falls back to regular search when CoT fails."""
        # Mock _should_use_chain_of_thought to return True
        search_service._should_use_chain_of_thought = Mock(return_value=True)  # type: ignore

        # Mock CoT search to raise exception
        search_service._search_with_chain_of_thought = AsyncMock(side_effect=Exception("CoT failed"))  # type: ignore

        # Mock regular search method
        expected_result = SearchOutput(
            answer="Regular answer",
            documents=[],
            query_results=[],
            execution_time=1.0,
            metadata={
                "search_method": "regular",
                "token_usage": {"total_tokens": 1500},
            },
        )
        search_service._search_regular_with_tokens = AsyncMock(return_value=expected_result)  # type: ignore

        search_input = SearchInput(
            question="Question that should use CoT",
            collection_id=uuid4(),
            user_id=uuid4(),
        )

        result = await search_service.search(search_input)

        # Verify fallback occurred
        search_service._search_with_chain_of_thought.assert_called_once()  # type: ignore
        search_service._search_regular_with_tokens.assert_called_once()  # type: ignore
        assert result.metadata["search_method"] == "regular"

    # ==================== TOKEN WARNING SERVICE INTEGRATION TESTS ====================

    @pytest.mark.unit
    def test_search_service_initializes_token_warning_service_lazily(self, search_service: SearchService) -> None:
        """Unit: Test search service initializes token warning service lazily."""
        # Ensure it starts as None
        search_service._token_tracking_service = None
        assert search_service._token_tracking_service is None

        # Accessing property should initialize it
        with patch("rag_solution.services.search_service.TokenTrackingService") as mock_warning_service_class:
            mock_warning_service = Mock()
            mock_warning_service_class.return_value = mock_warning_service

            warning_service = search_service.token_tracking_service

            # Should have created the service
            mock_warning_service_class.assert_called_once_with(search_service.db, search_service.settings)
            assert warning_service == mock_warning_service

    # ==================== SESSION ID PROPAGATION TESTS ====================

    @pytest.mark.unit
    async def test_search_propagates_session_id_to_llm_provider(
        self, search_service: SearchService, mock_llm_provider: Mock, mock_token_warning_service: Mock
    ) -> None:
        """Unit: Test search propagates session_id from config_metadata to LLM provider."""
        # Mock dependencies
        search_service._validate_search_input = Mock()  # type: ignore
        search_service._validate_collection_access = Mock()  # type: ignore
        search_service._resolve_user_default_pipeline = Mock(return_value=uuid4())  # type: ignore
        search_service.pipeline_service.get_pipeline_config = Mock(return_value=Mock())  # type: ignore
        # search_service._retrieve_documents = AsyncMock(return_value=[])  # Method doesn't exist
        # search_service._build_context_from_documents = Mock(return_value="test context")  # Method doesn't exist
        # search_service._build_generation_prompt = Mock(return_value="test prompt")  # Method doesn't exist
        # search_service._get_llm_provider = Mock(return_value=mock_llm_provider)  # Method doesn't exist
        search_service._token_tracking_service = mock_token_warning_service  # type: ignore

        search_input = SearchInput(
            question="What is AI?",
            collection_id=uuid4(),
            user_id=uuid4(),
            config_metadata={"session_id": "session_xyz_789"},
        )

        await search_service._search_regular_with_tokens(search_input, time.time())  # type: ignore

        # Verify session_id was passed to LLM provider
        mock_llm_provider.generate_text_with_usage.assert_called_once()
        call_args = mock_llm_provider.generate_text_with_usage.call_args
        assert call_args[1]["session_id"] == "session_xyz_789"

    @pytest.mark.unit
    async def test_search_handles_missing_session_id_gracefully(
        self, search_service: SearchService, mock_llm_provider: Mock, mock_token_warning_service: Mock
    ) -> None:
        """Unit: Test search handles missing session_id gracefully."""
        # Mock dependencies
        search_service._validate_search_input = Mock()  # type: ignore
        search_service._validate_collection_access = Mock()  # type: ignore
        search_service._resolve_user_default_pipeline = Mock(return_value=uuid4())  # type: ignore
        search_service.pipeline_service.get_pipeline_config = Mock(return_value=Mock())  # type: ignore
        # search_service._retrieve_documents = AsyncMock(return_value=[])  # Method doesn't exist
        # search_service._build_context_from_documents = Mock(return_value="test context")  # Method doesn't exist
        # search_service._build_generation_prompt = Mock(return_value="test prompt")  # Method doesn't exist
        # search_service._get_llm_provider = Mock(return_value=mock_llm_provider)  # Method doesn't exist
        search_service._token_tracking_service = mock_token_warning_service  # type: ignore

        search_input = SearchInput(
            question="What is AI?",
            collection_id=uuid4(),
            user_id=uuid4(),
            # No config_metadata
        )

        await search_service._search_regular_with_tokens(search_input, time.time())  # type: ignore

        # Verify None was passed as session_id
        mock_llm_provider.generate_text_with_usage.assert_called_once()
        call_args = mock_llm_provider.generate_text_with_usage.call_args
        assert call_args[1]["session_id"] is None
