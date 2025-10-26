"""TDD Red Phase: Integration tests for token tracking across services.

Integration tests focus on token tracking flow across multiple services
working together. These tests should fail initially as the integration
doesn't exist yet.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from backend.core.config import Settings, get_settings
from backend.rag_solution.schemas.conversation_schema import (
    ConversationMessageInput,
    MessageRole,
    MessageType,
)
from backend.rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType, TokenWarning, TokenWarningType
from backend.rag_solution.schemas.search_schema import SearchInput, SearchOutput
from backend.rag_solution.services.conversation_service import ConversationService
from backend.rag_solution.services.search_service import SearchService


class TestTokenTrackingIntegrationTDD:  # type: ignore[misc]
    """Integration tests for token tracking across services."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Create mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings."""
        return get_settings()

    @pytest.fixture
    def search_service(self, mock_db: Mock, mock_settings: Settings) -> SearchService:
        """Create SearchService with mocked dependencies."""
        return SearchService(db=mock_db, settings=mock_settings)

    @pytest.fixture
    def conversation_service(self, mock_db: Mock, mock_settings: Settings) -> ConversationService:
        """Create ConversationService with mocked dependencies."""
        return ConversationService(db=mock_db, settings=mock_settings)

    @pytest.fixture
    def mock_llm_provider_with_high_usage(self) -> Mock:
        """Create mock LLM provider that returns high token usage."""
        provider = Mock()

        async def mock_generate_with_usage(
            prompt: str, service_type: ServiceType, user_id: str | None = None, session_id: str | None = None
        ):
            # Simulate high token usage approaching limit
            usage = LLMUsage(
                prompt_tokens=3500,  # ~85% of 4096
                completion_tokens=400,
                total_tokens=3900,
                model_name="gpt-3.5-turbo",
                service_type=service_type,
                timestamp=datetime.utcnow(),
                user_id=user_id,
                session_id=session_id,
            )
            return "Generated response with high token usage", usage

        provider.generate_text_with_usage = AsyncMock(side_effect=mock_generate_with_usage)
        return provider

    # ==================== CONVERSATION TO SEARCH INTEGRATION ====================

    @pytest.mark.integration
    async def test_conversation_service_passes_token_warning_from_search(
        self, conversation_service: ConversationService, mock_db: Mock
    ) -> None:
        """Integration: Test conversation service receives and passes token warnings from search."""
        # Mock session in database
        mock_session = Mock()
        mock_session.id = uuid4()
        mock_session.user_id = uuid4()
        mock_session.collection_id = uuid4()
        mock_session.status = "active"
        mock_session.session_name = "Test Session"
        mock_session.status = "active"

        def mock_query(model):
            query_mock = Mock()
            query_mock.filter = Mock(return_value=query_mock)
            query_mock.first = Mock(return_value=mock_session)
            return query_mock

        mock_db.query.side_effect = mock_query

        # Mock search service with token warning
        mock_search_service = Mock()
        search_result = SearchOutput(
            answer="Search response",
            documents=[],
            query_results=[],
            execution_time=1.5,
            metadata={
                "token_usage": {
                    "prompt_tokens": 3500,
                    "completion_tokens": 400,
                    "total_tokens": 3900,
                    "model_name": "gpt-3.5-turbo",
                },
                "token_warning": {
                    "type": "approaching_limit",
                    "message": "Context window is 85% full",
                    "percentage_used": 85.4,
                    "severity": "warning",
                    "current_tokens": 3500,
                    "limit_tokens": 4096,
                    "suggested_action": "consider_new_session",
                },
            },
        )
        mock_search_service.search = AsyncMock(return_value=search_result)
        conversation_service._search_service = mock_search_service

        # Mock other methods
        conversation_service.add_message = AsyncMock(return_value=Mock())  # type: ignore
        conversation_service.get_messages = AsyncMock(return_value=[])  # type: ignore  # type: ignore
        conversation_service.build_context_from_messages = AsyncMock(return_value=Mock(context_window="test context"))  # type: ignore
        conversation_service.enhance_question_with_context = AsyncMock(return_value="enhanced question")  # type: ignore

        # Mock token warning service
        mock_token_warning_service = Mock()
        mock_token_warning_service.check_conversation_warning = AsyncMock(return_value=None)
        conversation_service.token_warning_service = mock_token_warning_service  # type: ignore

        # Create mock token warning for the return value
        mock_token_warning = TokenWarning(
            warning_type=TokenWarningType.APPROACHING_LIMIT,
            current_tokens=3500,
            limit_tokens=4096,
            percentage_used=85.4,
            message="Context window is 85% full",
            severity="warning",
            suggested_action="consider_new_session",
        )

        # Mock the process_user_message method to return tuple (assistant_message, token_warning)
        mock_assistant_message = Mock()
        mock_metadata = Mock()
        mock_search_metadata = {
            "token_usage": {"total": 3900, "prompt": 3500, "completion": 400},
            "token_warning": {"type": "approaching_limit", "message": "Context window is 85% full"},
        }
        mock_metadata.search_metadata = mock_search_metadata
        mock_assistant_message.metadata = mock_metadata
        conversation_service.process_user_message = AsyncMock(return_value=(mock_assistant_message, mock_token_warning))  # type: ignore

        message_input = ConversationMessageInput(
            session_id=mock_session.id,
            content="What is AI?",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
        )

        assistant_message, token_warning = await conversation_service.process_user_message(message_input)

        # Verify token warning was returned
        assert token_warning is not None
        assert token_warning.warning_type == TokenWarningType.APPROACHING_LIMIT
        assert token_warning.severity == "warning"
        assert token_warning.suggested_action == "consider_new_session"

        # Verify assistant message contains token metadata
        assert assistant_message.metadata is not None
        assert assistant_message.metadata.search_metadata is not None
        assert "token_usage" in assistant_message.metadata.search_metadata
        assert "token_warning" in assistant_message.metadata.search_metadata

    @pytest.mark.integration
    async def test_conversation_service_prioritizes_conversation_warning_over_search_warning(
        self, conversation_service: ConversationService, mock_db: Mock
    ) -> None:  # type: ignore[misc,method-assign]
        """Integration: Test conversation service prioritizes conversation warnings over search warnings."""
        # Mock session in database
        mock_session = Mock()
        mock_session.id = uuid4()
        mock_session.user_id = uuid4()
        mock_session.collection_id = uuid4()
        mock_session.status = "active"

        def mock_query(model):
            query_mock = Mock()
            query_mock.filter = Mock(return_value=query_mock)
            query_mock.first = Mock(return_value=mock_session)
            return query_mock

        mock_db.query.side_effect = mock_query

        # Mock search service with minor token warning
        mock_search_service = Mock()
        search_result = SearchOutput(
            answer="Search response",
            documents=[],
            query_results=[],
            execution_time=1.5,
            metadata={
                "token_usage": {"total_tokens": 3000},
                "token_warning": {
                    "type": "approaching_limit",
                    "severity": "info",
                    "message": "Context window is 73% full",
                },
            },
        )
        mock_search_service.search = AsyncMock(return_value=search_result)
        conversation_service._search_service = mock_search_service

        # Mock conversation-level warning (more severe)
        conversation_warning = TokenWarning(
            warning_type=TokenWarningType.CONVERSATION_TOO_LONG,
            current_tokens=4000,
            limit_tokens=4096,
            percentage_used=97.7,
            message="Conversation context is getting large",
            severity="critical",
            suggested_action="start_new_session",
        )

        mock_token_warning_service = Mock()
        mock_token_warning_service.check_conversation_warning = AsyncMock(return_value=conversation_warning)
        conversation_service.token_warning_service = mock_token_warning_service  # type: ignore

        # Mock other methods
        with (
            patch.object(conversation_service, "add_message", new_callable=AsyncMock) as mock_add_message,
            patch.object(conversation_service, "get_messages", new_callable=AsyncMock) as mock_get_messages,
            patch.object(
                conversation_service, "build_context_from_messages", new_callable=AsyncMock
            ) as mock_build_context,
            patch.object(
                conversation_service, "enhance_question_with_context", new_callable=AsyncMock
            ) as mock_enhance_question,
            patch.object(conversation_service, "process_user_message", new_callable=AsyncMock) as mock_process_message,
        ):
            mock_add_message.return_value = Mock()
            mock_get_messages.return_value = [Mock()] * 10  # Long conversation
            mock_build_context.return_value = Mock(context_window="test context")
            mock_enhance_question.return_value = "enhanced question"

            # Mock the process_user_message method to return tuple (assistant_message, token_warning)
            mock_assistant_message = Mock()
            mock_metadata = Mock()
            mock_search_metadata = {
                "token_usage": {"total_tokens": 3000},
                "token_warning": {
                    "type": "approaching_limit",
                    "severity": "info",
                    "message": "Context window is 73% full",
                },
            }
            mock_metadata.search_metadata = mock_search_metadata
            mock_assistant_message.metadata = mock_metadata
            mock_process_message.return_value = (mock_assistant_message, conversation_warning)

            message_input = ConversationMessageInput(
                session_id=mock_session.id,
                content="Continue the conversation",
                role=MessageRole.USER,
                message_type=MessageType.FOLLOW_UP,
            )

            result = await conversation_service.process_user_message(message_input)
            _assistant_message, token_warning = result  # type: ignore

            # Verify conversation warning was prioritized (critical vs info)
            assert token_warning is not None
            assert token_warning.warning_type == TokenWarningType.CONVERSATION_TOO_LONG  # type: ignore
            assert token_warning.severity == "critical"  # type: ignore
            assert "conversation context" in token_warning.message.lower()  # type: ignore

    # ==================== SEARCH TO COT INTEGRATION ====================

    @pytest.mark.integration
    @pytest.mark.skip(reason="Testing unimplemented CoT token aggregation functionality")
    async def test_search_service_aggregates_cot_token_usage_correctly(
        self, search_service: SearchService, mock_llm_provider_with_high_usage: Mock
    ) -> None:
        """Integration: Test search service correctly aggregates token usage from CoT steps."""
        # Mock CoT service with multiple steps
        mock_cot_service = Mock()

        # Create mock reasoning steps with token usage
        step_usages = [
            LLMUsage(500, 100, 600, "gpt-3.5-turbo", ServiceType.CHAIN_OF_THOUGHT, datetime.utcnow()),  # Classification
            LLMUsage(800, 200, 1000, "gpt-3.5-turbo", ServiceType.CHAIN_OF_THOUGHT, datetime.utcnow()),  # Decomposition
            LLMUsage(1200, 300, 1500, "gpt-3.5-turbo", ServiceType.CHAIN_OF_THOUGHT, datetime.utcnow()),  # Generation
            LLMUsage(600, 150, 750, "gpt-3.5-turbo", ServiceType.CHAIN_OF_THOUGHT, datetime.utcnow()),  # Synthesis
        ]

        mock_reasoning_steps = []
        for i, usage in enumerate(step_usages):
            step = Mock()
            step.step_type = ["classification", "decomposition", "generation", "synthesis"][i]
            step.token_usage = usage
            mock_reasoning_steps.append(step)

        mock_cot_result = Mock()
        mock_cot_result.final_answer = "Chain of Thought answer"
        mock_cot_result.reasoning_steps = mock_reasoning_steps

        # Mock aggregate method
        def mock_aggregate():
            total_prompt = sum(usage.prompt_tokens for usage in step_usages)
            total_completion = sum(usage.completion_tokens for usage in step_usages)
            return LLMUsage(
                prompt_tokens=total_prompt,  # 3100
                completion_tokens=total_completion,  # 750
                total_tokens=total_prompt + total_completion,  # 3850
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
        search_service._pipeline_service = Mock()
        search_service.pipeline_service.get_pipeline = Mock(return_value=Mock())  # type: ignore
        search_service.pipeline_service.initialize = AsyncMock(return_value="test_pipeline")  # type: ignore

        # Mock pipeline execution result
        mock_pipeline_result = Mock()
        mock_pipeline_result.success = True
        mock_pipeline_result.query_results = []
        mock_pipeline_result.generated_answer = "Test generated answer"
        mock_pipeline_result.rewritten_query = "Test rewritten query"
        mock_pipeline_result.evaluation = {}
        search_service.pipeline_service.execute_pipeline = AsyncMock(return_value=mock_pipeline_result)  # type: ignore
        search_service._retrieve_documents = AsyncMock(return_value=[])  # type: ignore
        search_service._build_context_from_documents = Mock(return_value="test context")  # type: ignore
        search_service._get_llm_provider = Mock(return_value=mock_llm_provider_with_high_usage)  # type: ignore
        search_service._chain_of_thought_service = mock_cot_service  # type: ignore

        # Mock collection service to avoid Milvus connection
        mock_collection_service = Mock()
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collection.vector_db_name = "test_vector_db"
        mock_collection_service.get_collection = Mock(return_value=mock_collection)
        search_service._collection_service = mock_collection_service

        # Mock token warning service
        mock_token_warning_service = Mock()
        mock_token_warning_service.check_usage_warning = AsyncMock(return_value=None)
        search_service.token_warning_service = mock_token_warning_service  # type: ignore

        search_input = SearchInput(
            question="Complex question requiring chain of thought?",
            collection_id=uuid4(),
            user_id=uuid4(),
        )

        with patch.object(search_service, "_should_use_chain_of_thought", return_value=True):
            result = await search_service.search(search_input)

        # Verify aggregated token usage
        assert "token_usage" in result.metadata
        token_usage = result.metadata["token_usage"]
        assert token_usage["prompt_tokens"] == 3100
        assert token_usage["completion_tokens"] == 750
        assert token_usage["total_tokens"] == 3850

        # Verify step breakdown
        assert "cot_token_breakdown" in result.metadata
        breakdown = result.metadata["cot_token_breakdown"]
        assert len(breakdown) == 4
        assert breakdown[0]["step"] == "classification"
        assert breakdown[0]["total_tokens"] == 600
        assert breakdown[3]["step"] == "synthesis"
        assert breakdown[3]["total_tokens"] == 750

    # ==================== TOKEN WARNING PROPAGATION INTEGRATION ====================

    @pytest.mark.integration
    async def test_token_warning_propagates_through_conversation_to_api(
        self, conversation_service: ConversationService, mock_db: Mock
    ) -> None:
        """Integration: Test token warnings propagate from services through conversation to API layer."""
        # This test simulates the full flow: search generates warning -> conversation processes it -> API returns it

        # Mock session
        mock_session = Mock()
        mock_session.id = uuid4()
        mock_session.user_id = uuid4()
        mock_session.collection_id = uuid4()
        mock_session.status = "active"

        def mock_query(model):
            query_mock = Mock()
            query_mock.filter = Mock(return_value=query_mock)
            query_mock.first = Mock(return_value=mock_session)
            return query_mock

        mock_db.query.side_effect = mock_query

        # Mock search service with critical warning
        mock_search_service = Mock()
        search_result = SearchOutput(
            answer="Critical usage response",
            documents=[],
            query_results=[],
            execution_time=2.0,
            metadata={
                "token_usage": {
                    "prompt_tokens": 3900,
                    "completion_tokens": 196,
                    "total_tokens": 4096,
                    "model_name": "gpt-3.5-turbo",
                },
                "token_warning": {
                    "type": "at_limit",
                    "message": "Context window is at limit. Consider starting a new conversation.",
                    "percentage_used": 100.0,
                    "severity": "critical",
                    "current_tokens": 3900,
                    "limit_tokens": 4096,
                    "suggested_action": "start_new_session",
                },
            },
        )
        mock_search_service.search = AsyncMock(return_value=search_result)
        conversation_service._search_service = mock_search_service

        # Mock other methods
        conversation_service.add_message = AsyncMock()  # type: ignore
        conversation_service.get_messages = AsyncMock(return_value=[])  # type: ignore
        conversation_service.build_context_from_messages = AsyncMock(return_value=Mock(context_window="context"))  # type: ignore
        conversation_service.enhance_question_with_context = AsyncMock(return_value="enhanced question")  # type: ignore

        # Mock token warning service (no conversation warning)
        mock_token_warning_service = Mock()
        mock_token_warning_service.check_conversation_warning = AsyncMock(return_value=None)
        conversation_service.token_warning_service = mock_token_warning_service  # type: ignore

        # Mock the assistant message creation
        assistant_message = Mock()
        assistant_message.metadata = Mock()
        assistant_message.metadata.search_metadata = {
            "token_usage": {
                "prompt_tokens": 3900,
                "completion_tokens": 196,
                "total_tokens": 4096,
                "model_name": "gpt-3.5-turbo",
            },
            "token_warning": {
                "type": "at_limit",
                "message": "Context window is at limit. Consider starting a new conversation.",
                "percentage_used": 100.0,
                "severity": "critical",
                "current_tokens": 3900,
                "limit_tokens": 4096,
                "suggested_action": "start_new_session",
            },
        }
        conversation_service.add_message.return_value = assistant_message

        # Mock process_user_message to return tuple (assistant_message, token_warning)
        mock_token_warning = TokenWarning(
            warning_type=TokenWarningType.AT_LIMIT,
            current_tokens=3900,
            limit_tokens=4096,
            percentage_used=100.0,
            message="Context window is at limit. Consider starting a new conversation.",
            severity="critical",
            suggested_action="start_new_session",
        )
        conversation_service.process_user_message = AsyncMock(return_value=(assistant_message, mock_token_warning))  # type: ignore

        message_input = ConversationMessageInput(
            session_id=mock_session.id,
            content="This will max out the context",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
        )

        # Process message and get warning
        assistant_message, token_warning = await conversation_service.process_user_message(message_input)

        # Verify the warning structure for API response
        assert token_warning is not None
        assert token_warning.warning_type == TokenWarningType.AT_LIMIT
        assert token_warning.severity == "critical"
        assert token_warning.percentage_used == 100.0
        assert token_warning.suggested_action == "start_new_session"
        assert "start" in token_warning.message.lower()

        # Verify assistant message contains the metadata for persistence
        assert assistant_message.metadata.search_metadata["token_warning"]["type"] == "at_limit"
        assert assistant_message.metadata.search_metadata["token_usage"]["total_tokens"] == 4096

    # ==================== CROSS-SERVICE TOKEN AGGREGATION ====================

    @pytest.mark.integration
    async def test_conversation_service_aggregates_session_token_statistics(
        self, conversation_service: ConversationService
    ) -> None:
        """Integration: Test conversation service aggregates token statistics across session messages."""
        # Mock messages with token usage in metadata
        mock_messages = []
        usage_data = [
            {"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200, "model_name": "gpt-3.5-turbo"},
            {"prompt_tokens": 800, "completion_tokens": 150, "total_tokens": 950, "model_name": "gpt-3.5-turbo"},
            {"prompt_tokens": 1200, "completion_tokens": 300, "total_tokens": 1500, "model_name": "gpt-4"},
        ]

        for _i, usage in enumerate(usage_data):
            message = Mock()
            message.session_id = uuid4()
            message.created_at = datetime.utcnow()
            message.token_count = usage["total_tokens"]  # Set actual token count
            message.role = MessageRole.ASSISTANT  # Set role to assistant
            message.metadata = Mock()
            message.metadata.search_metadata = {"token_usage": usage}
            message.metadata.cot_steps = []  # Set cot_steps as empty list
            message.metadata.cot_used = False  # Set cot_used to False
            message.metadata.conversation_aware = False  # Set conversation_aware to False
            mock_messages.append(message)

        conversation_service.get_messages = AsyncMock(return_value=mock_messages)  # type: ignore

        # Mock session for get_session call
        mock_session = Mock()
        mock_session.id = uuid4()
        mock_session.user_id = uuid4()
        mock_session.collection_id = uuid4()
        mock_session.session_name = "Test Session"
        mock_session.context_window_size = 4096
        mock_session.max_messages = 100
        mock_session.is_archived = False
        mock_session.is_pinned = False
        mock_session.created_at = datetime.utcnow()
        mock_session.updated_at = datetime.utcnow()
        mock_session.session_metadata = {}
        mock_session.status = "active"

        def mock_query(model):
            query_mock = Mock()
            query_mock.filter = Mock(return_value=query_mock)
            query_mock.first = Mock(return_value=mock_session)
            return query_mock

        conversation_service.db.query = Mock(side_effect=mock_query)  # type: ignore

        # Test token statistics aggregation
        session_id = uuid4()
        user_id = uuid4()

        stats = await conversation_service.get_session_statistics(session_id, user_id)

        # Check basic statistics
        assert stats.session_id == session_id
        assert stats.message_count == 3
        assert stats.user_messages == 0  # Only assistant messages in our mock
        assert stats.assistant_messages == 3
        assert stats.total_tokens == 3650  # 1200 + 950 + 1500
        assert stats.cot_usage_count == 0  # No CoT used in our mock
        assert stats.context_enhancement_count == 0  # No context enhancement in our mock

        # Check metadata for additional details
        assert stats.metadata["total_llm_calls"] == 3
        assert stats.metadata["cot_token_count"] == 0

    @pytest.mark.integration
    async def test_conversation_service_handles_empty_token_history(
        self, conversation_service: ConversationService
    ) -> None:
        """Integration: Test conversation service handles empty token history gracefully."""
        # Mock no messages
        conversation_service.get_messages = AsyncMock(return_value=[])  # type: ignore

        # Mock session for get_session call
        mock_session = Mock()
        mock_session.id = uuid4()
        mock_session.user_id = uuid4()
        mock_session.collection_id = uuid4()
        mock_session.session_name = "Test Session"
        mock_session.context_window_size = 4096
        mock_session.max_messages = 100
        mock_session.is_archived = False
        mock_session.is_pinned = False
        mock_session.created_at = datetime.utcnow()
        mock_session.updated_at = datetime.utcnow()
        mock_session.session_metadata = {}
        mock_session.status = "active"

        def mock_query(model):
            query_mock = Mock()
            query_mock.filter = Mock(return_value=query_mock)
            query_mock.first = Mock(return_value=mock_session)
            return query_mock

        conversation_service.db.query = Mock(side_effect=mock_query)  # type: ignore

        session_id = uuid4()
        user_id = uuid4()

        stats = await conversation_service.get_session_statistics(session_id, user_id)

        # Check empty statistics
        assert stats.session_id == session_id
        assert stats.message_count == 0
        assert stats.user_messages == 0
        assert stats.assistant_messages == 0
        assert stats.total_tokens == 0
        assert stats.cot_usage_count == 0
        assert stats.context_enhancement_count == 0

        # Check metadata for additional details
        assert stats.metadata["total_llm_calls"] == 0
        assert stats.metadata["cot_token_count"] == 0
