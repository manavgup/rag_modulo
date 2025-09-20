"""Integration tests for context flow validation - TDD Red Phase.

This module contains tests that validate the context flow from conversation
through search to Chain of Thought, ensuring seamless integration.
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from core.config import Settings

from rag_solution.schemas.conversation_schema import (
    ConversationContext,
    ConversationMessageInput,
    MessageRole,
    MessageType,
)
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.services.context_manager_service import ContextManagerService
from rag_solution.services.conversation_service import ConversationService
from rag_solution.services.search_service import SearchService


class TestContextFlowTDD:
    """Test cases for context flow validation across services."""

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

    @pytest.mark.integration
    def test_context_enhancement_question_with_entities(self, context_manager_service: ContextManagerService) -> None:
        """Integration: Test question enhancement with extracted entities."""
        # Arrange
        question = "How does it work?"
        conversation_context = "Previous discussion about machine learning and neural networks"
        message_history = [
            "What is machine learning?",
            "Machine learning is a subset of AI...",
            "What are neural networks?",
            "Neural networks are computing systems...",
        ]

        # Mock entity extraction
        with patch.object(
            context_manager_service,
            "extract_entities_from_context",
            return_value=["machine learning", "neural networks"],
        ):
            with patch.object(context_manager_service, "is_ambiguous_question", return_value=True):
                # Act
                enhanced_question = context_manager_service.enhance_question_with_conversation_context(
                    question, conversation_context, message_history
                )

                # Assert
                assert "machine learning" in enhanced_question
                assert "neural networks" in enhanced_question
                assert "(in the context of" in enhanced_question
                assert "(referring to:" in enhanced_question

    @pytest.mark.integration
    def test_context_enhancement_question_without_entities(
        self, context_manager_service: ContextManagerService
    ) -> None:
        """Integration: Test question enhancement without extracted entities."""
        # Arrange
        question = "What is the next step?"
        conversation_context = "Previous discussion about project planning"
        message_history = ["Let's plan the project", "First, we need to define requirements..."]

        # Mock entity extraction to return empty list
        with patch.object(context_manager_service, "extract_entities_from_context", return_value=[]):
            with patch.object(context_manager_service, "is_ambiguous_question", return_value=True):
                # Act
                enhanced_question = context_manager_service.enhance_question_with_conversation_context(
                    question, conversation_context, message_history
                )

                # Assert
                assert question in enhanced_question
                assert "(referring to:" in enhanced_question
                assert "project planning" in enhanced_question
                assert "(in the context of" not in enhanced_question

    @pytest.mark.integration
    def test_context_pruning_relevance_based(self, context_manager_service: ContextManagerService) -> None:
        """Integration: Test context pruning based on relevance scores."""
        # Arrange
        context = "This is about machine learning, neural networks, deep learning, computer vision, NLP, and reinforcement learning."
        current_question = "How does deep learning work?"

        # Mock relevance calculation
        with patch.object(context_manager_service, "_calculate_relevance_scores") as mock_calc:
            mock_calc.return_value = {
                "deep learning": 0.95,
                "neural networks": 0.85,
                "machine learning": 0.70,
                "computer vision": 0.30,
                "NLP": 0.25,
                "reinforcement learning": 0.20,
            }

            with patch.object(context_manager_service, "_keep_relevant_content") as mock_keep:
                mock_keep.return_value = "deep learning, neural networks, machine learning"

                # Act
                pruned_context = context_manager_service.prune_context_for_performance(context, current_question)

                # Assert
                mock_calc.assert_called_once_with(context, current_question)
                mock_keep.assert_called_once()
                assert pruned_context == "deep learning, neural networks, machine learning"

    @pytest.mark.integration
    def test_context_caching_hit(self, context_manager_service: ContextManagerService) -> None:
        """Integration: Test context caching hit scenario."""
        # Arrange
        session_id = uuid4()
        messages = [
            ConversationMessageInput(
                session_id=session_id, content="Test message", role=MessageRole.USER, message_type=MessageType.QUESTION
            )
        ]

        # Mock context building
        with patch.object(context_manager_service, "_build_context_from_messages_impl") as mock_build:
            mock_build.return_value = ConversationContext(
                session_id=session_id, context_window="Test context", relevant_documents=[], context_metadata={}
            )

            # Act - First call
            context1 = context_manager_service.build_context_from_messages(session_id, messages)

            # Second call (should hit cache)
            context2 = context_manager_service.build_context_from_messages(session_id, messages)

            # Assert
            assert mock_build.call_count == 1  # Should only build once
            assert context1 == context2

    @pytest.mark.integration
    def test_context_caching_miss(self, context_manager_service: ContextManagerService) -> None:
        """Integration: Test context caching miss scenario."""
        # Arrange
        session_id = uuid4()
        messages1 = [
            ConversationMessageInput(
                session_id=session_id, content="First message", role=MessageRole.USER, message_type=MessageType.QUESTION
            )
        ]
        messages2 = [
            ConversationMessageInput(
                session_id=session_id, content="First message", role=MessageRole.USER, message_type=MessageType.QUESTION
            ),
            ConversationMessageInput(
                session_id=session_id,
                content="Second message",
                role=MessageRole.ASSISTANT,
                message_type=MessageType.ANSWER,
            ),
        ]

        # Mock context building
        with patch.object(context_manager_service, "_build_context_from_messages_impl") as mock_build:
            mock_build.return_value = ConversationContext(
                session_id=session_id, context_window="Test context", relevant_documents=[], context_metadata={}
            )

            # Act - First call
            context1 = context_manager_service.build_context_from_messages(session_id, messages1)

            # Second call with different messages (should miss cache)
            context2 = context_manager_service.build_context_from_messages(session_id, messages2)

            # Assert
            assert mock_build.call_count == 2  # Should build twice
            assert context1 == context2  # But return same context (mocked)

    @pytest.mark.integration
    def test_context_metadata_propagation(
        self, conversation_service: ConversationService, search_service: SearchService
    ) -> None:
        """Integration: Test context metadata propagation through services."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        session_id = uuid4()

        message = ConversationMessageInput(
            session_id=session_id,
            content="What is machine learning?",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
        )

        # Mock search service to capture metadata
        captured_metadata = None

        def capture_metadata(search_input: SearchInput) -> SearchOutput:
            nonlocal captured_metadata
            captured_metadata = search_input.config_metadata
            return SearchOutput(answer="Test answer", documents=[], query_results=[], execution_time=1.0)

        with patch.object(search_service, "search", side_effect=capture_metadata):
            with patch.object(conversation_service, "search_service", search_service):
                # Act
                conversation_service.process_user_message(message)

                # Assert
                assert captured_metadata is not None
                assert "session_id" in captured_metadata
                assert captured_metadata["session_id"] == str(session_id)
                assert "conversation_context" in captured_metadata
                assert "message_history" in captured_metadata
                assert "conversation_entities" in captured_metadata
                assert captured_metadata["cot_enabled"] is True
                assert captured_metadata["show_cot_steps"] is False

    @pytest.mark.integration
    def test_context_enhancement_with_pronoun_resolution(self, context_manager_service: ContextManagerService) -> None:
        """Integration: Test context enhancement with pronoun resolution."""
        # Arrange
        question = "How does it work?"
        conversation_context = "Previous discussion about machine learning algorithms"
        message_history = [
            "What is machine learning?",
            "Machine learning is a subset of AI...",
            "What are the algorithms?",
            "There are many algorithms like linear regression, decision trees...",
        ]

        # Mock pronoun resolution
        with patch.object(context_manager_service, "resolve_pronouns", return_value="How does machine learning work?"):
            with patch.object(
                context_manager_service,
                "extract_entities_from_context",
                return_value=["machine learning", "algorithms"],
            ):
                # Act
                enhanced_question = context_manager_service.enhance_question_with_conversation_context(
                    question, conversation_context, message_history
                )

                # Assert
                assert "machine learning" in enhanced_question
                assert "algorithms" in enhanced_question
                assert "(in the context of" in enhanced_question

    @pytest.mark.integration
    def test_context_enhancement_with_follow_up_detection(self, context_manager_service: ContextManagerService) -> None:
        """Integration: Test context enhancement with follow-up question detection."""
        # Arrange
        question = "Tell me more"
        conversation_context = "Previous discussion about neural networks and deep learning"
        message_history = [
            "What are neural networks?",
            "Neural networks are computing systems...",
            "What is deep learning?",
            "Deep learning is a subset of machine learning...",
        ]

        # Mock follow-up detection
        with patch.object(context_manager_service, "detect_follow_up_question", return_value=True):
            with patch.object(
                context_manager_service,
                "extract_entities_from_context",
                return_value=["neural networks", "deep learning"],
            ):
                # Act
                enhanced_question = context_manager_service.enhance_question_with_conversation_context(
                    question, conversation_context, message_history
                )

                # Assert
                assert "neural networks" in enhanced_question
                assert "deep learning" in enhanced_question
                assert "(in the context of" in enhanced_question
                assert "(referring to:" in enhanced_question

    @pytest.mark.integration
    def test_context_enhancement_with_entity_relationships(
        self, context_manager_service: ContextManagerService
    ) -> None:
        """Integration: Test context enhancement with entity relationships."""
        # Arrange
        question = "How are they related?"
        conversation_context = "Previous discussion about machine learning, neural networks, and deep learning"
        message_history = [
            "What is machine learning?",
            "Machine learning is a subset of AI...",
            "What are neural networks?",
            "Neural networks are computing systems...",
            "What is deep learning?",
            "Deep learning is a subset of machine learning...",
        ]

        # Mock entity relationship extraction
        with patch.object(
            context_manager_service,
            "extract_entities_from_context",
            return_value=["machine learning", "neural networks", "deep learning"],
        ):
            with patch.object(
                context_manager_service,
                "extract_entity_relationships",
                return_value={
                    "machine learning": ["neural networks", "deep learning"],
                    "neural networks": ["deep learning"],
                    "deep learning": ["machine learning", "neural networks"],
                },
            ):
                # Act
                enhanced_question = context_manager_service.enhance_question_with_conversation_context(
                    question, conversation_context, message_history
                )

                # Assert
                assert "machine learning" in enhanced_question
                assert "neural networks" in enhanced_question
                assert "deep learning" in enhanced_question
                assert "(in the context of" in enhanced_question

    @pytest.mark.integration
    def test_context_enhancement_with_temporal_context(self, context_manager_service: ContextManagerService) -> None:
        """Integration: Test context enhancement with temporal context."""
        # Arrange
        question = "What did we discuss earlier?"
        conversation_context = "Previous discussion about project planning and requirements"
        message_history = [
            "Let's plan the project",
            "First, we need to define requirements...",
            "What about the timeline?",
            "We should aim for 3 months...",
            "What about resources?",
            "We'll need 2 developers...",
        ]

        # Mock temporal context extraction
        with patch.object(
            context_manager_service,
            "extract_temporal_context",
            return_value={
                "earlier_topics": ["project planning", "requirements", "timeline", "resources"],
                "recent_topics": ["resources", "timeline"],
                "temporal_relationships": {
                    "project planning": ["requirements", "timeline", "resources"],
                    "requirements": ["timeline", "resources"],
                },
            },
        ):
            # Act
            enhanced_question = context_manager_service.enhance_question_with_conversation_context(
                question, conversation_context, message_history
            )

            # Assert
            assert "project planning" in enhanced_question
            assert "requirements" in enhanced_question
            assert "timeline" in enhanced_question
            assert "resources" in enhanced_question
            assert "(referring to:" in enhanced_question

    @pytest.mark.integration
    def test_context_enhancement_with_semantic_similarity(self, context_manager_service: ContextManagerService) -> None:
        """Integration: Test context enhancement with semantic similarity."""
        # Arrange
        question = "How does it work?"
        conversation_context = "Previous discussion about machine learning algorithms and their applications"
        message_history = [
            "What is machine learning?",
            "Machine learning is a subset of AI...",
            "What are the algorithms?",
            "There are many algorithms like linear regression, decision trees, SVM...",
        ]

        # Mock semantic similarity calculation
        with patch.object(
            context_manager_service,
            "calculate_semantic_similarity",
            return_value={
                "machine learning": 0.95,
                "algorithms": 0.90,
                "linear regression": 0.85,
                "decision trees": 0.80,
                "SVM": 0.75,
            },
        ):
            with patch.object(
                context_manager_service,
                "extract_entities_from_context",
                return_value=["machine learning", "algorithms"],
            ):
                # Act
                enhanced_question = context_manager_service.enhance_question_with_conversation_context(
                    question, conversation_context, message_history
                )

                # Assert
                assert "machine learning" in enhanced_question
                assert "algorithms" in enhanced_question
                assert "(in the context of" in enhanced_question

    @pytest.mark.integration
    def test_context_enhancement_with_conversation_topic(self, context_manager_service: ContextManagerService) -> None:
        """Integration: Test context enhancement with conversation topic."""
        # Arrange
        question = "What's next?"
        conversation_context = "Previous discussion about project planning and implementation"
        message_history = [
            "Let's plan the project",
            "First, we need to define requirements...",
            "What about the architecture?",
            "We'll use microservices...",
            "What about the database?",
            "We'll use PostgreSQL...",
        ]

        # Mock conversation topic extraction
        with patch.object(
            context_manager_service, "extract_conversation_topic", return_value="project planning and implementation"
        ):
            with patch.object(
                context_manager_service,
                "extract_entities_from_context",
                return_value=["project", "requirements", "architecture", "microservices", "database", "PostgreSQL"],
            ):
                # Act
                enhanced_question = context_manager_service.enhance_question_with_conversation_context(
                    question, conversation_context, message_history
                )

                # Assert
                assert "project" in enhanced_question
                assert "requirements" in enhanced_question
                assert "architecture" in enhanced_question
                assert "(in the context of" in enhanced_question
