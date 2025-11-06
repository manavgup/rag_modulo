"""Conversation context service for managing conversation context and question enhancement.

This service handles context building, question enhancement, entity extraction,
pronoun resolution, and follow-up detection for conversation-aware RAG queries.

Extracted from ConversationService (11 context methods) for better separation
of concerns and improved testability.
"""

import asyncio
import logging
import re
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.schemas.conversation_schema import ConversationContext, ConversationMessageOutput
from rag_solution.services.entity_extraction_service import EntityExtractionService

logger = logging.getLogger(__name__)


class ConversationContextService:
    """Manages conversation context and question enhancement.

    This service provides:
    - Context window construction from messages
    - Question enhancement with entity extraction
    - Pronoun resolution using context entities
    - Follow-up question detection
    - Context pruning for performance
    - Temporal context extraction
    - Entity relationship extraction
    """

    def __init__(
        self,
        db: Session,
        settings: Settings,
        entity_extraction_service: EntityExtractionService,
    ):
        """Initialize the conversation context service.

        Args:
            db: Database session
            settings: Application settings
            entity_extraction_service: Entity extraction service
        """
        self.db = db
        self.settings = settings
        self.entity_extraction_service = entity_extraction_service
        self._context_cache: dict[str, ConversationContext] = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps: dict[str, float] = {}

    async def build_context_from_messages(
        self, session_id: UUID, messages: list[ConversationMessageOutput]
    ) -> ConversationContext:
        """Build conversation context from messages with caching.

        Args:
            session_id: Session ID
            messages: List of conversation messages

        Returns:
            Conversation context with context window, entities, and topics
        """
        # Check cache first
        cache_key = f"{session_id}_{len(messages)}"
        if cache_key in self._context_cache:
            if not self._is_cache_expired(cache_key):
                logger.debug(f"Cache hit for session {session_id}, {len(messages)} messages")
                return self._context_cache[cache_key]
            else:
                # Remove expired cache entry
                del self._context_cache[cache_key]
                del self._cache_timestamps[cache_key]

        # Build context
        context = await self._build_context_impl(session_id, messages)

        # Cache the result
        import time

        self._context_cache[cache_key] = context
        self._cache_timestamps[cache_key] = time.time()

        logger.debug(f"Built and cached context for session {session_id}, {len(messages)} messages")
        return context

    async def enhance_question_with_context(
        self, question: str, conversation_context: str, message_history: list[str]
    ) -> str:
        """Enhance question with conversation context.

        IMPORTANT: Only extracts entities from USER messages to prevent pollution
        from assistant's verbose responses containing discourse markers.

        Args:
            question: Original question
            conversation_context: Full conversation context
            message_history: Recent message history

        Returns:
            Enhanced question with entity and contextual information
        """
        # Extract user-only context to prevent assistant response pollution
        user_only_context = self._extract_user_messages_from_context(conversation_context)

        # Extract entities only from user messages
        entities = await self.extract_entities_from_context(user_only_context)

        # Start with the original question
        enhanced_question = question

        # Add entity context if entities exist
        if entities:
            entity_context = f" (in the context of {', '.join(entities)})"
            enhanced_question = f"{enhanced_question}{entity_context}"

        # Add conversation context if question is ambiguous
        if self.detect_follow_up_question(question):
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

        return enhanced_question

    async def extract_entities_from_context(self, context: str) -> list[str]:
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
        # Use async service in sync context
        try:
            entities = await self.entity_extraction_service.extract_entities(
                context=context,
                method="hybrid",  # Changed from "fast" to "hybrid" for better quality
                use_cache=True,
                max_entities=10,
            )
            logger.debug("Extracted %d entities from context: %s", len(entities), entities)
            return entities
        except Exception as e:
            logger.error("Entity extraction failed: %s, returning empty list", e)
            return []

    def resolve_pronouns(self, question: str, context: str) -> str:
        """Resolve pronouns using context entities.

        Args:
            question: Question with pronouns
            context: Conversation context

        Returns:
            Question with resolved pronouns
        """
        # Simple pronoun resolution - in production, this would be more sophisticated
        pronouns = ["it", "this", "that", "they", "them", "these", "those"]
        question_lower = question.lower()

        # Check if question contains pronouns
        if not any(pronoun in question_lower.split() for pronoun in pronouns):
            return question

        # Extract entities from context
        loop = asyncio.get_event_loop()
        entities = loop.run_until_complete(self.extract_entities_from_context(context))

        if not entities:
            return question

        # Use the most recent entity for pronoun resolution
        most_recent_entity = entities[0] if entities else None

        if most_recent_entity:
            # Simple replacement (in production, use more sophisticated NLP)
            for pronoun in pronouns:
                pattern = rf"\b{pronoun}\b"
                question = re.sub(pattern, most_recent_entity, question, count=1, flags=re.IGNORECASE)

        return question

    def detect_follow_up_question(self, question: str) -> bool:
        """Detect if question is a follow-up using patterns.

        Args:
            question: Question to analyze

        Returns:
            True if question appears to be a follow-up
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

    def prune_context_for_performance(self, context: str, current_question: str) -> str:
        """Prune context while maintaining relevance.

        Args:
            context: Full conversation context
            current_question: Current question

        Returns:
            Pruned context with only relevant information
        """
        # Calculate relevance scores
        scores = self._calculate_relevance_scores(context, current_question)

        # Keep only relevant content
        pruned_context = self._keep_relevant_content(context, scores, threshold=0.5)

        return pruned_context

    def extract_entity_relationships(self, context: str) -> dict[str, list[str]]:
        """Extract relationships between entities.

        Args:
            context: Conversation context

        Returns:
            Dictionary mapping entities to related entities
        """
        # Simple relationship extraction - in production, use advanced NLP
        loop = asyncio.get_event_loop()
        entities = loop.run_until_complete(self.extract_entities_from_context(context))

        relationships: dict[str, list[str]] = {}
        for i, entity in enumerate(entities):
            # Relate each entity to nearby entities (simple co-occurrence)
            related = []
            if i > 0:
                related.append(entities[i - 1])
            if i < len(entities) - 1:
                related.append(entities[i + 1])

            if related:
                relationships[entity] = related

        return relationships

    def extract_temporal_context(self, context: str) -> dict[str, list[str]]:
        """Extract temporal context information.

        Args:
            context: Conversation context

        Returns:
            Dictionary with temporal information (past, present, future references)
        """
        temporal_info: dict[str, list[str]] = {"past": [], "present": [], "future": []}

        # Temporal markers
        past_markers = [
            "was",
            "were",
            "had",
            "did",
            "previously",
            "before",
            "earlier",
            "last",
            "ago",
            "yesterday",
        ]
        present_markers = ["is", "are", "am", "currently", "now", "today", "at the moment"]
        future_markers = [
            "will",
            "shall",
            "would",
            "going to",
            "planning",
            "next",
            "tomorrow",
            "soon",
            "later",
        ]

        sentences = context.split(".")
        for sentence in sentences:
            sentence_lower = sentence.lower()

            if any(marker in sentence_lower for marker in past_markers):
                temporal_info["past"].append(sentence.strip())
            elif any(marker in sentence_lower for marker in present_markers):
                temporal_info["present"].append(sentence.strip())
            elif any(marker in sentence_lower for marker in future_markers):
                temporal_info["future"].append(sentence.strip())

        return temporal_info

    # Internal helper methods

    def _is_cache_expired(self, cache_key: str) -> bool:
        """Check if cache entry is expired.

        Args:
            cache_key: Cache key

        Returns:
            True if cache is expired
        """
        import time

        if cache_key not in self._cache_timestamps:
            return True

        elapsed = time.time() - self._cache_timestamps[cache_key]
        return elapsed > self._cache_ttl

    async def _build_context_impl(
        self, session_id: UUID, messages: list[ConversationMessageOutput]
    ) -> ConversationContext:
        """Implementation for building context from messages.

        Args:
            session_id: Session ID
            messages: List of conversation messages

        Returns:
            Conversation context
        """
        context_window = self._build_context_window(messages)
        entities = await self.extract_entities_from_context(context_window)
        topics = self._extract_topics_from_context(context_window)

        from rag_solution.schemas.conversation_schema import ContextMetadata

        return ConversationContext(
            session_id=session_id,
            context_window=context_window,
            relevant_documents=[],
            context_metadata=ContextMetadata(
                extracted_entities=entities,
                conversation_topics=topics,
                message_count=len(messages),
                context_length=len(context_window),
            ),
        )

    def _build_context_window(self, messages: list[ConversationMessageOutput]) -> str:
        """Build context window from messages.

        Args:
            messages: List of conversation messages

        Returns:
            Context window string
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

    def _extract_topics_from_context(self, context: str) -> list[str]:
        """Extract topics from context.

        Args:
            context: Conversation context

        Returns:
            List of topics
        """
        topics = []

        # Look for question patterns
        question_patterns = [r"what is (.+?)\?", r"how does (.+?) work", r"explain (.+?)", r"tell me about (.+?)"]

        for pattern in question_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            topics.extend(matches)

        return list(set(topics))

    def _calculate_relevance_scores(self, context: str, current_question: str) -> dict[str, float]:
        """Calculate relevance scores for context elements.

        Args:
            context: Conversation context
            current_question: Current question

        Returns:
            Dictionary mapping entities to relevance scores
        """
        scores = {}
        loop = asyncio.get_event_loop()
        entities = loop.run_until_complete(self.extract_entities_from_context(context))
        question_lower = current_question.lower()

        for entity in entities:
            if entity.lower() in question_lower:
                scores[entity] = 0.9
            elif any(word in entity.lower() for word in question_lower.split()):
                scores[entity] = 0.7
            else:
                scores[entity] = 0.3

        return scores

    def _keep_relevant_content(self, _context: str, relevance_scores: dict[str, float], threshold: float = 0.5) -> str:
        """Keep only relevant content based on scores.

        Args:
            _context: Full conversation context (unused, reserved for future enhancements)
            relevance_scores: Relevance scores for entities
            threshold: Minimum relevance score to keep

        Returns:
            Pruned context with only relevant entities
        """
        relevant_entities = [entity for entity, score in relevance_scores.items() if score >= threshold]
        return ", ".join(relevant_entities)
