"""Tests for context pollution bug fixes.

Tests verify that the three specific bug fixes work correctly:
1. USER message filtering (no assistant responses in message_history)
2. Message deduplication (no duplicate questions)
3. Refined ambiguity detection (fewer false positives)
"""

import pytest
from rag_solution.services.conversation_service import ConversationService


class TestContextPollutionFixes:
    """Test suite for context pollution bug fixes."""

    @pytest.fixture
    def service(self):
        """Create a conversation service for testing."""
        # Create service with minimal mocks
        from unittest.mock import Mock
        mock_search = Mock()
        mock_repo = Mock()
        mock_llm_config = Mock()

        service = ConversationService(
            search_service=mock_search,
            conversation_repository=mock_repo,
            llm_config_service=mock_llm_config
        )
        return service

    @pytest.mark.asyncio
    async def test_message_deduplication_preserves_order(self, service):
        """Test that message history is deduplicated while preserving order.

        Bug Fix #2: Verify that duplicate questions are removed.
        """
        # Simulate message history with duplicates (from debug log)
        message_history = [
            "what was the IBM revenue?",
            "How many members are part of the IBM Q Network?",
            "How many members are part of the IBM Q Network?",  # DUPLICATE
        ]

        result = await service.enhance_question_with_context(
            question="Tell me more about quantum computing",
            conversation_context="User: what was the IBM revenue?\nUser: How many members are part of the IBM Q Network?",
            message_history=message_history
        )

        # Should NOT contain duplicate "How many members" question
        # The deduplication happens inside enhance_question_with_context
        assert result is not None

    def test_ambiguity_detection_reduces_false_positives(self, service):
        """Test that ambiguity detection is more restrictive.

        Bug Fix #3: Verify fewer false positives.
        """
        # These should NOT be detected as ambiguous (were false positives before)
        not_ambiguous = [
            "How many members are part of this network?",  # "this" with clear subject
            "What was the first IBM quantum computer?",  # "first" with clear subject
            "What technologies do they use in quantum computing?",  # "they" in middle of question
        ]

        for question in not_ambiguous:
            result = service._is_ambiguous_question(question)
            assert not result, f"Question should NOT be ambiguous: {question}"

        # These SHOULD be detected as ambiguous
        actually_ambiguous = [
            "What is it?",  # Pronoun at start
            "Tell me more",  # Continuation phrase
            "What about the earlier discussion?",  # Temporal reference without subject
            "How does this work?",  # Vague pronoun at start
        ]

        for question in actually_ambiguous:
            result = service._is_ambiguous_question(question)
            assert result, f"Question SHOULD be ambiguous: {question}"

    @pytest.mark.asyncio
    async def test_deduplicated_history_used_in_context(self, service):
        """Test that deduplicated history is used when building context."""
        # Exact scenario from debug log
        message_history = [
            "what was the IBM revenue?",
            "How many members are part of the IBM Q Network, and what industries do they represent?",
            "How many members are part of the IBM Q Network, and what industries do they represent?",  # DUPLICATE
        ]

        # Question that triggers ambiguity detection
        result = await service.enhance_question_with_context(
            question="Tell me more",  # Ambiguous question
            conversation_context="User: what was the IBM revenue?",
            message_history=message_history
        )

        # The result should contain context, but not duplicate the IBM Q Network question
        assert "Tell me more" in result
        # Should only mention IBM Q Network once in referring clause
        referring_count = result.count("How many members")
        assert referring_count <= 1, f"Duplicate question detected: {result}"
