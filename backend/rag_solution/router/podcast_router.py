"""
Podcast generation API endpoints.

Provides RESTful API for podcast generation, status checking, and management.
"""

import io
import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from rag_solution.core.dependencies import get_current_user
from rag_solution.file_management.database import get_db
from rag_solution.schemas.podcast_schema import (
    PodcastGenerationInput,
    PodcastGenerationOutput,
    PodcastListResponse,
)
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.podcast_service import PodcastService
from rag_solution.services.search_service import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/podcasts", tags=["podcasts"])


# Dependency to get PodcastService
def get_podcast_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PodcastService:
    """
    Create PodcastService instance with dependencies.

    Args:
        session: Database session
        settings: Application settings

    Returns:
        Configured PodcastService
    """
    # Create service dependencies
    collection_service = CollectionService(session, settings)
    search_service = SearchService(session, settings)

    return PodcastService(
        session=session,
        collection_service=collection_service,
        search_service=search_service,
    )


@router.post(
    "/generate",
    response_model=PodcastGenerationOutput,
    status_code=202,
    summary="Generate podcast from collection",
    description="""
    Generate a podcast from a document collection using Q&A dialogue format.

    The request is processed asynchronously:
    1. Returns immediately with status QUEUED
    2. Background task generates podcast (1-2 minutes)
    3. Poll GET /podcasts/{podcast_id} to check status
    4. When COMPLETED, audio_url contains the podcast file

    Requirements:
    - Collection must have at least 5 documents (configurable)
    - User cannot have more than 3 concurrent podcast generations

    Cost (OpenAI TTS):
    - SHORT (5 min): ~$0.07
    - MEDIUM (15 min): ~$0.20
    - LONG (30 min): ~$0.41
    - EXTENDED (60 min): ~$0.81
    """,
)
async def generate_podcast(
    podcast_input: PodcastGenerationInput,
    background_tasks: BackgroundTasks,
    podcast_service: Annotated[PodcastService, Depends(get_podcast_service)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> PodcastGenerationOutput:
    """
    Generate podcast from collection (async).

    Args:
        podcast_input: Podcast generation request
        background_tasks: FastAPI background tasks
        podcast_service: Injected podcast service
        current_user: Authenticated user from JWT token

    Returns:
        PodcastGenerationOutput with QUEUED status and podcast_id

    Raises:
        HTTPException 400: Validation failed
        HTTPException 401: Unauthorized
        HTTPException 403: User doesn't own collection
        HTTPException 404: Collection not found
        HTTPException 500: Internal error
    """
    # Set user_id from authenticated session (security best practice)
    # Never trust user_id from request body - always use authenticated session
    user_id_from_token = current_user.get("user_id")

    if not user_id_from_token:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in authentication token",
        )

    # Create validated input with authenticated user_id (ensures user_id is never None)
    validated_input = podcast_input.model_copy(update={"user_id": user_id_from_token})

    return await podcast_service.generate_podcast(validated_input, background_tasks)


@router.get(
    "/{podcast_id}",
    response_model=PodcastGenerationOutput,
    summary="Get podcast status and details",
    description="""
    Get podcast generation status and details.

    Status values:
    - QUEUED: Podcast queued for processing
    - GENERATING: Currently generating (check progress_percentage)
    - COMPLETED: Ready to download (see audio_url)
    - FAILED: Generation failed (see error_message)

    Progress tracking (when GENERATING):
    - progress_percentage: 0-100
    - current_step: retrieving_content, generating_script, parsing_turns,
                    generating_audio, storing_audio
    - step_details: Additional details (e.g., turn progress)
    """,
)
async def get_podcast(
    podcast_id: UUID4,
    podcast_service: Annotated[PodcastService, Depends(get_podcast_service)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> PodcastGenerationOutput:
    """
    Get podcast by ID.

    Args:
        podcast_id: Podcast UUID
        podcast_service: Injected podcast service
        current_user: Authenticated user from JWT token

    Returns:
        PodcastGenerationOutput with current status

    Raises:
        HTTPException 401: Unauthorized
        HTTPException 403: Access denied
        HTTPException 404: Podcast not found
    """
    user_id = current_user.get("user_id")
    return await podcast_service.get_podcast(podcast_id, user_id)


@router.get(
    "/",
    response_model=PodcastListResponse,
    summary="List user's podcasts",
    description="""
    List all podcasts for the authenticated user, ordered by creation date (newest first).

    Supports pagination via limit and offset parameters.
    """,
)
async def list_podcasts(
    podcast_service: Annotated[PodcastService, Depends(get_podcast_service)],
    current_user: Annotated[dict, Depends(get_current_user)],
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of results"),
    ] = 100,
    offset: Annotated[
        int,
        Query(ge=0, description="Pagination offset"),
    ] = 0,
) -> PodcastListResponse:
    """
    List authenticated user's podcasts.

    Args:
        limit: Maximum results (1-100)
        offset: Pagination offset
        podcast_service: Injected podcast service
        current_user: Authenticated user from JWT token

    Returns:
        PodcastListResponse with list of podcasts

    Raises:
        HTTPException 401: Unauthorized
    """
    user_id = current_user.get("user_id")
    return await podcast_service.list_user_podcasts(user_id, limit, offset)


@router.delete(
    "/{podcast_id}",
    status_code=204,
    summary="Delete podcast",
    description="""
    Delete a podcast and its associated audio file.

    This operation:
    1. Deletes the audio file from storage
    2. Deletes the podcast record from database

    Cannot be undone.
    """,
)
async def delete_podcast(
    podcast_id: UUID4,
    podcast_service: Annotated[PodcastService, Depends(get_podcast_service)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> None:
    """
    Delete podcast.

    Args:
        podcast_id: Podcast UUID
        podcast_service: Injected podcast service
        current_user: Authenticated user from JWT token

    Returns:
        None (204 No Content)

    Raises:
        HTTPException 401: Unauthorized
        HTTPException 403: Access denied
        HTTPException 404: Podcast not found
    """
    user_id = current_user.get("user_id")
    await podcast_service.delete_podcast(podcast_id, user_id)


# Valid voice IDs for OpenAI TTS voices
VALID_VOICE_IDS = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}


@router.get(
    "/voice-preview/{voice_id}",
    summary="Get a voice preview",
    description="Generates and returns a short audio preview for a given voice ID.",
    response_class=StreamingResponse,
)
async def get_voice_preview(
    voice_id: str,
    podcast_service: Annotated[PodcastService, Depends(get_podcast_service)],
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """
    Get a voice preview.

    Args:
        voice_id: The ID of the voice to preview. Must be one of: alloy, echo, fable, onyx, nova, shimmer.
        podcast_service: Injected podcast service.
        current_user: Authenticated user (required for access control).

    Returns:
        A streaming response with the audio preview.

    Raises:
        HTTPException 400: Invalid voice_id provided.
        HTTPException 500: Failed to generate voice preview.
    """
    # Validate voice_id
    if voice_id not in VALID_VOICE_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid voice_id '{voice_id}'. Must be one of: {', '.join(sorted(VALID_VOICE_IDS))}",
        )

    audio_bytes = await podcast_service.generate_voice_preview(voice_id)
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
