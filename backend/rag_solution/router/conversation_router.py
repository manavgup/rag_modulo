"""Conversation router for REST API conversation management.

This router provides REST endpoints for conversation session CRUD operations,
message history retrieval, and conversation management functionality.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.config import get_settings
from rag_solution.core.dependencies import get_current_user
from rag_solution.core.exceptions import NotFoundError, ValidationError
from rag_solution.file_management.database import get_db
from rag_solution.schemas.conversation_schema import (
    ConversationMessageOutput,
    ConversationSessionCreateInput,
    ConversationSessionInput,
    ConversationSessionOutput,
    SessionStatistics,
)
from rag_solution.services.conversation_service import ConversationService

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
    updates: dict,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionOutput:
    """Update conversation session.

    Args:
        session_id: Conversation session ID
        updates: Fields to update
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
