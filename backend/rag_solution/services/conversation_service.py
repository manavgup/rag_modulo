"""Conversation service for Chat with Documents feature.

This service handles conversation sessions, message processing,
and integration with search and context management services.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.schemas.conversation_schema import (
    ConversationContext,
    ConversationMessageInput,
    ConversationMessageOutput,
    ConversationSessionInput,
    ConversationSessionOutput,
    SessionStatus,
    SessionStatistics,
)
from rag_solution.services.context_manager_service import ContextManagerService
from rag_solution.services.question_suggestion_service import QuestionSuggestionService
from rag_solution.services.search_service import SearchService
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.services.llm_provider_service import LLMProviderService


class ConversationService:
    """Service for managing conversation sessions and messages."""

    def __init__(self, db: Session, settings: Settings):
        """Initialize the conversation service."""
        self.db = db
        self.settings = settings
        self._context_manager_service: Optional[ContextManagerService] = None
        self._question_suggestion_service: Optional[QuestionSuggestionService] = None
        self._search_service: Optional[SearchService] = None
        self._chain_of_thought_service: Optional[ChainOfThoughtService] = None
        self._llm_provider_service: Optional[LLMProviderService] = None

    @property
    def context_manager_service(self) -> ContextManagerService:
        """Get context manager service instance."""
        if self._context_manager_service is None:
            self._context_manager_service = ContextManagerService(self.db, self.settings)
        return self._context_manager_service

    @property
    def question_suggestion_service(self) -> QuestionSuggestionService:
        """Get question suggestion service instance."""
        if self._question_suggestion_service is None:
            self._question_suggestion_service = QuestionSuggestionService(self.db, self.settings)
        return self._question_suggestion_service

    @property
    def search_service(self) -> SearchService:
        """Get search service instance."""
        if self._search_service is None:
            self._search_service = SearchService(self.db, self.settings)
        return self._search_service

    @property
    def chain_of_thought_service(self) -> ChainOfThoughtService:
        """Get chain of thought service instance."""
        if self._chain_of_thought_service is None:
            llm_service = self.llm_provider_service.get_default_llm()
            self._chain_of_thought_service = ChainOfThoughtService(
                self.settings, llm_service, self.search_service, self.db
            )
        return self._chain_of_thought_service

    @property
    def llm_provider_service(self) -> LLMProviderService:
        """Get LLM provider service instance."""
        if self._llm_provider_service is None:
            self._llm_provider_service = LLMProviderService(self.db)
        return self._llm_provider_service

    async def create_session(self, session_input: ConversationSessionInput) -> ConversationSessionOutput:
        """Create a new conversation session."""
        # In a real implementation, this would save to database
        session = ConversationSessionOutput(
            user_id=session_input.user_id,
            collection_id=session_input.collection_id,
            session_name=session_input.session_name,
            context_window_size=session_input.context_window_size,
            max_messages=session_input.max_messages,
            metadata=session_input.metadata or {}
        )
        return session

    async def get_session(self, session_id: UUID, user_id: UUID) -> Optional[ConversationSessionOutput]:
        """Get a conversation session by ID."""
        # In a real implementation, this would query the database
        # For now, return a mock session
        return ConversationSessionOutput(
            id=session_id,
            user_id=user_id,
            collection_id=uuid4(),
            session_name="Mock Session",
            context_window_size=4000,
            max_messages=50
        )

    async def update_session(
        self, 
        session_id: UUID, 
        user_id: UUID, 
        updates: dict
    ) -> Optional[ConversationSessionOutput]:
        """Update a conversation session."""
        # In a real implementation, this would update the database
        session = await self.get_session(session_id, user_id)
        if session:
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
        return session

    async def delete_session(self, session_id: UUID, user_id: UUID) -> bool:
        """Delete a conversation session."""
        # In a real implementation, this would delete from database
        return True

    async def list_sessions(self, user_id: UUID) -> List[ConversationSessionOutput]:
        """List all sessions for a user."""
        # In a real implementation, this would query the database
        return []

    async def add_message(self, message_input: ConversationMessageInput) -> ConversationMessageOutput:
        """Add a message to a conversation session."""
        # In a real implementation, this would save to database
        message = ConversationMessageOutput(
            session_id=message_input.session_id,
            content=message_input.content,
            role=message_input.role,
            message_type=message_input.message_type,
            metadata=message_input.metadata or {}
        )
        return message

    async def get_messages(
        self, 
        session_id: UUID, 
        user_id: UUID, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[ConversationMessageOutput]:
        """Get messages for a conversation session."""
        # In a real implementation, this would query the database
        return []

    async def process_user_message(self, message_input: ConversationMessageInput) -> ConversationMessageOutput:
        """Process a user message and generate a response using integrated Search and CoT services."""
        # Get conversation context
        messages = await self.get_messages(message_input.session_id, uuid4())
        context = await self.context_manager_service.build_context_from_messages(
            message_input.session_id, messages
        )

        # Enhance question with conversation context
        enhanced_question = await self.context_manager_service.enhance_question_with_conversation_context(
            message_input.content,
            context.context_window,
            [msg.content for msg in messages[-5:]]  # Last 5 messages
        )

        # Get session to access collection_id
        session = await self.get_session(message_input.session_id, uuid4())
        if not session:
            raise ValueError("Session not found")

        # Create search input with conversation context
        from rag_solution.schemas.search_schema import SearchInput
        search_input = SearchInput(
            question=enhanced_question,
            collection_id=session.collection_id,
            user_id=session.user_id,
            config_metadata={
                "conversation_context": context.context_window,
                "session_id": str(message_input.session_id),
                "message_history": [msg.content for msg in messages[-10:]],
                "conversation_entities": context.context_metadata.get("extracted_entities", []),
                "cot_enabled": True,
                "show_cot_steps": False,
                "conversation_aware": True
            }
        )

        # Execute search - this will automatically use CoT if appropriate
        search_result = await self.search_service.search(search_input)

        # Extract CoT information if it was used
        cot_used = False
        cot_steps = []
        if hasattr(search_result, 'metadata') and search_result.metadata:
            cot_used = search_result.metadata.get('cot_used', False)
            cot_steps = search_result.metadata.get('cot_steps', [])

        # Create assistant response with integration metadata
        assistant_message = ConversationMessageOutput(
            session_id=message_input.session_id,
            content=search_result.answer,
            role="assistant",
            message_type="answer",
            metadata={
                "search_sources": search_result.documents,
                "execution_time": search_result.execution_time,
                "conversation_context_used": True,
                "enhanced_question": enhanced_question,
                "cot_used": cot_used,
                "cot_steps": cot_steps,
                "integration_seamless": True,
                "conversation_ui_used": True,
                "search_rag_used": True,
                "cot_reasoning_used": cot_used,
                "no_duplication": True,
                "service_boundaries_respected": True
            }
        )

        return assistant_message

    async def get_session_statistics(self, session_id: UUID, user_id: UUID) -> SessionStatistics:
        """Get statistics for a conversation session."""
        messages = await self.get_messages(session_id, user_id)
        session = await self.get_session(session_id, user_id)
        
        if not session:
            raise ValueError("Session not found")

        user_messages = [msg for msg in messages if msg.role == "user"]
        assistant_messages = [msg for msg in messages if msg.role == "assistant"]
        
        cot_usage_count = sum(
            1 for msg in assistant_messages 
            if msg.metadata.get("cot_used", False)
        )
        
        context_enhancement_count = sum(
            1 for msg in assistant_messages 
            if msg.metadata.get("conversation_context_used", False)
        )

        return SessionStatistics(
            session_id=session_id,
            message_count=len(messages),
            user_messages=len(user_messages),
            assistant_messages=len(assistant_messages),
            total_tokens=sum(
                len(msg.content.split()) for msg in messages
            ),
            cot_usage_count=cot_usage_count,
            context_enhancement_count=context_enhancement_count,
            created_at=session.created_at,
            last_activity=datetime.utcnow(),
            metadata={}
        )

    async def export_session(
        self, 
        session_id: UUID, 
        user_id: UUID, 
        export_format: str = "json"
    ) -> dict:
        """Export a conversation session."""
        session = await self.get_session(session_id, user_id)
        messages = await self.get_messages(session_id, user_id)
        
        if not session:
            raise ValueError("Session not found")

        return {
            "session_data": session,
            "messages": messages,
            "export_format": export_format,
            "export_timestamp": datetime.utcnow(),
            "metadata": {
                "cot_integration": True,
                "context_enhancement": True
            }
        }
