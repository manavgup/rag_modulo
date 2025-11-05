"""Conversation Context Service for context management and question enhancement.

This service manages conversation context building and question enhancement.
Extracted from ConversationService to follow Single Responsibility Principle.

Phase 3C: Minimal Implementation
- Only implements methods actually used in production code
- build_context_from_messages(): Used by MessageProcessingOrchestrator
- enhance_question_with_context(): Used by MessageProcessingOrchestrator
"""

import asyncio
import logging
import re
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.schemas.conversation_schema import (
    ConversationContext,
    ConversationMessageOutput,
)
from rag_solution.services.entity_extraction_service import EntityExtractionService

logger = logging.getLogger(__name__)


class ConversationContextService:
    """Manages conversation context and question enhancement.

    Responsibilities:
    - Build conversation context from message history
    - Extract entities from user messages (not assistant responses)
    - Enhance questions with contextual information
    - Cache context for performance (5-minute TTL)
    """

    def __init__(
        self,
        db: Session,
        settings: Settings,
        entity_extraction_service: EntityExtractionService,
    ):
        """Initialize ConversationContextService.

        Args:
            db: Database session
            settings: Application settings
            entity_extraction_service: Service for entity extraction
        """
        self.db = db
        self.settings = settings
        self.entity_extraction_service = entity_extraction_service
        self._context_cache: dict[str, ConversationContext] = {}
        self._cache_ttl = 300  # 5 minutes

    async def build_context_from_messages(
        self, session_id: UUID, messages: list[ConversationMessageOutput]
    ) -> ConversationContext:
        """Build conversation context from messages with caching and entity extraction.

        Args:
            session_id: Conversation session ID
            messages: List of conversation messages

        Returns:
            ConversationContext with context window, entities, topics, and metadata
        """
        # Check cache first
        cache_key = f"{session_id}_{len(messages)}"
        if cache_key in self._context_cache:
            logger.debug(f"Cache hit for context: {cache_key}")
            return self._context_cache[cache_key]

        # Build context window from messages
        context_window = self._build_context_window(messages)

        # Extract entities and topics from context
        entities = self._extract_entities_from_context(context_window)
        topics = self._extract_topics_from_context(context_window)

        # Create context object with typed metadata
        from rag_solution.schemas.conversation_schema import ContextMetadata

        context = ConversationContext(
            session_id=session_id,
            context_window=context_window,
            relevant_documents=[],
            metadata=ContextMetadata(
                extracted_entities=entities,
                conversation_topics=topics,
                message_count=len(messages),
                context_length=len(context_window),
            ),
        )

        # Cache the result
        self._context_cache[cache_key] = context
        logger.debug(
            f"Built context for session {session_id}: "
            f"{len(entities)} entities, {len(topics)} topics, "
            f"{len(messages)} messages"
        )

        return context

    async def enhance_question_with_context(
        self,
        question: str,
        conversation_context: str,
        message_history: list[str],
        cached_entities: list[str] | None = None,
    ) -> str:
        """Enhance question with conversation context.

        IMPORTANT: Only extracts entities from USER messages to prevent pollution
        from assistant's verbose responses containing discourse markers.

        Performance Optimization: Reuses cached entities when provided to avoid
        duplicate extraction (saves 50-100ms per request).

        Args:
            question: Original user question
            conversation_context: Full conversation context
            message_history: Recent message history
            cached_entities: Pre-extracted entities from build_context_from_messages().
                If provided, skips entity extraction (50-100ms saved).

        Returns:
            Enhanced question with entity and contextual information
        """
        # Use cached entities if provided, otherwise extract fresh
        if cached_entities is not None:
            entities = cached_entities
            logger.debug(f"Reusing {len(cached_entities)} cached entities (skipping extraction)")
        else:
            # Extract user-only context to prevent assistant response pollution
            user_only_context = self._extract_user_messages_from_context(conversation_context)
            # Extract entities only from user messages
            entities = self._extract_entities_from_context(user_only_context)
            logger.debug(f"Extracted {len(entities)} entities (no cache provided)")

        # Start with the original question
        enhanced_question = question

        # Add entity context if entities exist
        if entities:
            entity_context = f" (in the context of {', '.join(entities)})"
            enhanced_question = f"{enhanced_question}{entity_context}"

        # Add conversation context if question is ambiguous
        if self._is_ambiguous_question(question):
            recent_context = " ".join(message_history[-3:])  # Last 3 messages
            if entities:
                # If we already added entity context, add ambiguous context as well
                enhanced_question = f"{enhanced_question} (referring to: {recent_context})"
            else:
                # If no entities, add both conversation context and message history
                context_parts = []
                if user_only_context.strip():
                    context_parts.append(user_only_context)
                if recent_context.strip():
                    context_parts.append(recent_context)

                if context_parts:
                    combined_context = " ".join(context_parts)
                    enhanced_question = f"{question} (referring to: {combined_context})"
                else:
                    enhanced_question = question

        logger.debug(f"Enhanced question: '{question}' -> '{enhanced_question}'")
        return enhanced_question

    def _build_context_window(self, messages: list[ConversationMessageOutput]) -> str:
        """Build context window from messages.

        Takes the last 10 messages and formats them as a conversation string.

        Args:
            messages: List of conversation messages

        Returns:
            String representation of conversation context
        """
        if not messages:
            return "No previous conversation context"

        # Take last 10 messages for context
        recent_messages = messages[-10:]
        context_parts = []

        for msg in recent_messages:
            if msg.role == "user":
                context_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                context_parts.append(f"Assistant: {msg.content}")

        return " ".join(context_parts) if context_parts else "No previous conversation context"

    def _extract_user_messages_from_context(self, context: str) -> str:
        """Extract only user messages from context, excluding assistant responses.

        This prevents contamination from assistant's verbose responses which contain
        discourse markers like "Based on", "However", "Additionally" that get
        incorrectly identified as entities by spaCy's noun chunking.

        Args:
            context: Full conversation context with both user and assistant messages

        Returns:
            String containing only user messages, filtered from the context

        Example:
            Input: "User: What is IBM? Assistant: Based on the analysis..."
            Output: "What is IBM?"
        """
        if not context or context == "No previous conversation context":
            return ""

        user_messages = []

        # Split by "Assistant:" to separate sections
        sections = context.split("Assistant:")

        for section in sections:
            if "User:" in section:
                # Extract all user messages from this section
                user_parts = section.split("User:")
                for part in user_parts[1:]:  # Skip first split (before first "User:")
                    user_msg = part.strip()
                    if user_msg:
                        user_messages.append(user_msg)

        return " ".join(user_messages)

    def _extract_entities_from_context(self, context: str) -> list[str]:
        """Extract entities from context using EntityExtractionService.

        This method delegates to EntityExtractionService which provides:
        - Fast spaCy NER extraction (5ms, 75% accuracy)
        - Hybrid mode: spaCy + LLM-based refinement for better quality
        - Comprehensive stop word filtering
        - Entity validation and deduplication

        Note: Using 'hybrid' mode (instead of 'fast') for better quality filtering
        of noise and discourse markers from conversation context. The slight
        performance tradeoff (~50-100ms) is worthwhile for cleaner entity extraction.

        Args:
            context: Conversation context to extract entities from

        Returns:
            List of validated entity strings (max 10)
        """
        if not context or context == "No previous conversation context":
            return []

        loop = asyncio.get_event_loop()
        try:
            entities = loop.run_until_complete(
                self.entity_extraction_service.extract_entities(
                    context=context,
                    method="hybrid",  # Use hybrid mode for better quality
                    use_cache=True,
                    max_entities=10,
                )
            )
            logger.debug("Extracted %d entities from context: %s", len(entities), entities)
            return entities
        except Exception as e:
            logger.error("Entity extraction failed: %s, returning empty list", e)
            return []

    def _extract_topics_from_context(self, context: str) -> list[str]:
        """Extract conversation topics using question pattern matching.

        Args:
            context: Conversation context

        Returns:
            List of extracted topics
        """
        if not context or context == "No previous conversation context":
            return []

        topics = []

        # Look for question patterns
        question_patterns = [
            r"what is (.+?)\?",
            r"how does (.+?) work",
            r"explain (.+?)",
            r"tell me about (.+?)",
        ]

        for pattern in question_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            topics.extend(matches)

        return list(set(topics))

    def _is_ambiguous_question(self, question: str) -> bool:
        """Check if a question is ambiguous and needs contextual enhancement.

        Args:
            question: User question to check

        Returns:
            True if question contains ambiguous references
        """
        question_lower = question.lower().strip()

        # Pattern-based detection for ambiguous questions
        ambiguous_patterns = [
            r"\b(it|this|that|they|them|these|those)\b",  # Pronouns
            r"^(what|how|why|when|where)\s+(is|are|was|were|does|do|did|can|could|will|would)\s+(it|this|that|they)\b",  # Pronoun questions
            r"^(tell me more|what about|how about|what\'s next|next step)\b",  # Vague requests
            r"\b(earlier|before|previous|last|first)\b",  # Temporal references
        ]

        return any(re.search(pattern, question_lower) for pattern in ambiguous_patterns)
