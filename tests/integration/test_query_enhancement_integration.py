"""Integration tests for query enhancement with assistant message filtering.

These tests verify that the query enhancement process filters out assistant
messages and prevents pollution from discourse markers in the end-to-end flow.
"""

import pytest

from rag_solution.schemas.conversation_schema import ConversationMessageOutput
from rag_solution.services.conversation_service import ConversationService


@pytest.mark.integration
class TestQueryEnhancementIntegration:
    """Integration tests for query enhancement with filtered context."""

    @pytest.fixture
    def sample_messages_with_assistant_pollution(self):
        """Create sample messages with assistant discourse markers."""
        return [
            ConversationMessageOutput(
                id="msg1",
                session_id="sess1",
                content="What is IBM?",
                role="user",
                metadata={},
            ),
            ConversationMessageOutput(
                id="msg2",
                session_id="sess1",
                content="Based on the analysis, IBM is a technology company. However, the context suggests it has multiple divisions. Additionally, since the revenue data shows strong returns on equity, it appears that Global Financing is a key component.",
                role="assistant",
                metadata={},
            ),
            ConversationMessageOutput(
                id="msg3",
                session_id="sess1",
                content="What was the revenue in 2020?",
                role="user",
                metadata={},
            ),
        ]

    @pytest.fixture
    def expected_clean_entities(self):
        """Expected entities after filtering (no discourse markers)."""
        return ["IBM", "2020", "revenue"]

    async def test_enhance_question_filters_assistant_messages(
        self, conversation_service: ConversationService, sample_messages_with_assistant_pollution
    ):
        """Test that query enhancement filters out assistant messages end-to-end."""
        # Build context from messages (includes both user and assistant)
        context = conversation_service._build_context_window(sample_messages_with_assistant_pollution)

        # Verify context includes assistant messages (as expected)
        assert "Based on the analysis" in context
        assert "However" in context
        assert "Additionally" in context

        # Extract user-only context
        user_context = conversation_service._extract_user_messages_from_context(context)

        # Verify assistant messages are filtered out
        assert "Based on the analysis" not in user_context
        assert "However" not in user_context
        assert "Additionally" not in user_context
        assert "Since" not in user_context

        # Verify user messages are preserved
        assert "What is IBM?" in user_context
        assert "What was the revenue in 2020?" in user_context

    async def test_entity_extraction_without_discourse_markers(
        self, conversation_service: ConversationService, sample_messages_with_assistant_pollution
    ):
        """Test that entities extracted don't include discourse markers."""
        # Build context
        context = conversation_service._build_context_window(sample_messages_with_assistant_pollution)

        # Extract user-only context (as the fix does)
        user_context = conversation_service._extract_user_messages_from_context(context)

        # Extract entities from filtered context
        entities = conversation_service._extract_entities_from_context(user_context)

        # Verify no discourse markers in entities
        discourse_markers = {
            "however",
            "based",
            "additionally",
            "since",
            "this",
            "that",
            "context",
            "analysis",
            "suggests",
            "appears",
        }

        entity_lower = {e.lower() for e in entities}
        discourse_in_entities = discourse_markers & entity_lower

        assert len(discourse_in_entities) == 0, f"Discourse markers found in entities: {discourse_in_entities}"

    async def test_enhanced_question_is_cleaner(
        self, conversation_service: ConversationService, sample_messages_with_assistant_pollution
    ):
        """Test that enhanced question is significantly cleaner without assistant pollution."""
        question = "What was the revenue in 2020?"

        # Build context (includes assistant messages)
        context = conversation_service._build_context_window(sample_messages_with_assistant_pollution)
        message_history = [msg.content for msg in sample_messages_with_assistant_pollution]

        # Enhance question using the service
        enhanced = await conversation_service.enhance_question_with_context(question, context, message_history)

        # The enhanced question should not contain discourse markers
        discourse_markers = [
            "However",
            "Based",
            "Additionally",
            "Since",
            "analysis",
            "context suggests",
            "appears that",
        ]

        for marker in discourse_markers:
            assert marker not in enhanced, f"Discourse marker '{marker}' found in enhanced query: {enhanced}"

        # Should still contain the original question
        assert question in enhanced

    async def test_query_enhancement_reduces_token_count(
        self, conversation_service: ConversationService, sample_messages_with_assistant_pollution
    ):
        """Test that filtering reduces token count significantly (target: 85-92% reduction)."""
        question = "What was the revenue in 2020?"

        # Build full context with assistant messages
        full_context = conversation_service._build_context_window(sample_messages_with_assistant_pollution)

        # Extract entities from full context (old way - would include pollution)
        full_entities = conversation_service._extract_entities_from_context(full_context)

        # Extract user-only context (new way - filtered)
        user_context = conversation_service._extract_user_messages_from_context(full_context)
        filtered_entities = conversation_service._extract_entities_from_context(user_context)

        # Filtered entities should be significantly fewer
        # We expect at least 50% reduction in entity count
        assert len(filtered_entities) <= len(full_entities) * 0.5, (
            f"Expected significant entity reduction. Full: {len(full_entities)}, Filtered: {len(filtered_entities)}"
        )

        # Build enhanced questions
        message_history = [msg.content for msg in sample_messages_with_assistant_pollution]
        enhanced = await conversation_service.enhance_question_with_context(
            question,
            user_context,
            message_history,  # Using filtered context
        )

        # Enhanced query token count should be reasonable (< 100 tokens)
        enhanced_token_count = len(enhanced.split())
        assert enhanced_token_count < 100, (
            f"Enhanced query too long: {enhanced_token_count} tokens. Expected < 100 tokens. Query: {enhanced}"
        )

    async def test_user_only_messages_preserve_query_context(self, conversation_service: ConversationService):
        """Test that user-only filtering preserves all necessary query context."""
        messages = [
            ConversationMessageOutput(
                id="msg1",
                session_id="sess1",
                content="Tell me about IBM revenue",
                role="user",
                metadata={},
            ),
            ConversationMessageOutput(
                id="msg2",
                session_id="sess1",
                content="IBM had revenue of $57.4 billion in 2023.",
                role="assistant",
                metadata={},
            ),
            ConversationMessageOutput(
                id="msg3",
                session_id="sess1",
                content="What about 2020?",
                role="user",
                metadata={},
            ),
        ]

        context = conversation_service._build_context_window(messages)
        user_context = conversation_service._extract_user_messages_from_context(context)

        # Should preserve user messages
        assert "Tell me about IBM revenue" in user_context
        assert "What about 2020?" in user_context

        # Should filter assistant response
        assert "57.4 billion" not in user_context

        # Extract entities from filtered context
        entities = conversation_service._extract_entities_from_context(user_context)

        # Should extract relevant entities from user messages
        entity_lower = [e.lower() for e in entities]
        assert any("ibm" in e for e in entity_lower), f"Expected 'IBM' in entities: {entities}"
        assert any("2020" in e for e in entity_lower), f"Expected '2020' in entities: {entities}"
