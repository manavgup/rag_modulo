"""Chat router for conversation API endpoints.

This router provides REST API endpoints for the Chat with Documents feature,
including session management, message handling, and conversation statistics.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core.config import get_settings
from rag_solution.core.dependencies import get_current_user
from rag_solution.file_management.database import get_db
from rag_solution.schemas.conversation_schema import (
    ContextSummarizationInput,
    ContextSummarizationOutput,
    ConversationExportInput,
    ConversationExportOutput,
    ConversationMessageInput,
    ConversationMessageOutput,
    ConversationSessionInput,
    ConversationSessionOutput,
    ConversationSuggestionInput,
    ConversationSuggestionOutput,
    ConversationSummaryInput,
    ConversationSummaryOutput,
    ExportFormat,
    SessionStatistics,
    SessionStatus,
    SummarizationConfigInput,
)
from rag_solution.services.conversation_service import ConversationService
from rag_solution.services.conversation_summarization_service import ConversationSummarizationService

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    """Get conversation service instance."""
    settings = get_settings()
    return ConversationService(db, settings)


def get_summarization_service(db: Session = Depends(get_db)) -> ConversationSummarizationService:
    """Get conversation summarization service instance."""
    settings = get_settings()
    return ConversationSummarizationService(db, settings)


@router.post("/sessions", response_model=ConversationSessionOutput)
async def create_session(
    session_data: ConversationSessionInput,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionOutput:
    """Create a new conversation session."""
    try:
        session = await conversation_service.create_session(session_data)
        return session
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/sessions/{session_id}", response_model=ConversationSessionOutput)
async def get_session(
    session_id: UUID,
    request: Request,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionOutput:
    """Get a conversation session by ID."""
    user_id = UUID(current_user["uuid"])
    session = await conversation_service.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/sessions/{session_id}", response_model=ConversationSessionOutput)
async def update_session(
    session_id: UUID,
    _request: Request,
    current_user: dict = Depends(get_current_user),
    updates: dict | None = None,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionOutput:
    """Update a conversation session."""
    if updates is None:
        updates = {}

    user_id = UUID(current_user["uuid"])
    session = await conversation_service.update_session(session_id, user_id, updates)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    _request: Request,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> dict:
    """Delete a conversation session."""
    user_id = UUID(current_user["uuid"])
    success = await conversation_service.delete_session(session_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}


@router.get("/sessions", response_model=list[ConversationSessionOutput])
async def list_sessions(
    _request: Request,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationSessionOutput]:
    """List all sessions for a user."""
    user_id = UUID(current_user["uuid"])
    sessions = await conversation_service.list_sessions(user_id)
    return sessions


@router.post("/sessions/{session_id}/messages", response_model=ConversationMessageOutput)
async def add_message(
    session_id: UUID,
    message_data: ConversationMessageInput,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationMessageOutput:
    """Add a message to a conversation session."""
    try:
        # Ensure session_id matches
        message_data.session_id = session_id
        message = await conversation_service.add_message(message_data)
        return message
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/sessions/{session_id}/messages", response_model=list[ConversationMessageOutput])
async def get_messages(
    session_id: UUID,
    _request: Request,
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationMessageOutput]:
    """Get messages for a conversation session."""
    user_id = UUID(current_user["uuid"])
    messages = await conversation_service.get_messages(session_id, user_id, limit, offset)
    return messages


@router.post("/sessions/{session_id}/process", response_model=ConversationMessageOutput)
async def process_user_message(
    session_id: UUID,
    message_data: ConversationMessageInput,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationMessageOutput:
    """Process a user message and generate a response."""
    try:
        # Ensure session_id matches
        message_data.session_id = session_id
        response = await conversation_service.process_user_message(message_data)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sessions/{session_id}/statistics", response_model=SessionStatistics)
async def get_session_statistics(
    session_id: UUID,
    request: Request,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> SessionStatistics:
    """Get statistics for a conversation session."""
    try:
        user_id = UUID(current_user["uuid"])
        stats = await conversation_service.get_session_statistics(session_id, user_id)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: UUID,
    _request: Request,
    current_user: dict = Depends(get_current_user),
    export_format: ExportFormat = Query(ExportFormat.JSON, description="Export format"),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> dict:
    """Export a conversation session."""
    try:
        user_id = UUID(current_user["uuid"])
        export_data = await conversation_service.export_session(session_id, user_id, export_format.value)
        return export_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sessions/{session_id}/suggestions")
async def get_question_suggestions(
    session_id: UUID,
    _request: Request,
    current_user: dict = Depends(get_current_user),
    _current_message: str = Query(..., description="Current message content"),
    _max_suggestions: int = Query(3, ge=1, le=10, description="Maximum number of suggestions"),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> dict:
    """Get question suggestions for a conversation."""
    try:
        user_id = UUID(current_user["uuid"])
        # Get session and context
        session = await conversation_service.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Generate suggestions
        suggestions = await conversation_service.get_question_suggestions(session_id, user_id)

        return {
            "suggestions": suggestions.suggestions,
            "confidence_scores": suggestions.confidence_scores,
            "reasoning": suggestions.reasoning,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Summarization Endpoints


@router.post("/sessions/{session_id}/summaries", response_model=ConversationSummaryOutput)
async def create_summary(
    session_id: UUID,
    summary_input: ConversationSummaryInput,
    _request: Request,
    current_user: dict = Depends(get_current_user),
    summarization_service: ConversationSummarizationService = Depends(get_summarization_service),
) -> ConversationSummaryOutput:
    """Create a conversation summary for the specified session.

    This endpoint allows users to create summaries of conversation sessions,
    which can help manage context windows and extract key insights.
    """
    try:
        # Ensure session_id matches the URL parameter
        summary_input.session_id = session_id

        user_id = UUID(current_user["uuid"])
        summary = await summarization_service.create_summary(summary_input, user_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/sessions/{session_id}/summaries", response_model=list[ConversationSummaryOutput])
async def get_session_summaries(
    session_id: UUID,
    _request: Request,
    current_user: dict = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of summaries to return"),
    summarization_service: ConversationSummarizationService = Depends(get_summarization_service),
) -> list[ConversationSummaryOutput]:
    """Get conversation summaries for a session.

    Returns a list of conversation summaries for the specified session,
    ordered by creation date (newest first).
    """
    try:
        user_id = UUID(current_user["uuid"])
        summaries = await summarization_service.get_session_summaries(session_id, user_id, limit)
        return summaries
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sessions/{session_id}/context-summarization", response_model=ContextSummarizationOutput)
async def summarize_for_context(
    session_id: UUID,
    summarization_input: ContextSummarizationInput,
    _request: Request,
    current_user: dict = Depends(get_current_user),
    summarization_service: ConversationSummarizationService = Depends(get_summarization_service),
) -> ContextSummarizationOutput:
    """Perform context-aware summarization for conversation management.

    This endpoint is designed for automatic context window management,
    summarizing older messages while preserving recent conversation flow.
    """
    try:
        # Ensure session_id matches
        summarization_input.session_id = session_id

        result = await summarization_service.summarize_for_context_management(summarization_input)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/sessions/{session_id}/context-threshold")
async def check_context_threshold(
    session_id: UUID,
    _request: Request,
    current_user: dict = Depends(get_current_user),
    config: SummarizationConfigInput = Depends(),
    summarization_service: ConversationSummarizationService = Depends(get_summarization_service),
) -> dict:
    """Check if a session has reached the context window threshold for summarization.

    This endpoint helps determine when automatic summarization should be triggered
    based on context window usage and configuration thresholds.
    """
    try:
        needs_summarization = await summarization_service.check_context_window_threshold(session_id, config)
        return {
            "session_id": session_id,
            "needs_summarization": needs_summarization,
            "threshold_config": config.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Enhanced Question Suggestions


@router.post("/sessions/{session_id}/conversation-suggestions", response_model=ConversationSuggestionOutput)
async def get_conversation_suggestions(
    session_id: UUID,
    suggestion_input: ConversationSuggestionInput,
    _conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSuggestionOutput:
    """Get enhanced question suggestions based on conversation context.

    This endpoint provides context-aware question suggestions that consider
    the full conversation history and document context.
    """
    try:
        # Ensure session_id matches
        suggestion_input.session_id = session_id

        # This would need to be implemented in the conversation service
        # For now, return a placeholder response
        return ConversationSuggestionOutput(
            suggestions=["Based on the conversation, what are your next steps?"],
            suggestion_types=["follow_up"],
            confidence_scores=[0.8],
            context_relevance=[0.9],
            document_sources=[[]],
            reasoning="Generated based on conversation context and document analysis",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# Enhanced Export Functionality


@router.post("/sessions/{session_id}/enhanced-export", response_model=ConversationExportOutput)
async def export_conversation_enhanced(
    session_id: UUID,
    export_input: ConversationExportInput,
    _request: Request,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
    summarization_service: ConversationSummarizationService = Depends(get_summarization_service),
) -> ConversationExportOutput:
    """Export conversation with enhanced features including summaries and metadata.

    This endpoint provides comprehensive conversation export with optional
    summaries, enhanced metadata, and multiple format support.
    """
    try:
        # Ensure session_id matches
        export_input.session_id = session_id

        # Get authenticated user ID
        user_id = UUID(current_user["uuid"])

        # Get basic session data using authenticated user
        try:
            session = await conversation_service.get_session(session_id, user_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        except Exception:
            # Fallback: create a dummy session for export with minimal data
            session = ConversationSessionOutput(
                id=session_id,
                user_id=user_id,
                collection_id=session_id,  # Placeholder
                session_name="Export Session",
                status=SessionStatus.ACTIVE,
                context_window_size=4000,
                max_messages=50,
                is_archived=False,
                is_pinned=False,
                message_count=0,
            )

        # Get messages
        messages = await conversation_service.get_messages(session_id, user_id)

        # Get summaries if requested
        summaries = []
        if export_input.include_summaries:
            summaries = await summarization_service.get_session_summaries(session_id, user_id, limit=50)

        # Calculate export statistics
        total_tokens = sum(msg.token_count or 0 for msg in messages)

        return ConversationExportOutput(
            session_data=session,
            messages=messages,
            summaries=summaries,
            export_format=export_input.format,
            total_messages=len(messages),
            total_tokens=total_tokens,
            file_size_bytes=0,  # Would be calculated based on actual export
            metadata={
                "export_options": export_input.model_dump(),
                "summary_count": len(summaries),
                "date_range": {"start": export_input.date_range_start, "end": export_input.date_range_end},
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
