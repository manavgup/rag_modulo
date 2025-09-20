"""Context manager service for conversation context handling.

This service manages conversation context, entity extraction,
question enhancement, and context pruning for optimal performance.
"""

import re
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.schemas.conversation_schema import (
    ConversationContext,
    ConversationMessageOutput,
    ContextInput,
    ContextOutput,
)


class ContextManagerService:
    """Service for managing conversation context."""

    def __init__(self, db: Session, settings: Settings):
        """Initialize the context manager service."""
        self.db = db
        self.settings = settings
        self._context_cache: Dict[str, ConversationContext] = {}
        self._cache_ttl = 300  # 5 minutes

    async def build_context_from_messages(
        self, 
        session_id: UUID, 
        messages: List[ConversationMessageOutput]
    ) -> ConversationContext:
        """Build conversation context from messages."""
        # Check cache first
        cache_key = f"{session_id}_{len(messages)}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]

        # Build context from messages
        context_window = self._build_context_window(messages)
        entities = self._extract_entities_from_context(context_window)
        topics = self._extract_topics_from_context(context_window)

        context = ConversationContext(
            session_id=session_id,
            context_window=context_window,
            relevant_documents=[],  # Would be populated from search results
            context_metadata={
                "extracted_entities": entities,
                "conversation_topics": topics,
                "message_count": len(messages),
                "context_length": len(context_window)
            }
        )

        # Cache the result
        self._context_cache[cache_key] = context
        return context

    async def enhance_question_with_conversation_context(
        self, 
        question: str, 
        conversation_context: str, 
        message_history: List[str]
    ) -> str:
        """Enhance question with conversation context."""
        # Extract entities from conversation
        entities = self.extract_entities_from_context(conversation_context)
        
        # Build enhanced question
        if entities:
            entity_context = f" (in the context of {', '.join(entities)})"
            enhanced_question = f"{question}{entity_context}"
        else:
            enhanced_question = question
        
        # Add conversation context if question is ambiguous
        if self.is_ambiguous_question(question):
            recent_context = " ".join(message_history[-3:])  # Last 3 messages
            enhanced_question = f"{question} (referring to: {recent_context})"
        
        return enhanced_question

    async def prune_context_for_performance(
        self, 
        context: ConversationContext, 
        current_question: str
    ) -> ConversationContext:
        """Prune context for performance optimization."""
        # Calculate relevance scores
        relevance_scores = self._calculate_relevance_scores(context.context_window, current_question)
        
        # Keep only highly relevant content
        pruned_content = self._keep_relevant_content(
            context.context_window, 
            relevance_scores, 
            max_tokens=2000
        )
        
        return ConversationContext(
            session_id=context.session_id,
            context_window=pruned_content,
            relevant_documents=context.relevant_documents,
            context_metadata={
                **context.context_metadata,
                "pruned": True,
                "original_length": len(context.context_window),
                "pruned_length": len(pruned_content)
            }
        )

    def extract_entities_from_context(self, context: str) -> List[str]:
        """Extract entities from conversation context."""
        # Simple entity extraction - in real implementation would use NLP
        entities = []
        
        # Common AI/ML terms
        ai_terms = [
            "machine learning", "artificial intelligence", "neural networks", 
            "deep learning", "natural language processing", "computer vision",
            "reinforcement learning", "supervised learning", "unsupervised learning"
        ]
        
        context_lower = context.lower()
        for term in ai_terms:
            if term in context_lower:
                entities.append(term)
        
        return list(set(entities))

    def is_ambiguous_question(self, question: str) -> bool:
        """Check if a question is ambiguous and needs context."""
        ambiguous_indicators = [
            "it", "this", "that", "they", "them", "these", "those",
            "how does it work", "what about it", "tell me more",
            "how do they relate", "what's next"
        ]
        
        question_lower = question.lower()
        return any(indicator in question_lower for indicator in ambiguous_indicators)

    def _build_context_window(self, messages: List[ConversationMessageOutput]) -> str:
        """Build context window from messages."""
        if not messages:
            return ""
        
        # Take last 10 messages for context
        recent_messages = messages[-10:]
        context_parts = []
        
        for msg in recent_messages:
            if msg.role == "user":
                context_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                context_parts.append(f"Assistant: {msg.content}")
        
        return " ".join(context_parts)

    def _extract_entities_from_context(self, context: str) -> List[str]:
        """Extract entities from context."""
        return self.extract_entities_from_context(context)

    def _extract_topics_from_context(self, context: str) -> List[str]:
        """Extract topics from context."""
        # Simple topic extraction
        topics = []
        
        # Look for question patterns
        question_patterns = [
            r"what is (.+?)\?",
            r"how does (.+?) work",
            r"explain (.+?)",
            r"tell me about (.+?)"
        ]
        
        for pattern in question_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            topics.extend(matches)
        
        return list(set(topics))

    def _calculate_relevance_scores(
        self, 
        context: str, 
        current_question: str
    ) -> Dict[str, float]:
        """Calculate relevance scores for context sentences."""
        sentences = context.split('.')
        scores = {}
        
        question_words = set(current_question.lower().split())
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            sentence_words = set(sentence.lower().split())
            # Simple relevance: word overlap
            overlap = len(question_words.intersection(sentence_words))
            scores[sentence] = overlap / len(question_words) if question_words else 0.0
        
        return scores

    def _keep_relevant_content(
        self, 
        content: str, 
        relevance_scores: Dict[str, float], 
        max_tokens: int
    ) -> str:
        """Keep only relevant content based on scores."""
        sentences = content.split('.')
        relevant_sentences = []
        current_tokens = 0
        
        # Sort by relevance score
        sorted_sentences = sorted(
            sentences, 
            key=lambda s: relevance_scores.get(s, 0.0), 
            reverse=True
        )
        
        for sentence in sorted_sentences:
            if not sentence.strip():
                continue
                
            sentence_tokens = len(sentence.split())
            if current_tokens + sentence_tokens <= max_tokens:
                relevant_sentences.append(sentence)
                current_tokens += sentence_tokens
            else:
                break
        
        return '. '.join(relevant_sentences)

    async def resolve_pronouns(self, question: str, context: str) -> str:
        """Resolve pronouns in question using context."""
        # Simple pronoun resolution
        if "it" in question.lower():
            # Find the most recent noun in context
            words = context.split()
            nouns = [word for word in words if word.isalpha() and len(word) > 3]
            if nouns:
                question = question.replace("it", nouns[-1])
        
        return question

    async def detect_follow_up_question(self, question: str) -> bool:
        """Detect if question is a follow-up."""
        follow_up_indicators = [
            "tell me more", "what about", "how about", "what else",
            "can you explain", "go on", "continue", "and then"
        ]
        
        question_lower = question.lower()
        return any(indicator in question_lower for indicator in follow_up_indicators)

    async def extract_entity_relationships(self, entities: List[str]) -> Dict[str, List[str]]:
        """Extract relationships between entities."""
        # Simple relationship extraction
        relationships = {}
        
        for entity in entities:
            related = []
            for other_entity in entities:
                if entity != other_entity:
                    # Simple co-occurrence based relationship
                    if entity in other_entity or other_entity in entity:
                        related.append(other_entity)
            relationships[entity] = related
        
        return relationships

    async def extract_temporal_context(self, context: str) -> Dict[str, Any]:
        """Extract temporal context from conversation."""
        # Simple temporal extraction
        temporal_indicators = [
            "earlier", "before", "previously", "first", "initially",
            "then", "next", "after", "later", "finally"
        ]
        
        found_indicators = [
            indicator for indicator in temporal_indicators 
            if indicator in context.lower()
        ]
        
        return {
            "temporal_indicators": found_indicators,
            "has_temporal_structure": len(found_indicators) > 0
        }

    async def calculate_semantic_similarity(
        self, 
        text1: str, 
        text2: str
    ) -> float:
        """Calculate semantic similarity between texts."""
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    async def extract_conversation_topic(self, context: str) -> str:
        """Extract the main topic of the conversation."""
        # Simple topic extraction based on most frequent terms
        words = context.lower().split()
        
        # Remove common words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "is", "are", "was", "were", "be", "been", "have",
            "has", "had", "do", "does", "did", "will", "would", "could", "should"
        }
        
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
        
        if not filtered_words:
            return "general discussion"
        
        # Return most frequent word as topic
        word_counts = {}
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        return max(word_counts, key=word_counts.get)
