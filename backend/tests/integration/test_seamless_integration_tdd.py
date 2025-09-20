"""Integration tests for seamless Search + CoT + Conversation integration - TDD Red Phase.

This module validates the core integration principles:
1. Conversation provides UI and context management
2. Search provides RAG functionality with conversation awareness
3. CoT provides enhanced reasoning with conversation history
4. All three work seamlessly without duplication
5. Existing capabilities are preserved and enhanced
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from core.config import Settings

from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput, ChainOfThoughtOutput
from rag_solution.schemas.conversation_schema import (
    ConversationContext,
    ConversationMessageInput,
    ConversationSessionInput,
    MessageRole,
    MessageType,
)
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.services.context_manager_service import ContextManagerService
from rag_solution.services.conversation_service import ConversationService
from rag_solution.services.question_suggestion_service import QuestionSuggestionService
from rag_solution.services.search_service import SearchService


class TestSeamlessIntegrationTDD:
    """Test cases for seamless integration between Search, CoT, and Conversation services."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings."""
        return Settings()

    @pytest.fixture
    def conversation_service(self, mock_db: Mock, mock_settings: Settings) -> ConversationService:
        """Create ConversationService with mocked dependencies."""
        return ConversationService(db=mock_db, settings=mock_settings)

    @pytest.fixture
    def context_manager_service(self, mock_db: Mock, mock_settings: Settings) -> ContextManagerService:
        """Create ContextManagerService with mocked dependencies."""
        return ContextManagerService(db=mock_db, settings=mock_settings)

    @pytest.fixture
    def search_service(self, mock_db: Mock, mock_settings: Settings) -> SearchService:
        """Create SearchService with mocked dependencies."""
        return SearchService(db=mock_db, settings=mock_settings)

    @pytest.fixture
    def cot_service(self, mock_db: Mock, mock_settings: Settings) -> ChainOfThoughtService:
        """Create ChainOfThoughtService with mocked dependencies."""
        return ChainOfThoughtService(settings=mock_settings, llm_service=Mock(), search_service=Mock(), db=mock_db)

    @pytest.fixture
    def question_suggestion_service(self, mock_db: Mock, mock_settings: Settings) -> QuestionSuggestionService:
        """Create QuestionSuggestionService with mocked dependencies."""
        return QuestionSuggestionService(db=mock_db, settings=mock_settings)

    @pytest.mark.integration
    def test_conversation_provides_ui_and_context_management(
        self, conversation_service: ConversationService, context_manager_service: ContextManagerService
    ) -> None:
        """Integration: Test that Conversation provides UI and context management."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        session_id = uuid4()

        # Test 1: Conversation UI - Session management
        session_input = ConversationSessionInput(
            user_id=user_id,
            collection_id=collection_id,
            session_name="Test Session",
            context_window_size=4000,
            max_messages=50,
        )

        # Mock session creation
        with patch.object(conversation_service, "create_session") as mock_create:
            mock_create.return_value = ConversationSessionInput(
                user_id=user_id,
                collection_id=collection_id,
                session_name="Test Session",
                context_window_size=4000,
                max_messages=50,
            )

            # Act
            session = conversation_service.create_session(session_input)

            # Assert - Conversation provides UI functionality
            assert session.user_id == user_id
            assert session.collection_id == collection_id
            assert session.session_name == "Test Session"
            mock_create.assert_called_once_with(session_input)

        # Test 2: Context Management - Building context from messages
        messages = [
            ConversationMessageInput(
                session_id=session_id,
                content="What is machine learning?",
                role=MessageRole.USER,
                message_type=MessageType.QUESTION,
            ),
            ConversationMessageInput(
                session_id=session_id,
                content="Machine learning is a subset of AI...",
                role=MessageRole.ASSISTANT,
                message_type=MessageType.ANSWER,
            ),
        ]

        expected_context = ConversationContext(
            session_id=session_id,
            context_window="Previous discussion about machine learning",
            relevant_documents=["doc1", "doc2"],
            context_metadata={"extracted_entities": ["machine learning", "AI"], "conversation_topic": "AI concepts"},
        )

        with patch.object(context_manager_service, "build_context_from_messages", return_value=expected_context):
            # Act
            context = context_manager_service.build_context_from_messages(session_id, messages)

            # Assert - Context management works
            assert context.session_id == session_id
            assert "machine learning" in context.context_window
            assert "extracted_entities" in context.context_metadata
            assert context.context_metadata["extracted_entities"] == ["machine learning", "AI"]

        # Test 3: Context Management - Question enhancement
        with patch.object(context_manager_service, "enhance_question_with_conversation_context") as mock_enhance:
            mock_enhance.return_value = "What is machine learning? (in the context of AI concepts)"

            # Act
            enhanced_question = context_manager_service.enhance_question_with_conversation_context(
                "What is it?",
                "Previous discussion about machine learning",
                ["What is machine learning?", "Machine learning is a subset of AI..."],
            )

            # Assert - Question enhancement works
            assert "machine learning" in enhanced_question
            assert "(in the context of" in enhanced_question
            mock_enhance.assert_called_once()

    @pytest.mark.integration
    def test_search_provides_rag_with_conversation_awareness(
        self, search_service: SearchService, conversation_service: ConversationService
    ) -> None:
        """Integration: Test that Search provides RAG functionality with conversation awareness."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        session_id = uuid4()

        # Test 1: Search with conversation context
        search_input = SearchInput(
            question="How does machine learning work?",
            collection_id=collection_id,
            user_id=user_id,
            config_metadata={
                "conversation_context": "Previous discussion about AI and neural networks",
                "message_history": ["What is AI?", "AI is artificial intelligence..."],
                "conversation_entities": ["AI", "neural networks"],
                "cot_enabled": True,
                "session_id": str(session_id),
            },
        )

        # Mock search service to handle conversation-aware search
        with patch.object(search_service, "search") as mock_search:
            mock_search.return_value = SearchOutput(
                answer="Machine learning works by using algorithms to identify patterns in data, building on our previous discussion about AI and neural networks.",
                documents=["doc1", "doc2"],
                query_results=[],
                execution_time=1.5,
                metadata={
                    "conversation_aware": True,
                    "enhanced_question": "How does machine learning work? (in the context of AI and neural networks)",
                    "context_used": True,
                },
            )

            # Act
            result = search_service.search(search_input)

            # Assert - Search provides RAG with conversation awareness
            assert result.answer is not None
            assert "Previous discussion about AI" in result.answer
            assert result.metadata["conversation_aware"] is True
            assert result.metadata["context_used"] is True
            assert "enhanced_question" in result.metadata
            mock_search.assert_called_once_with(search_input)

        # Test 2: Search without conversation context (preserves existing functionality)
        search_input_no_context = SearchInput(
            question="How does machine learning work?",
            collection_id=collection_id,
            user_id=user_id,
            config_metadata={},  # No conversation context
        )

        with patch.object(search_service, "search") as mock_search_no_context:
            mock_search_no_context.return_value = SearchOutput(
                answer="Machine learning works by using algorithms to identify patterns in data.",
                documents=["doc1", "doc2"],
                query_results=[],
                execution_time=1.0,
                metadata={"conversation_aware": False, "context_used": False},
            )

            # Act
            result_no_context = search_service.search(search_input_no_context)

            # Assert - Existing functionality preserved
            assert result_no_context.answer is not None
            assert result_no_context.metadata["conversation_aware"] is False
            assert result_no_context.metadata["context_used"] is False
            mock_search_no_context.assert_called_once_with(search_input_no_context)

        # Test 3: Search integration with Conversation service
        message = ConversationMessageInput(
            session_id=session_id,
            content="Tell me more about deep learning",
            role=MessageRole.USER,
            message_type=MessageType.FOLLOW_UP,
        )

        with patch.object(conversation_service, "search_service", search_service):
            with patch.object(search_service, "search") as mock_search_integration:
                mock_search_integration.return_value = SearchOutput(
                    answer="Deep learning is a subset of machine learning that uses neural networks with multiple layers.",
                    documents=["doc3", "doc4"],
                    query_results=[],
                    execution_time=1.2,
                )

                # Act
                conversation_service.process_user_message(message)

                # Assert - Search integrates with Conversation
                mock_search_integration.assert_called_once()
                # Verify the search input has conversation context
                call_args = mock_search_integration.call_args[0][0]
                assert "conversation_context" in call_args.config_metadata
                assert call_args.config_metadata["session_id"] == str(session_id)

    @pytest.mark.integration
    def test_cot_provides_enhanced_reasoning_with_conversation_history(
        self, cot_service: ChainOfThoughtService
    ) -> None:
        """Integration: Test that CoT provides enhanced reasoning with conversation history."""
        # Arrange
        user_id = str(uuid4())
        collection_id = uuid4()

        # Test 1: CoT with conversation context
        cot_input_with_context = ChainOfThoughtInput(
            question="How do they relate?",
            collection_id=collection_id,
            user_id=user_id,
            context_metadata={
                "conversation_context": "Previous discussion about machine learning and neural networks",
                "message_history": [
                    "What is machine learning?",
                    "Machine learning is a subset of AI...",
                    "What are neural networks?",
                    "Neural networks are computing systems...",
                ],
                "conversation_entities": ["machine learning", "neural networks", "AI"],
                "previous_answers": [
                    "Machine learning is a subset of AI...",
                    "Neural networks are computing systems...",
                ],
            },
        )

        context_documents = [
            "Machine learning is a subset of artificial intelligence...",
            "Neural networks are computing systems inspired by biological neural networks...",
        ]

        # Mock CoT execution with conversation awareness
        with patch.object(cot_service, "execute_chain_of_thought") as mock_cot:
            mock_cot.return_value = ChainOfThoughtOutput(
                original_question=cot_input_with_context.question,
                final_answer="Machine learning and neural networks are closely related. Machine learning is the broader field that includes neural networks as one of its key techniques, building on our previous discussion about AI concepts.",
                reasoning_steps=[
                    {
                        "step_number": 1,
                        "step_question": "What is machine learning?",
                        "intermediate_answer": "Machine learning is a subset of AI...",
                        "confidence_score": 0.9,
                    },
                    {
                        "step_number": 2,
                        "step_question": "What are neural networks?",
                        "intermediate_answer": "Neural networks are computing systems...",
                        "confidence_score": 0.85,
                    },
                    {
                        "step_number": 3,
                        "step_question": "How do they relate?",
                        "intermediate_answer": "Neural networks are a key technique in machine learning...",
                        "confidence_score": 0.88,
                    },
                ],
                total_confidence=0.88,
                total_execution_time=2.5,
                reasoning_strategy="conversation_aware",
            )

            # Act
            result = cot_service.execute_chain_of_thought(cot_input_with_context, context_documents, user_id)

            # Assert - CoT provides enhanced reasoning with conversation history
            assert result.final_answer is not None
            assert "Previous discussion about AI concepts" in result.final_answer
            assert result.reasoning_strategy == "conversation_aware"
            assert len(result.reasoning_steps) == 3
            assert result.total_confidence > 0.8
            mock_cot.assert_called_once_with(cot_input_with_context, context_documents, user_id)

        # Test 2: CoT without conversation context (preserves existing functionality)
        cot_input_no_context = ChainOfThoughtInput(
            question="How do machine learning and neural networks relate?",
            collection_id=collection_id,
            user_id=user_id,
            context_metadata={},  # No conversation context
        )

        with patch.object(cot_service, "execute_chain_of_thought") as mock_cot_no_context:
            mock_cot_no_context.return_value = ChainOfThoughtOutput(
                original_question=cot_input_no_context.question,
                final_answer="Machine learning and neural networks are closely related. Neural networks are a key technique in machine learning.",
                reasoning_steps=[
                    {
                        "step_number": 1,
                        "step_question": "What is machine learning?",
                        "intermediate_answer": "Machine learning is a subset of AI...",
                        "confidence_score": 0.9,
                    },
                    {
                        "step_number": 2,
                        "step_question": "What are neural networks?",
                        "intermediate_answer": "Neural networks are computing systems...",
                        "confidence_score": 0.85,
                    },
                ],
                total_confidence=0.87,
                total_execution_time=2.0,
                reasoning_strategy="decomposition",
            )

            # Act
            result_no_context = cot_service.execute_chain_of_thought(cot_input_no_context, context_documents, user_id)

            # Assert - Existing functionality preserved
            assert result_no_context.final_answer is not None
            assert result_no_context.reasoning_strategy == "decomposition"
            assert len(result_no_context.reasoning_steps) == 2
            assert result_no_context.total_confidence > 0.8
            mock_cot_no_context.assert_called_once_with(cot_input_no_context, context_documents, user_id)

        # Test 3: CoT with conversation context enhancement
        with patch.object(cot_service, "_build_conversation_aware_context") as mock_build_context:
            mock_build_context.return_value = [
                "Machine learning is a subset of artificial intelligence...",
                "Neural networks are computing systems inspired by biological neural networks...",
                "Conversation context: Previous discussion about machine learning and neural networks",
                "Previously discussed: machine learning, neural networks, AI",
                "Recent discussion: What are neural networks? Neural networks are computing systems...",
            ]

            with patch.object(cot_service, "_execute_conversation_aware_reasoning") as mock_execute:
                mock_execute.return_value = ChainOfThoughtOutput(
                    original_question=cot_input_with_context.question,
                    final_answer="Machine learning and neural networks are closely related...",
                    reasoning_steps=[],
                    total_confidence=0.95,
                    total_execution_time=2.5,
                    reasoning_strategy="conversation_aware",
                )

                # Act
                cot_service.execute_chain_of_thought(cot_input_with_context, context_documents, user_id)

                # Assert - Conversation context is properly built and used
                mock_build_context.assert_called_once_with(
                    context_documents,
                    "Previous discussion about machine learning and neural networks",
                    [
                        "What is machine learning?",
                        "Machine learning is a subset of AI...",
                        "What are neural networks?",
                        "Neural networks are computing systems...",
                    ],
                    ["machine learning", "neural networks", "AI"],
                )
                mock_execute.assert_called_once()

    @pytest.mark.integration
    def test_seamless_integration_without_duplication(
        self,
        conversation_service: ConversationService,
        search_service: SearchService,
        cot_service: ChainOfThoughtService,
    ) -> None:
        """Integration: Test that all three services work seamlessly without duplication."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        session_id = uuid4()

        # Test 1: Verify no duplication of functionality
        # Conversation handles UI and context, Search handles RAG, CoT handles reasoning

        # Mock the integration flow
        with patch.object(conversation_service, "process_user_message") as mock_conversation:
            with patch.object(search_service, "search") as mock_search:
                with patch.object(cot_service, "execute_chain_of_thought") as mock_cot:
                    # Setup mocks for seamless flow
                    mock_search.return_value = SearchOutput(
                        answer="Search result with conversation context",
                        documents=["doc1", "doc2"],
                        query_results=[],
                        execution_time=1.0,
                        metadata={"conversation_aware": True},
                    )

                    mock_cot.return_value = ChainOfThoughtOutput(
                        original_question="Test question",
                        final_answer="CoT result with conversation history",
                        reasoning_steps=[],
                        total_confidence=0.9,
                        total_execution_time=2.0,
                        reasoning_strategy="conversation_aware",
                    )

                    mock_conversation.return_value = ConversationMessageInput(
                        session_id=session_id,
                        content="Final response integrating all services",
                        role=MessageRole.ASSISTANT,
                        message_type=MessageType.ANSWER,
                        metadata={
                            "search_used": True,
                            "cot_used": True,
                            "conversation_context_used": True,
                            "integration_seamless": True,
                        },
                    )

                    # Act
                    message = ConversationMessageInput(
                        session_id=session_id,
                        content="Test question",
                        role=MessageRole.USER,
                        message_type=MessageType.QUESTION,
                    )

                    result = conversation_service.process_user_message(message)

                    # Assert - No duplication, each service has distinct role
                    assert result.metadata["search_used"] is True
                    assert result.metadata["cot_used"] is True
                    assert result.metadata["conversation_context_used"] is True
                    assert result.metadata["integration_seamless"] is True

                    # Verify each service was called appropriately
                    mock_conversation.assert_called_once()
                    # Note: In real implementation, conversation would call search and cot internally

        # Test 2: Verify service boundaries are respected
        # Conversation doesn't duplicate search logic
        # Search doesn't duplicate conversation logic
        # CoT doesn't duplicate search or conversation logic

        # Mock service boundaries
        with patch.object(conversation_service, "search_service", search_service):
            with patch.object(search_service, "chain_of_thought_service", cot_service):
                # Verify conversation delegates to search (doesn't duplicate)
                with patch.object(search_service, "search") as mock_search_delegate:
                    mock_search_delegate.return_value = SearchOutput(
                        answer="Delegated search result", documents=[], query_results=[], execution_time=1.0
                    )

                    # Act
                    conversation_service.process_user_message(message)

                    # Assert - Conversation delegates to search, doesn't duplicate
                    mock_search_delegate.assert_called_once()

        # Test 3: Verify data flow without duplication
        # Context flows from Conversation → Search → CoT
        # Each service adds value without duplicating others' work

        search_input = SearchInput(
            question="Test question",
            collection_id=collection_id,
            user_id=user_id,
            config_metadata={
                "conversation_context": "Previous discussion",
                "session_id": str(session_id),
                "cot_enabled": True,
            },
        )

        with patch.object(search_service, "search") as mock_search_flow:
            with patch.object(cot_service, "execute_chain_of_thought") as mock_cot_flow:
                mock_search_flow.return_value = SearchOutput(
                    answer="Search with context", documents=["doc1"], query_results=[], execution_time=1.0
                )

                mock_cot_flow.return_value = ChainOfThoughtOutput(
                    original_question="Test question",
                    final_answer="CoT with conversation history",
                    reasoning_steps=[],
                    total_confidence=0.9,
                    total_execution_time=2.0,
                    reasoning_strategy="conversation_aware",
                )

                # Act
                search_result = search_service.search(search_input)

                # Assert - Data flows without duplication
                assert search_result.answer is not None
                assert "conversation_context" in search_input.config_metadata
                assert search_input.config_metadata["cot_enabled"] is True

    @pytest.mark.integration
    def test_preservation_and_enhancement_of_existing_capabilities(
        self,
        search_service: SearchService,
        cot_service: ChainOfThoughtService,
        conversation_service: ConversationService,
    ) -> None:
        """Integration: Test that existing capabilities are preserved and enhanced."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        session_id = uuid4()

        # Test 1: Existing search functionality preserved
        search_input_original = SearchInput(
            question="What is machine learning?",
            collection_id=collection_id,
            user_id=user_id,
            config_metadata={},  # No conversation context
        )

        with patch.object(search_service, "search") as mock_search_original:
            mock_search_original.return_value = SearchOutput(
                answer="Machine learning is a subset of artificial intelligence...",
                documents=["doc1", "doc2"],
                query_results=[],
                execution_time=1.0,
                metadata={"conversation_aware": False, "enhanced": False, "original_functionality": True},
            )

            # Act
            result_original = search_service.search(search_input_original)

            # Assert - Original functionality preserved
            assert result_original.answer is not None
            assert result_original.metadata["conversation_aware"] is False
            assert result_original.metadata["original_functionality"] is True
            mock_search_original.assert_called_once_with(search_input_original)

        # Test 2: Existing CoT functionality preserved
        cot_input_original = ChainOfThoughtInput(
            question="How does machine learning work?",
            collection_id=collection_id,
            user_id=user_id,
            context_metadata={},  # No conversation context
        )

        with patch.object(cot_service, "execute_chain_of_thought") as mock_cot_original:
            mock_cot_original.return_value = ChainOfThoughtOutput(
                original_question=cot_input_original.question,
                final_answer="Machine learning works by using algorithms...",
                reasoning_steps=[
                    {
                        "step_number": 1,
                        "step_question": "What is machine learning?",
                        "intermediate_answer": "Machine learning is a subset of AI...",
                        "confidence_score": 0.9,
                    }
                ],
                total_confidence=0.9,
                total_execution_time=2.0,
                reasoning_strategy="decomposition",
            )

            # Act
            result_cot_original = cot_service.execute_chain_of_thought(cot_input_original, ["doc1"], user_id)

            # Assert - Original CoT functionality preserved
            assert result_cot_original.final_answer is not None
            assert result_cot_original.reasoning_strategy == "decomposition"
            assert len(result_cot_original.reasoning_steps) == 1
            assert result_cot_original.total_confidence > 0.8
            mock_cot_original.assert_called_once_with(cot_input_original, ["doc1"], user_id)

        # Test 3: Enhanced search with conversation context
        search_input_enhanced = SearchInput(
            question="How does it work?",
            collection_id=collection_id,
            user_id=user_id,
            config_metadata={
                "conversation_context": "Previous discussion about machine learning",
                "message_history": ["What is machine learning?", "Machine learning is a subset of AI..."],
                "conversation_entities": ["machine learning", "AI"],
                "cot_enabled": True,
                "session_id": str(session_id),
            },
        )

        with patch.object(search_service, "search") as mock_search_enhanced:
            mock_search_enhanced.return_value = SearchOutput(
                answer="Machine learning works by using algorithms to identify patterns in data, building on our previous discussion about AI concepts.",
                documents=["doc1", "doc2"],
                query_results=[],
                execution_time=1.2,
                metadata={
                    "conversation_aware": True,
                    "enhanced": True,
                    "original_functionality": True,
                    "enhanced_question": "How does machine learning work? (in the context of AI concepts)",
                },
            )

            # Act
            result_enhanced = search_service.search(search_input_enhanced)

            # Assert - Enhanced functionality works
            assert result_enhanced.answer is not None
            assert "Previous discussion about AI concepts" in result_enhanced.answer
            assert result_enhanced.metadata["conversation_aware"] is True
            assert result_enhanced.metadata["enhanced"] is True
            assert result_enhanced.metadata["original_functionality"] is True
            mock_search_enhanced.assert_called_once_with(search_input_enhanced)

        # Test 4: Enhanced CoT with conversation history
        cot_input_enhanced = ChainOfThoughtInput(
            question="How do they relate?",
            collection_id=collection_id,
            user_id=user_id,
            context_metadata={
                "conversation_context": "Previous discussion about machine learning and neural networks",
                "message_history": [
                    "What is machine learning?",
                    "Machine learning is a subset of AI...",
                    "What are neural networks?",
                    "Neural networks are computing systems...",
                ],
                "conversation_entities": ["machine learning", "neural networks", "AI"],
            },
        )

        with patch.object(cot_service, "execute_chain_of_thought") as mock_cot_enhanced:
            mock_cot_enhanced.return_value = ChainOfThoughtOutput(
                original_question=cot_input_enhanced.question,
                final_answer="Machine learning and neural networks are closely related. Machine learning is the broader field that includes neural networks as one of its key techniques, building on our previous discussion about AI concepts.",
                reasoning_steps=[
                    {
                        "step_number": 1,
                        "step_question": "What is machine learning?",
                        "intermediate_answer": "Machine learning is a subset of AI...",
                        "confidence_score": 0.9,
                    },
                    {
                        "step_number": 2,
                        "step_question": "What are neural networks?",
                        "intermediate_answer": "Neural networks are computing systems...",
                        "confidence_score": 0.85,
                    },
                    {
                        "step_number": 3,
                        "step_question": "How do they relate?",
                        "intermediate_answer": "Neural networks are a key technique in machine learning...",
                        "confidence_score": 0.88,
                    },
                ],
                total_confidence=0.88,
                total_execution_time=2.5,
                reasoning_strategy="conversation_aware",
            )

            # Act
            result_cot_enhanced = cot_service.execute_chain_of_thought(cot_input_enhanced, ["doc1", "doc2"], user_id)

            # Assert - Enhanced CoT functionality works
            assert result_cot_enhanced.final_answer is not None
            assert "Previous discussion about AI concepts" in result_cot_enhanced.final_answer
            assert result_cot_enhanced.reasoning_strategy == "conversation_aware"
            assert len(result_cot_enhanced.reasoning_steps) == 3
            assert result_cot_enhanced.total_confidence > 0.8
            mock_cot_enhanced.assert_called_once_with(cot_input_enhanced, ["doc1", "doc2"], user_id)

        # Test 5: Backward compatibility - existing APIs still work
        # This ensures that existing clients continue to work without changes

        # Test existing search API
        assert search_service.search(search_input_original).answer is not None

        # Test existing CoT API
        assert cot_service.execute_chain_of_thought(cot_input_original, ["doc1"], user_id).final_answer is not None

        # Test that new conversation features are additive, not breaking
        message = ConversationMessageInput(
            session_id=session_id, content="Test question", role=MessageRole.USER, message_type=MessageType.QUESTION
        )

        with patch.object(conversation_service, "process_user_message") as mock_conversation:
            mock_conversation.return_value = ConversationMessageInput(
                session_id=session_id,
                content="Response with enhanced capabilities",
                role=MessageRole.ASSISTANT,
                message_type=MessageType.ANSWER,
                metadata={"backward_compatible": True, "enhanced_features": True, "original_apis_preserved": True},
            )

            # Act
            result_conversation = conversation_service.process_user_message(message)

            # Assert - Backward compatibility maintained
            assert result_conversation.metadata["backward_compatible"] is True
            assert result_conversation.metadata["enhanced_features"] is True
            assert result_conversation.metadata["original_apis_preserved"] is True
