"""
Podcast generation API endpoints.

Provides RESTful API for podcast generation, status checking, and management.
"""

import io
import logging
from typing import Annotated

from core.config import Settings, get_settings
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from rag_solution.file_management.database import get_db
from rag_solution.generation.audio.factory import AudioProviderFactory
from rag_solution.schemas.podcast_schema import (
    PodcastGenerationInput,
    PodcastGenerationOutput,
    PodcastListResponse,
)
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.podcast_service import PodcastService
from rag_solution.services.search_service import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/podcasts", tags=["podcasts"])


# Dependency to get PodcastService
async def get_podcast_service(
    session: Annotated[AsyncSession, Depends(get_db)],
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
    # TODO: Inject services properly via dependency injection
    # For now, create inline (will need refactoring)
    collection_service = CollectionService(session, settings)  # type: ignore[arg-type]
    search_service = SearchService(session, settings)  # type: ignore[arg-type]

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
) -> PodcastGenerationOutput:
    """
    Generate podcast from collection (async).

    Args:
        podcast_input: Podcast generation request
        background_tasks: FastAPI background tasks
        podcast_service: Injected podcast service

    Returns:
        PodcastGenerationOutput with QUEUED status and podcast_id

    Raises:
        HTTPException 400: Validation failed
        HTTPException 404: Collection not found
        HTTPException 500: Internal error
    """
    return await podcast_service.generate_podcast(podcast_input, background_tasks)


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
    user_id: Annotated[
        UUID4,
        Query(description="User ID for access control"),
    ],
    podcast_service: Annotated[PodcastService, Depends(get_podcast_service)],
) -> PodcastGenerationOutput:
    """
    Get podcast by ID.

    Args:
        podcast_id: Podcast UUID
        user_id: Requesting user UUID
        podcast_service: Injected podcast service

    Returns:
        PodcastGenerationOutput with current status

    Raises:
        HTTPException 404: Podcast not found
        HTTPException 403: Access denied
    """
    return await podcast_service.get_podcast(podcast_id, user_id)


@router.get(
    "/",
    response_model=PodcastListResponse,
    summary="List user's podcasts",
    description="""
    List all podcasts for a user, ordered by creation date (newest first).

    Supports pagination via limit and offset parameters.
    """,
)
async def list_podcasts(
    user_id: Annotated[
        UUID4,
        Query(description="User ID to list podcasts for"),
    ],
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of results"),
    ] = 100,
    offset: Annotated[
        int,
        Query(ge=0, description="Pagination offset"),
    ] = 0,
    podcast_service: PodcastService = Depends(get_podcast_service),
) -> PodcastListResponse:
    """
    List user's podcasts.

    Args:
        user_id: User UUID
        limit: Maximum results (1-100)
        offset: Pagination offset
        podcast_service: Injected podcast service

    Returns:
        PodcastListResponse with list of podcasts
    """
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
    user_id: Annotated[
        UUID4,
        Query(description="User ID for access control"),
    ],
    podcast_service: Annotated[PodcastService, Depends(get_podcast_service)],
) -> None:
    """
    Delete podcast.

    Args:
        podcast_id: Podcast UUID
        user_id: Requesting user UUID
        podcast_service: Injected podcast service

    Returns:
        None (204 No Content)

    Raises:
        HTTPException 404: Podcast not found
        HTTPException 403: Access denied
    """
    await podcast_service.delete_podcast(podcast_id, user_id)


@router.get(
    "/voice-preview/{voice_id}",
    summary="Get a voice preview",
    description="Returns a short audio preview of a specific voice.",
    response_class=StreamingResponse,
)
async def get_voice_preview(
    voice_id: str,
    podcast_service: Annotated[PodcastService, Depends(get_podcast_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    """
    Get a voice preview.
    Args:
        voice_id: The ID of the voice to preview.
        podcast_service: Injected podcast service.
        settings: Application settings.
    Returns:
        A streaming response with the audio preview.
    """
    audio_provider = AudioProviderFactory.create_provider(
        provider_type=settings.podcast_audio_provider,
        settings=settings,
    )
    available_voices = await audio_provider.list_available_voices()
    valid_voice_ids = [v["voice_id"] for v in available_voices]
    if voice_id not in valid_voice_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid voice_id. Must be one of: {valid_voice_ids}",
        )
    try:
        audio_bytes = await podcast_service.generate_voice_preview(voice_id)
        return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"Error generating voice preview: {e}")
        raise HTTPException(status_code=500, detail="Error generating voice preview")
