"""Question suggestion service for conversation enhancement.

This service generates intelligent follow-up questions based on
conversation context and current message content.
"""

from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.schemas.conversation_schema import (
    ConversationContext,
    QuestionSuggestionInput,
    QuestionSuggestionOutput,
)


class QuestionSuggestionService:
    """Service for generating question suggestions."""

    def __init__(self, db: Session, settings: Settings):
        """Initialize the question suggestion service."""
        self.db = db
        self.settings = settings

    async def generate_suggestions(self, suggestion_input: QuestionSuggestionInput) -> QuestionSuggestionOutput:
        """Generate question suggestions based on context."""
        suggestions = []
        confidence_scores = []
        reasoning = ""

        # Extract context information
        entities = suggestion_input.context.context_metadata.get("extracted_entities", [])
        topics = suggestion_input.context.context_metadata.get("conversation_topics", [])
        current_content = suggestion_input.current_message.lower()

        # Generate suggestions based on context
        if "machine learning" in current_content or "machine learning" in entities:
            suggestions.extend([
                "How does machine learning work?",
                "What are the different types of machine learning?",
                "Can you give me examples of machine learning applications?"
            ])
            confidence_scores.extend([0.9, 0.8, 0.7])
            reasoning = "Generated ML-related questions based on detected machine learning context"

        elif "neural networks" in current_content or "neural networks" in entities:
            suggestions.extend([
                "How do neural networks learn?",
                "What is the difference between shallow and deep neural networks?",
                "What are some common neural network architectures?"
            ])
            confidence_scores.extend([0.9, 0.8, 0.7])
            reasoning = "Generated neural network questions based on detected context"

        elif "artificial intelligence" in current_content or "ai" in entities:
            suggestions.extend([
                "What are the main branches of AI?",
                "How is AI different from machine learning?",
                "What are the current limitations of AI?"
            ])
            confidence_scores.extend([0.9, 0.8, 0.7])
            reasoning = "Generated AI-related questions based on detected context"

        elif "deep learning" in current_content or "deep learning" in entities:
            suggestions.extend([
                "What makes deep learning different from traditional machine learning?",
                "What are the advantages and disadvantages of deep learning?",
                "What are some popular deep learning frameworks?"
            ])
            confidence_scores.extend([0.9, 0.8, 0.7])
            reasoning = "Generated deep learning questions based on detected context"

        else:
            # Generic suggestions based on conversation flow
            suggestions.extend([
                "Can you explain that in more detail?",
                "What are the practical applications of this?",
                "How does this relate to other concepts we've discussed?"
            ])
            confidence_scores.extend([0.6, 0.5, 0.4])
            reasoning = "Generated generic follow-up questions based on conversation flow"

        # Limit to requested number of suggestions
        suggestions = suggestions[:suggestion_input.max_suggestions]
        confidence_scores = confidence_scores[:suggestion_input.max_suggestions]

        return QuestionSuggestionOutput(
            suggestions=suggestions,
            confidence_scores=confidence_scores,
            reasoning=reasoning
        )

    async def generate_contextual_suggestions(
        self, 
        session_id: UUID, 
        current_message: str, 
        context: ConversationContext
    ) -> List[str]:
        """Generate contextual suggestions based on conversation history."""
        suggestions = []
        
        # Analyze conversation context
        entities = context.context_metadata.get("extracted_entities", [])
        topics = context.context_metadata.get("conversation_topics", [])
        
        # Generate suggestions based on entities
        for entity in entities[:3]:  # Top 3 entities
            if entity == "machine learning":
                suggestions.append("What are the different algorithms used in machine learning?")
            elif entity == "neural networks":
                suggestions.append("How do neural networks process information?")
            elif entity == "deep learning":
                suggestions.append("What are the key components of a deep learning model?")
        
        # Generate suggestions based on topics
        for topic in topics[:2]:  # Top 2 topics
            suggestions.append(f"Can you elaborate on {topic}?")
            suggestions.append(f"What are the key concepts related to {topic}?")
        
        # Add general follow-up questions
        suggestions.extend([
            "What are the real-world applications of this?",
            "How does this compare to other approaches?",
            "What are the challenges in this area?"
        ])
        
        return suggestions[:5]  # Return top 5 suggestions

    async def generate_exploratory_suggestions(
        self, 
        current_message: str, 
        context: ConversationContext
    ) -> List[str]:
        """Generate exploratory questions to deepen the conversation."""
        suggestions = []
        
        # Analyze the current message for question patterns
        if "what" in current_message.lower():
            suggestions.extend([
                "How does this work in practice?",
                "What are the implications of this?",
                "What are the alternatives to this approach?"
            ])
        
        elif "how" in current_message.lower():
            suggestions.extend([
                "What are the steps involved?",
                "What tools or techniques are used?",
                "What are the challenges in this process?"
            ])
        
        elif "why" in current_message.lower():
            suggestions.extend([
                "What are the benefits of this approach?",
                "What problems does this solve?",
                "What are the trade-offs involved?"
            ])
        
        else:
            # General exploratory questions
            suggestions.extend([
                "What are the key principles behind this?",
                "How does this relate to other concepts?",
                "What are the practical considerations?"
            ])
        
        return suggestions

    async def generate_comparison_suggestions(
        self, 
        entities: List[str]
    ) -> List[str]:
        """Generate comparison questions based on entities."""
        suggestions = []
        
        if len(entities) >= 2:
            # Generate comparison questions
            entity1, entity2 = entities[0], entities[1]
            suggestions.extend([
                f"What are the similarities between {entity1} and {entity2}?",
                f"How do {entity1} and {entity2} differ?",
                f"When would you use {entity1} vs {entity2}?"
            ])
        
        return suggestions

    async def generate_application_suggestions(
        self, 
        topics: List[str]
    ) -> List[str]:
        """Generate application-focused questions."""
        suggestions = []
        
        for topic in topics:
            suggestions.extend([
                f"What are the real-world applications of {topic}?",
                f"How is {topic} used in industry?",
                f"What problems can {topic} solve?"
            ])
        
        return suggestions

    async def analyze_conversation_depth(self, context: ConversationContext) -> str:
        """Analyze the depth of the conversation."""
        message_count = context.context_metadata.get("message_count", 0)
        entities = context.context_metadata.get("extracted_entities", [])
        
        if message_count < 5:
            return "shallow"
        elif message_count < 15:
            return "moderate"
        else:
            return "deep"

    async def generate_depth_appropriate_suggestions(
        self, 
        depth: str, 
        current_message: str
    ) -> List[str]:
        """Generate suggestions appropriate for conversation depth."""
        if depth == "shallow":
            return [
                "Can you explain this in more detail?",
                "What are the basic concepts here?",
                "How does this work at a high level?"
            ]
        elif depth == "moderate":
            return [
                "What are the technical details?",
                "How does this compare to other approaches?",
                "What are the practical considerations?"
            ]
        else:  # deep
            return [
                "What are the advanced techniques?",
                "What are the current research directions?",
                "What are the limitations and challenges?"
            ]

    async def generate_learning_path_suggestions(
        self, 
        context: ConversationContext
    ) -> List[str]:
        """Generate suggestions for a learning path."""
        entities = context.context_metadata.get("extracted_entities", [])
        suggestions = []
        
        # Create a learning progression
        if "machine learning" in entities and "neural networks" not in entities:
            suggestions.append("What are neural networks and how do they relate to machine learning?")
        
        if "neural networks" in entities and "deep learning" not in entities:
            suggestions.append("How does deep learning extend neural networks?")
        
        if "deep learning" in entities and "computer vision" not in entities:
            suggestions.append("What are some applications of deep learning like computer vision?")
        
        return suggestions
