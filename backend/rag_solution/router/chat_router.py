"""Chat router for conversation API endpoints.

This router provides REST API endpoints for the Chat with Documents feature,
including session management, message handling, and conversation statistics.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.config import get_settings
from rag_solution.file_management.database import get_db
from rag_solution.schemas.conversation_schema import (
    ConversationMessageInput,
    ConversationMessageOutput,
    ConversationSessionInput,
    ConversationSessionOutput,
    ExportFormat,
    SessionStatistics,
)
from rag_solution.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    """Get conversation service instance."""
    settings = get_settings()
    return ConversationService(db, settings)


@router.post("/sessions", response_model=ConversationSessionOutput)
async def create_session(
    session_data: ConversationSessionInput,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> ConversationSessionOutput:
    """Create a new conversation session."""
    try:
        session = await conversation_service.create_session(session_data)
        return session
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{session_id}", response_model=ConversationSessionOutput)
async def get_session(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID"),
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> ConversationSessionOutput:
    """Get a conversation session by ID."""
    session = await conversation_service.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/sessions/{session_id}", response_model=ConversationSessionOutput)
async def update_session(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID"),
    updates: dict = None,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> ConversationSessionOutput:
    """Update a conversation session."""
    if updates is None:
        updates = {}
    
    session = await conversation_service.update_session(session_id, user_id, updates)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID"),
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> dict:
    """Delete a conversation session."""
    success = await conversation_service.delete_session(session_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}


@router.get("/sessions", response_model=List[ConversationSessionOutput])
async def list_sessions(
    user_id: UUID = Query(..., description="User ID"),
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> List[ConversationSessionOutput]:
    """List all sessions for a user."""
    sessions = await conversation_service.list_sessions(user_id)
    return sessions


@router.post("/sessions/{session_id}/messages", response_model=ConversationMessageOutput)
async def add_message(
    session_id: UUID,
    message_data: ConversationMessageInput,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> ConversationMessageOutput:
    """Add a message to a conversation session."""
    try:
        # Ensure session_id matches
        message_data.session_id = session_id
        message = await conversation_service.add_message(message_data)
        return message
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{session_id}/messages", response_model=List[ConversationMessageOutput])
async def get_messages(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> List[ConversationMessageOutput]:
    """Get messages for a conversation session."""
    messages = await conversation_service.get_messages(session_id, user_id, limit, offset)
    return messages


@router.post("/sessions/{session_id}/process", response_model=ConversationMessageOutput)
async def process_user_message(
    session_id: UUID,
    message_data: ConversationMessageInput,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> ConversationMessageOutput:
    """Process a user message and generate a response."""
    try:
        # Ensure session_id matches
        message_data.session_id = session_id
        response = await conversation_service.process_user_message(message_data)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/statistics", response_model=SessionStatistics)
async def get_session_statistics(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID"),
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> SessionStatistics:
    """Get statistics for a conversation session."""
    try:
        stats = await conversation_service.get_session_statistics(session_id, user_id)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID"),
    format: ExportFormat = Query(ExportFormat.JSON, description="Export format"),
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> dict:
    """Export a conversation session."""
    try:
        export_data = await conversation_service.export_session(
            session_id, user_id, format.value
        )
        return export_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/suggestions")
async def get_question_suggestions(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID"),
    current_message: str = Query(..., description="Current message content"),
    max_suggestions: int = Query(3, ge=1, le=10, description="Maximum number of suggestions"),
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> dict:
    """Get question suggestions for a conversation."""
    try:
        # Get session and context
        session = await conversation_service.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = await conversation_service.get_messages(session_id, user_id)
        context = await conversation_service.context_manager_service.build_context_from_messages(
            session_id, messages
        )
        
        # Generate suggestions
        from rag_solution.schemas.conversation_schema import QuestionSuggestionInput
        suggestion_input = QuestionSuggestionInput(
            session_id=session_id,
            current_message=current_message,
            context=context,
            max_suggestions=max_suggestions
        )
        suggestions = await conversation_service.question_suggestion_service.generate_suggestions(suggestion_input)
        
        return {
            "suggestions": suggestions.suggestions,
            "confidence_scores": suggestions.confidence_scores,
            "reasoning": suggestions.reasoning
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
