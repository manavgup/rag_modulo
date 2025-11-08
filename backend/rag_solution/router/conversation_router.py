"""Unified conversation router for REST API conversation management.

This router provides comprehensive REST endpoints for conversation session management,
including CRUD operations, message processing, summarization, and conversation analytics.

This is the unified router that consolidates the previous /api/conversations and /api/chat
endpoints. All conversation functionality is now available through /api/conversations.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.config import get_settings
from rag_solution.core.dependencies import get_current_user
from rag_solution.core.exceptions import NotFoundError, ValidationError
from rag_solution.file_management.database import get_db
from rag_solution.schemas.conversation_schema import (
    ContextSummarizationInput,
    ContextSummarizationOutput,
    ConversationExportInput,
    ConversationExportOutput,
    ConversationMessageInput,
    ConversationMessageOutput,
    ConversationSessionCreateInput,
    ConversationSessionInput,
    ConversationSessionOutput,
    ConversationSuggestionInput,
    ConversationSuggestionOutput,
    ConversationSummaryInput,
    ConversationSummaryOutput,
    SessionStatistics,
    SummarizationConfigInput,
)
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.services.conversation_context_service import ConversationContextService
from rag_solution.services.conversation_service import ConversationService
from rag_solution.services.conversation_summarization_service import ConversationSummarizationService
from rag_solution.services.entity_extraction_service import EntityExtractionService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.message_processing_orchestrator import MessageProcessingOrchestrator
from rag_solution.services.search_service import SearchService
from rag_solution.services.token_tracking_service import TokenTrackingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    """Get conversation service instance.

    Args:
        db: Database session dependency

    Returns:
        ConversationService instance
    """
    from rag_solution.repository.conversation_repository import ConversationRepository
    from rag_solution.services.question_service import QuestionService

    settings = get_settings()
    repository = ConversationRepository(db)
    question_service = QuestionService(db, settings)

    return ConversationService(db, settings, repository, question_service)


def get_summarization_service(db: Session = Depends(get_db)) -> ConversationSummarizationService:
    """Get conversation summarization service instance.

    Args:
        db: Database session dependency

    Returns:
        ConversationSummarizationService instance
    """
    settings = get_settings()
    return ConversationSummarizationService(db, settings)


def get_message_processing_orchestrator(
    db: Session = Depends(get_db),
) -> MessageProcessingOrchestrator:
    """Get message processing orchestrator instance with all dependencies.

    This factory method creates a MessageProcessingOrchestrator with all required
    services, following dependency injection best practices.

    Args:
        db: Database session dependency

    Returns:
        MessageProcessingOrchestrator: Orchestrator for processing user messages
    """
    from rag_solution.repository.conversation_repository import ConversationRepository

    settings = get_settings()

    # Create repository layer
    repository = ConversationRepository(db)

    # Create service dependencies
    search_service = SearchService(db, settings)
    entity_extraction_service = EntityExtractionService(db, settings)
    context_service = ConversationContextService(db, settings, entity_extraction_service)
    token_tracking_service = TokenTrackingService(db, settings)
    llm_provider_service = LLMProviderService(db)

    # Create CoT service (optional)
    cot_service = None
    try:
        provider = llm_provider_service.get_default_provider()
        if provider and hasattr(provider, "llm_base"):
            cot_service = ChainOfThoughtService(settings, provider.llm_base, search_service, db)
    except Exception as e:
        # CoT is optional, continue without it
        logger.warning("Failed to initialize Chain of Thought service: %s", str(e))

    return MessageProcessingOrchestrator(
        db=db,
        settings=settings,
        conversation_repository=repository,
        search_service=search_service,
        context_service=context_service,
        token_tracking_service=token_tracking_service,
        llm_provider_service=llm_provider_service,
        chain_of_thought_service=cot_service,
    )


@router.get("", response_model=list[ConversationSessionOutput])
async def list_conversations(
    user_id: UUID | None = None,
    collection_id: UUID | None = None,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationSessionOutput]:
    """List user's conversation sessions.

    Args:
        user_id: Optional user ID filter (defaults to current user)
        collection_id: Optional collection ID filter
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        List of conversation sessions

    Raises:
        HTTPException: For authentication or validation errors
    """
    try:
        # Use current user if no user_id provided
        if user_id:
            target_user_id = user_id
        else:
            # Validate UUID format before conversion
            uuid_str = current_user.get("uuid", "")
            if not uuid_str:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="User UUID not found in authentication context"
                )
            try:
                target_user_id = UUID(uuid_str)
            except ValueError as ve:
                logger.error("Invalid UUID format: %s", uuid_str)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid user UUID format: {uuid_str}"
                ) from ve

        # Get all sessions for user
        sessions = await conversation_service.list_sessions(target_user_id)

        # Filter by collection_id if provided
        if collection_id:
            sessions = [s for s in sessions if s.collection_id == collection_id]

        logger.info("Listed %d conversations for user %s", len(sessions), str(target_user_id))
        return sessions

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing conversations: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list conversations: {e!s}"
        ) from e


@router.post("", response_model=ConversationSessionOutput, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    session_data: ConversationSessionCreateInput,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionOutput:
    """Create a new conversation session.

    Args:
        session_data: Conversation session creation data
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        Created conversation session

    Raises:
        HTTPException: For validation or creation errors
    """
    try:
        # Convert to full input schema with user_id from current user
        full_session_data = ConversationSessionInput(
            user_id=UUID(current_user["uuid"]),
            collection_id=session_data.collection_id,
            session_name=session_data.session_name,
            context_window_size=session_data.context_window_size,
            max_messages=session_data.max_messages,
            is_archived=session_data.is_archived,
            is_pinned=session_data.is_pinned,
            metadata=session_data.metadata,
        )

        session = await conversation_service.create_session(full_session_data)
        logger.info("Created conversation session %s for user %s", str(session.id), str(session.user_id))
        return session

    except ValidationError as e:
        logger.warning("Validation error creating conversation: %s", str(e))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        logger.error("Error creating conversation: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create conversation: {e!s}"
        ) from e


@router.get("/{session_id}", response_model=ConversationSessionOutput)
async def get_conversation(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionOutput:
    """Get conversation session details.

    Args:
        session_id: Conversation session ID
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        Conversation session details

    Raises:
        HTTPException: For not found or access errors
    """
    try:
        user_id = UUID(current_user["uuid"])
        session = await conversation_service.get_session(session_id, user_id)
        logger.info("Retrieved conversation session %s for user %s", str(session_id), str(user_id))
        return session

    except NotFoundError as e:
        logger.warning("Conversation session not found: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found") from e
    except Exception as e:
        logger.error("Error getting conversation: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get conversation: {e!s}"
        ) from e


@router.put("/{session_id}", response_model=ConversationSessionOutput)
async def update_conversation(
    session_id: UUID,
    updates: dict[str, Any],  # TODO: Replace with ConversationSessionUpdateInput schema for type safety
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionOutput:
    """Update conversation session.

    Args:
        session_id: Conversation session ID
        updates: Fields to update. Accepted fields:
            - session_name (str): Update session name
            - status (SessionStatus): Update session status
            - is_archived (bool): Archive/unarchive session
            - is_pinned (bool): Pin/unpin session
            - metadata (dict): Update metadata
            Note: user_id, collection_id, created_at cannot be updated
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        Updated conversation session

    Raises:
        HTTPException: For not found or validation errors
    """
    try:
        user_id = UUID(current_user["uuid"])
        session = await conversation_service.update_session(session_id, user_id, updates)
        logger.info("Updated conversation session %s for user %s", str(session_id), str(user_id))
        return session

    except NotFoundError as e:
        logger.warning("Conversation session not found for update: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found") from e
    except ValidationError as e:
        logger.warning("Validation error updating conversation: %s", str(e))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        logger.error("Error updating conversation: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update conversation: {e!s}"
        ) from e


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> None:
    """Delete conversation session.

    Args:
        session_id: Conversation session ID
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Raises:
        HTTPException: For not found or deletion errors
    """
    try:
        user_id = UUID(current_user["uuid"])
        success = await conversation_service.delete_session(session_id, user_id)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found")

        logger.info("Deleted conversation session %s for user %s", str(session_id), str(user_id))

    except NotFoundError as e:
        logger.warning("Conversation session not found for deletion: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found") from e
    except Exception as e:
        logger.error("Error deleting conversation: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete conversation: {e!s}"
        ) from e


@router.get("/{session_id}/messages", response_model=list[ConversationMessageOutput])
async def get_conversation_messages(
    session_id: UUID,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationMessageOutput]:
    """Get conversation message history.

    Args:
        session_id: Conversation session ID
        limit: Maximum number of messages to return
        offset: Number of messages to skip
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        List of conversation messages

    Raises:
        HTTPException: For not found or access errors
    """
    try:
        user_id = UUID(current_user["uuid"])

        # Verify session exists and user has access
        await conversation_service.get_session(session_id, user_id)

        # Get messages with pagination
        messages = await conversation_service.get_messages(
            session_id=session_id, user_id=user_id, limit=limit, offset=offset
        )

        logger.info("Retrieved %d messages for session %s", len(messages), str(session_id))
        return messages

    except NotFoundError as e:
        logger.warning("Conversation session not found for messages: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found") from e
    except Exception as e:
        logger.error("Error getting conversation messages: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get conversation messages: {e!s}"
        ) from e


@router.get("/{session_id}/statistics", response_model=SessionStatistics)
async def get_conversation_statistics(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> SessionStatistics:
    """Get conversation session statistics.

    Args:
        session_id: Conversation session ID
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        Session statistics

    Raises:
        HTTPException: For not found or access errors
    """
    try:
        user_id = UUID(current_user["uuid"])
        stats = await conversation_service.get_session_statistics(session_id, user_id)
        logger.info("Retrieved statistics for session %s", str(session_id))
        return stats

    except NotFoundError as e:
        logger.warning("Conversation session not found for statistics: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found") from e
    except Exception as e:
        logger.error("Error getting conversation statistics: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get conversation statistics: {e!s}"
        ) from e


@router.post("/{session_id}/export")
async def export_conversation(
    session_id: UUID,
    export_format: str = "json",
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> dict:
    """Export conversation session.

    Args:
        session_id: Conversation session ID
        export_format: Export format (json, txt, etc.)
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        Exported conversation data

    Raises:
        HTTPException: For not found or export errors
    """
    try:
        user_id = UUID(current_user["uuid"])
        export_data = await conversation_service.export_session(session_id, user_id, export_format)
        logger.info("Exported session %s for user %s", str(session_id), str(user_id))
        return export_data

    except NotFoundError as e:
        logger.warning("Conversation session not found for export: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found") from e
    except Exception as e:
        logger.error("Error exporting conversation: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to export conversation: {e!s}"
        ) from e


@router.post("/{session_id}/archive", response_model=ConversationSessionOutput)
async def archive_conversation(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionOutput:
    """Archive conversation session.

    Args:
        session_id: Conversation session ID
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        Archived conversation session

    Raises:
        HTTPException: For not found or archive errors
    """
    try:
        user_id = UUID(current_user["uuid"])
        session = await conversation_service.archive_session(session_id, user_id)
        logger.info("Archived session %s for user %s", str(session_id), str(user_id))
        return session

    except NotFoundError as e:
        logger.warning("Conversation session not found for archive: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found") from e
    except Exception as e:
        logger.error("Error archiving conversation: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to archive conversation: {e!s}"
        ) from e


@router.post("/{session_id}/restore", response_model=ConversationSessionOutput)
async def restore_conversation(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionOutput:
    """Restore archived conversation session.

    Args:
        session_id: Conversation session ID
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        Restored conversation session

    Raises:
        HTTPException: For not found or restore errors
    """
    try:
        user_id = UUID(current_user["uuid"])
        session = await conversation_service.restore_session(session_id, user_id)
        logger.info("Restored session %s for user %s", str(session_id), str(user_id))
        return session

    except NotFoundError as e:
        logger.warning("Conversation session not found for restore: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found") from e
    except Exception as e:
        logger.error("Error restoring conversation: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to restore conversation: {e!s}"
        ) from e


@router.get("/{session_id}/summary")
async def get_conversation_summary(
    session_id: UUID,
    summary_type: str = "brief",
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> dict:
    """Get conversation summary.

    Args:
        session_id: Conversation session ID
        summary_type: Type of summary (brief, detailed, key_points)
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        Conversation summary

    Raises:
        HTTPException: For not found or summary generation errors
    """
    try:
        user_id = UUID(current_user["uuid"])
        summary = await conversation_service.generate_conversation_summary(session_id, user_id, summary_type)
        logger.info("Generated %s summary for session %s", summary_type, str(session_id))
        return summary

    except NotFoundError as e:
        logger.warning("Conversation session not found for summary: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found") from e
    except Exception as e:
        logger.error("Error generating conversation summary: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate conversation summary: {e!s}"
        ) from e


@router.post("/{session_id}/generate-name", response_model=ConversationSessionOutput)
async def generate_conversation_name(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionOutput:
    """Generate and apply an automatic name for a conversation.

    Args:
        session_id: Conversation session ID
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        Updated conversation session with new name

    Raises:
        HTTPException: For not found or generation errors
    """
    try:
        user_id = UUID(current_user["uuid"])

        # Generate new name and update the conversation
        new_name = await conversation_service.generate_conversation_name(session_id, user_id)
        await conversation_service.update_conversation_name(session_id, user_id)

        # Get the updated session to return
        updated_session = await conversation_service.get_session(session_id, user_id)
        logger.info("Generated name '%s' for session %s", new_name, str(session_id))
        return updated_session

    except NotFoundError as e:
        logger.warning("Conversation session not found for name generation: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found") from e
    except Exception as e:
        logger.error("Error generating conversation name: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate conversation name: {e!s}"
        ) from e


@router.post("/bulk-rename")
async def bulk_rename_conversations(
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> dict:
    """Apply automatic naming to all conversations for the current user.

    Args:
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        Summary of bulk rename operation

    Raises:
        HTTPException: For bulk rename errors
    """
    try:
        user_id = UUID(current_user["uuid"])

        # Apply automatic naming to all user conversations
        results = await conversation_service.update_all_conversation_names(user_id)

        logger.info("Bulk renamed %d conversations for user %s", results["updated"], str(user_id))
        return results

    except Exception as e:
        logger.error("Error in bulk conversation rename: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to bulk rename conversations: {e!s}"
        ) from e


# Message Management Endpoints


@router.post("/{session_id}/messages", response_model=ConversationMessageOutput)
async def add_message(
    session_id: UUID,
    message_data: ConversationMessageInput,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationMessageOutput:
    """Add a message to a conversation session.

    SECURITY: Requires authentication. User must own the session.

    Args:
        session_id: Conversation session ID
        message_data: Message data to add
        current_user: Current authenticated user
        conversation_service: Conversation service dependency

    Returns:
        Created message

    Raises:
        HTTPException: For access denied or validation errors
    """
    try:
        # SECURITY FIX: Verify user owns the session
        user_id = UUID(current_user["uuid"])
        session = await conversation_service.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Ensure session_id matches
        message_data.session_id = session_id
        message = await conversation_service.add_message(message_data)
        logger.info("Added message to session %s for user %s", str(session_id), str(user_id))
        return message

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error adding message: %s", str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/{session_id}/process", response_model=ConversationMessageOutput)
async def process_user_message(
    session_id: UUID,
    message_data: ConversationMessageInput,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
    orchestrator: MessageProcessingOrchestrator = Depends(get_message_processing_orchestrator),
) -> ConversationMessageOutput:
    """Process a user message and generate a response.

    SECURITY: Requires authentication. User must own the session.
    CRITICAL: This endpoint consumes LLM API tokens and must be protected.

    This is the main endpoint for chat functionality, using MessageProcessingOrchestrator
    for proper service separation and comprehensive message processing.

    Args:
        session_id: Conversation session ID
        message_data: User message to process
        current_user: Current authenticated user
        conversation_service: Conversation service dependency
        orchestrator: Message processing orchestrator

    Returns:
        Assistant response message

    Raises:
        HTTPException: For access denied, not found, or processing errors
    """
    try:
        # SECURITY FIX: Verify user owns the session (prevent unauthorized LLM usage)
        user_id = UUID(current_user["uuid"])
        session = await conversation_service.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Ensure session_id matches
        message_data.session_id = session_id

        # Use MessageProcessingOrchestrator for comprehensive message processing
        response = await orchestrator.process_user_message(message_data)
        logger.info("Processed message for session %s for user %s", str(session_id), str(user_id))
        return response

    except HTTPException:
        raise
    except NotFoundError as e:
        logger.warning("Session not found for message processing: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error("Error processing message: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process message: {e!s}"
        ) from e


# Summarization Endpoints


@router.post("/{session_id}/summaries", response_model=ConversationSummaryOutput)
async def create_summary(
    session_id: UUID,
    summary_input: ConversationSummaryInput,
    current_user: dict = Depends(get_current_user),
    summarization_service: ConversationSummarizationService = Depends(get_summarization_service),
) -> ConversationSummaryOutput:
    """Create a conversation summary for the specified session.

    This endpoint allows users to create summaries of conversation sessions,
    which can help manage context windows and extract key insights.

    Args:
        session_id: Conversation session ID
        summary_input: Summary creation parameters
        current_user: Current authenticated user
        summarization_service: Summarization service dependency

    Returns:
        Created summary

    Raises:
        HTTPException: For not found or validation errors
    """
    try:
        # Ensure session_id matches the URL parameter
        summary_input.session_id = session_id

        user_id = UUID(current_user["uuid"])
        summary = await summarization_service.create_summary(summary_input, user_id)
        logger.info("Created summary for session %s for user %s", str(session_id), str(user_id))
        return summary

    except NotFoundError as e:
        logger.warning("Session not found for summary creation: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error("Error creating summary: %s", str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{session_id}/summaries", response_model=list[ConversationSummaryOutput])
async def get_session_summaries(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of summaries to return"),
    summarization_service: ConversationSummarizationService = Depends(get_summarization_service),
) -> list[ConversationSummaryOutput]:
    """Get conversation summaries for a session.

    Returns a list of conversation summaries for the specified session,
    ordered by creation date (newest first).

    Args:
        session_id: Conversation session ID
        current_user: Current authenticated user
        limit: Maximum number of summaries to return
        summarization_service: Summarization service dependency

    Returns:
        List of summaries

    Raises:
        HTTPException: For not found or access errors
    """
    try:
        user_id = UUID(current_user["uuid"])
        summaries = await summarization_service.get_session_summaries(session_id, user_id, limit)
        logger.info("Retrieved %d summaries for session %s", len(summaries), str(session_id))
        return summaries

    except NotFoundError as e:
        logger.warning("Session not found for summaries: %s", str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error("Error retrieving summaries: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve summaries: {e!s}"
        ) from e


@router.post("/{session_id}/context-summarization", response_model=ContextSummarizationOutput)
async def summarize_for_context(
    session_id: UUID,
    summarization_input: ContextSummarizationInput,
    current_user: dict = Depends(get_current_user),
    summarization_service: ConversationSummarizationService = Depends(get_summarization_service),
) -> ContextSummarizationOutput:
    """Perform context-aware summarization for conversation management.

    This endpoint is designed for automatic context window management,
    summarizing older messages while preserving recent conversation flow.

    Args:
        session_id: Conversation session ID
        summarization_input: Context summarization parameters
        current_user: Current authenticated user (unused but required for auth)
        summarization_service: Summarization service dependency

    Returns:
        Context summarization result

    Raises:
        HTTPException: For validation or processing errors
    """
    try:
        # Ensure session_id matches
        summarization_input.session_id = session_id

        result = await summarization_service.summarize_for_context_management(summarization_input)
        logger.info("Created context summarization for session %s", str(session_id))
        return result

    except Exception as e:
        logger.error("Error in context summarization: %s", str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{session_id}/context-threshold")
async def check_context_threshold(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
    config: SummarizationConfigInput = Depends(),
    summarization_service: ConversationSummarizationService = Depends(get_summarization_service),
) -> dict:
    """Check if a session has reached the context window threshold for summarization.

    This endpoint helps determine when automatic summarization should be triggered
    based on context window usage and configuration thresholds.

    Args:
        session_id: Conversation session ID
        current_user: Current authenticated user (unused but required for auth)
        config: Summarization configuration
        summarization_service: Summarization service dependency

    Returns:
        Context threshold check result

    Raises:
        HTTPException: For processing errors
    """
    try:
        needs_summarization = await summarization_service.check_context_window_threshold(session_id, config)
        return {
            "session_id": session_id,
            "needs_summarization": needs_summarization,
            "threshold_config": config.model_dump(),
        }

    except Exception as e:
        logger.error("Error checking context threshold: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to check context threshold: {e!s}"
        ) from e


# Enhanced Question Suggestions


@router.get("/{session_id}/suggestions")
async def get_question_suggestions(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
    _current_message: str = Query(..., description="Current message content"),
    _max_suggestions: int = Query(3, ge=1, le=10, description="Maximum number of suggestions"),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> dict:
    """Get question suggestions for a conversation.

    Note: This endpoint is migrated from /api/chat. Parameters _current_message and
    _max_suggestions are kept for backward compatibility with old client code but are
    not currently used in the suggestion generation logic. Future implementation may
    utilize these parameters for enhanced suggestions.

    Args:
        session_id: Conversation session ID
        current_user: Current authenticated user
        _current_message: Current message content (unused, kept for API compatibility with /api/chat)
        _max_suggestions: Maximum number of suggestions (unused, kept for API compatibility with /api/chat)
        conversation_service: Conversation service dependency

    Returns:
        Question suggestions with confidence scores

    Raises:
        HTTPException: For not found or processing errors
    """
    try:
        user_id = UUID(current_user["uuid"])
        # Get session and context
        session = await conversation_service.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

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
        logger.error("Error generating suggestions: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate suggestions: {e!s}"
        ) from e


@router.post("/{session_id}/conversation-suggestions", response_model=ConversationSuggestionOutput)
async def get_conversation_suggestions(
    session_id: UUID,
    suggestion_input: ConversationSuggestionInput,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSuggestionOutput:
    """Get enhanced question suggestions based on conversation context.

    This endpoint provides context-aware question suggestions that consider
    the full conversation history and document context.

    Note: Currently uses placeholder implementation with security checks.
    Full implementation tracked in issue #558.

    Args:
        session_id: Conversation session ID
        suggestion_input: Suggestion request parameters
        current_user: Current authenticated user
        conversation_service: Conversation service (used for security validation)

    Returns:
        Enhanced conversation suggestions

    Raises:
        HTTPException: For validation errors or access denied
    """
    try:
        user_id = current_user["user_id"]

        # SECURITY FIX: Verify user has access to this session before proceeding
        # This prevents unauthorized access to session data through placeholder endpoint
        try:
            session = await conversation_service.get_session(session_id, user_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session {session_id} not found or access denied",
                )
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found") from e

        # Ensure session_id matches
        suggestion_input.session_id = session_id

        # TODO: This is a placeholder implementation that returns hardcoded suggestions
        # Real implementation should call conversation_service.generate_suggestions()
        # See issue #558 for implementation plan
        # IMPORTANT: This placeholder is safe because we verify session ownership above
        logger.warning(
            "get_conversation_suggestions is using placeholder implementation - "
            "returning hardcoded suggestions for session %s (user %s)",
            session_id,
            user_id,
        )
        return ConversationSuggestionOutput(
            suggestions=["Based on the conversation, what are your next steps?"],
            suggestion_types=["follow_up"],
            confidence_scores=[0.8],
            context_relevance=[0.9],
            document_sources=[[]],
            reasoning="Generated based on conversation context and document analysis (placeholder)",
        )

    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except Exception as e:
        logger.error("Error generating conversation suggestions: %s", str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# Enhanced Export Functionality


@router.post("/{session_id}/enhanced-export", response_model=ConversationExportOutput)
async def export_conversation_enhanced(
    session_id: UUID,
    export_input: ConversationExportInput,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
    summarization_service: ConversationSummarizationService = Depends(get_summarization_service),
) -> ConversationExportOutput:
    """Export conversation with enhanced features including summaries and metadata.

    Note: Uses POST instead of GET because ConversationExportInput contains complex
    filter options (date_range, include_summaries, include_metadata, etc.) that
    exceed typical query parameter complexity. POST with request body is more
    appropriate for this use case per REST best practices.

    This endpoint provides comprehensive conversation export with optional
    summaries, enhanced metadata, and multiple format support.

    Args:
        session_id: Conversation session ID
        export_input: Export configuration parameters
        current_user: Current authenticated user
        conversation_service: Conversation service dependency
        summarization_service: Summarization service dependency

    Returns:
        Enhanced export data

    Raises:
        HTTPException: For not found or export errors
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
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        except HTTPException:
            # Re-raise HTTP exceptions (404, etc.)
            raise
        except NotFoundError as e:
            # Session not found - raise 404
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
        except Exception as e:
            # Unexpected errors should be logged and raised, not masked
            logger.error("Unexpected error retrieving session %s: %s", session_id, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve session data"
            ) from e

        # Get messages
        messages = await conversation_service.get_messages(session_id, user_id)

        # Get summaries if requested
        summaries = []
        if export_input.include_summaries:
            summaries = await summarization_service.get_session_summaries(session_id, user_id, limit=50)

        # Calculate export statistics
        total_tokens = sum(msg.token_count or 0 for msg in messages)

        logger.info("Enhanced export for session %s for user %s", str(session_id), str(user_id))
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
        logger.error("Error in enhanced export: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to export conversation: {e!s}"
        ) from e
