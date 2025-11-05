"""Integration tests for MessageProcessingOrchestrator.

Tests the full message processing workflow with real services and database.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from uuid import uuid4

from rag_solution.schemas.conversation_schema import (
    ConversationMessageInput,
    ConversationMessageOutput,
    MessageRole,
    MessageType,
)
from rag_solution.schemas.search_schema import SearchOutput
from rag_solution.services.message_processing_orchestrator import MessageProcessingOrchestrator


@pytest.mark.integration
class TestMessageProcessingIntegration:
    """Integration tests for MessageProcessingOrchestrator."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.temperature = 0.7
        return settings

    @pytest.fixture
    def mock_repository(self):
        """Create a mock conversation repository."""
        repository = Mock()

        # Mock create_message to return ConversationMessageOutput with metadata
        def create_message_mock(message_input):
            # Convert metadata dict to MessageMetadata if present
            metadata_value = None
            if message_input.metadata:
                if isinstance(message_input.metadata, dict):
                    from rag_solution.schemas.conversation_schema import MessageMetadata
                    try:
                        metadata_value = MessageMetadata(**message_input.metadata)
                    except (ValueError, KeyError, AttributeError):
                        metadata_value = None
                else:
                    metadata_value = message_input.metadata
            
            # Extract sources, cot_output, token_analysis from metadata dict
            sources = None
            cot_output = None
            token_analysis = None
            if isinstance(message_input.metadata, dict):
                sources = message_input.metadata.get("sources")
                cot_output = message_input.metadata.get("cot_output")
                token_analysis = message_input.metadata.get("token_analysis")
            
            return ConversationMessageOutput(
                id=uuid4(),
                session_id=message_input.session_id,
                content=message_input.content,
                role=message_input.role,
                message_type=message_input.message_type,
                token_count=message_input.token_count,
                execution_time=message_input.execution_time,
                metadata=metadata_value,
                sources=sources,
                cot_output=cot_output,
                token_analysis=token_analysis,
            )

        repository.create_message = Mock(side_effect=create_message_mock)
        repository.get_messages_by_session = Mock(return_value=[])
        return repository

    @pytest.fixture
    def mock_search_service(self):
        """Create a mock search service."""
        service = Mock()

        # Mock search method as async
        async def search_mock(search_input):
            return SearchOutput(
                answer="Test answer from search",
                documents=[],
                query_results=[],
                metadata={"cot_used": False},
                execution_time=0.5,
            )

        service.search = AsyncMock(side_effect=search_mock)
        return service

    @pytest.fixture
    def mock_context_service(self):
        """Create a mock conversation context service."""
        service = Mock()

        # Mock build_context_from_messages as async
        from rag_solution.schemas.conversation_schema import ConversationContext, ContextMetadata

        async def build_context_mock(session_id, messages):
            return ConversationContext(
                session_id=session_id,
                context_window="Test context window",
                relevant_documents=[],
                metadata=ContextMetadata(
                    extracted_entities=[],
                    conversation_topics=[],
                    message_count=len(messages),
                    context_length=100,
                ),
            )

        service.build_context_from_messages = AsyncMock(side_effect=build_context_mock)

        # Mock enhance_question_with_context as async
        async def enhance_question_mock(question, context, history, cached_entities=None):
            return question  # Return original question (stub implementation)

        service.enhance_question_with_context = AsyncMock(side_effect=enhance_question_mock)
        return service

    @pytest.fixture
    def mock_token_tracking_service(self):
        """Create a mock token tracking service."""
        service = Mock()

        # Mock check_usage_warning as async
        async def check_usage_warning_mock(current_usage, context_tokens):
            return None  # No warning

        service.check_usage_warning = AsyncMock(side_effect=check_usage_warning_mock)
        return service

    @pytest.fixture
    def mock_llm_provider_service(self):
        """Create a mock LLM provider service."""
        service = Mock()
        provider = Mock()
        provider.model_id = "test-model"

        # Mock client with tokenize method
        # The code accesses provider.client.tokenize() so we need to mock the client
        provider_client = Mock()
        provider_client.tokenize = Mock(return_value={"result": [1, 2, 3, 4, 5]})  # 5 tokens
        provider.client = provider_client

        service.get_user_provider = Mock(return_value=provider)
        return service

    @pytest.fixture
    def orchestrator(
        self,
        mock_db_session,
        mock_settings,
        mock_repository,
        mock_search_service,
        mock_context_service,
        mock_token_tracking_service,
        mock_llm_provider_service,
    ):
        """Create MessageProcessingOrchestrator with mocked dependencies."""
        # Mock the session query
        session_mock = Mock()
        session_mock.id = uuid4()
        session_mock.user_id = uuid4()
        session_mock.collection_id = uuid4()
        session_mock.status = "active"

        mock_db_session.query = Mock(
            return_value=Mock(
                filter=Mock(
                    return_value=Mock(
                        first=Mock(return_value=session_mock)
                    )
                )
            )
        )

        return MessageProcessingOrchestrator(
            db=mock_db_session,
            settings=mock_settings,
            conversation_repository=mock_repository,
            search_service=mock_search_service,
            context_service=mock_context_service,
            token_tracking_service=mock_token_tracking_service,
            llm_provider_service=mock_llm_provider_service,
            chain_of_thought_service=None,  # CoT is optional
        )

    @pytest.mark.asyncio
    async def test_process_user_message_full_workflow(self, orchestrator):
        """Test complete message processing workflow."""
        # Arrange
        session_id = uuid4()
        message_input = ConversationMessageInput(
            session_id=session_id,
            content="What is machine learning?",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
        )

        # Act
        result = await orchestrator.process_user_message(message_input)

        # Assert
        assert result is not None
        assert isinstance(result, ConversationMessageOutput)
        assert result.content == "Test answer from search"
        assert result.role == MessageRole.ASSISTANT
        assert result.message_type == MessageType.ANSWER
        assert result.token_count > 0
        assert result.metadata is not None

    @pytest.mark.asyncio
    async def test_process_user_message_validates_session(self, orchestrator, mock_db_session):
        """Test that process_user_message validates session exists."""
        # Arrange: Mock session not found
        mock_db_session.query = Mock(
            return_value=Mock(
                filter=Mock(
                    return_value=Mock(
                        first=Mock(return_value=None)  # Session not found
                    )
                )
            )
        )

        message_input = ConversationMessageInput(
            session_id=uuid4(),
            content="Test question",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Session not found"):
            await orchestrator.process_user_message(message_input)

    @pytest.mark.asyncio
    async def test_coordinate_search_with_context(
        self, orchestrator, mock_search_service, mock_context_service
    ):
        """Test search coordination with conversation context."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        collection_id = uuid4()

        from rag_solution.schemas.conversation_schema import ConversationContext, ContextMetadata

        context = ConversationContext(
            session_id=session_id,
            context_window="Previous context",
            relevant_documents=[],
            metadata=ContextMetadata(
                extracted_entities=["IBM", "Watson"],
                conversation_topics=["AI"],
                message_count=5,
                context_length=100,
            ),
        )

        # Act
        search_result = await orchestrator._coordinate_search(
            enhanced_question="Tell me about IBM Watson",
            session_id=session_id,
            collection_id=collection_id,
            user_id=user_id,
            context=context,
            messages=[],
        )

        # Assert
        assert search_result is not None
        assert search_result.answer == "Test answer from search"
        mock_search_service.search.assert_called_once()

        # Verify search input contained conversation context
        call_args = mock_search_service.search.call_args
        search_input = call_args[0][0]  # First positional argument
        assert search_input.config_metadata["conversation_context"] == "Previous context"
        assert "IBM" in search_input.config_metadata["conversation_entities"]
        assert "Watson" in search_input.config_metadata["conversation_entities"]

    @pytest.mark.asyncio
    async def test_serialize_response_with_sources(self, orchestrator):
        """Test response serialization with DocumentMetadata."""
        # Arrange
        from rag_solution.schemas.search_schema import SearchOutput
        from vectordbs.data_types import DocumentMetadata

        # Create proper DocumentMetadata object
        mock_doc = DocumentMetadata(
            document_name="Test Document",
            content="Test content",
        )

        search_result = SearchOutput(
            answer="Test answer",
            documents=[mock_doc],
            query_results=[],
            metadata={"cot_used": False},
            execution_time=0.5,
        )

        from rag_solution.schemas.conversation_schema import ConversationContext, ContextMetadata

        context = ConversationContext(
            session_id=uuid4(),
            context_window="Test context",
            relevant_documents=[],
            metadata=ContextMetadata(),
        )

        # Mock repository.get_messages_by_session to return empty list for conversation_total calculation
        orchestrator.repository.get_messages_by_session = Mock(return_value=[])

        # Act
        metadata_dict, token_count = await orchestrator._serialize_response(
            search_result=search_result,
            user_token_count=50,
            user_id=uuid4(),
            session_id=uuid4(),
            context=context,
        )

        # Assert
        assert metadata_dict is not None
        assert token_count > 0
        assert "sources" in metadata_dict
        assert "token_analysis" in metadata_dict
        assert metadata_dict["token_analysis"]["query_tokens"] == 50
        assert metadata_dict["sources"] is not None
        assert len(metadata_dict["sources"]) == 1
        assert metadata_dict["sources"][0]["document_name"] == "Test Document"

    @pytest.mark.asyncio
    async def test_metadata_includes_token_analysis(self, orchestrator):
        """Test that metadata includes comprehensive token analysis."""
        # Arrange
        session_id = uuid4()
        message_input = ConversationMessageInput(
            session_id=session_id,
            content="What is AI?",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
        )

        # Act
        result = await orchestrator.process_user_message(message_input)

        # Assert
        assert result.metadata is not None
        metadata_dict = result.metadata.model_dump()
        assert "token_analysis" in metadata_dict
        token_analysis = metadata_dict["token_analysis"]
        assert "query_tokens" in token_analysis
        assert "response_tokens" in token_analysis
        assert "system_tokens" in token_analysis
        assert "total_this_turn" in token_analysis
        assert "conversation_total" in token_analysis
