"""
Podcast generation API endpoints.

Provides RESTful API for podcast generation, status checking, and management.
"""

import io
import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from core.custom_exceptions import NotFoundError, ValidationError
from core.identity_service import IdentityService
from rag_solution.core.dependencies import get_current_user
from rag_solution.file_management.database import get_db
from rag_solution.schemas.podcast_schema import (
    PodcastAudioGenerationInput,
    PodcastGenerationInput,
    PodcastGenerationOutput,
    PodcastListResponse,
    PodcastScriptGenerationInput,
    PodcastScriptOutput,
)
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.podcast_service import PodcastService
from rag_solution.services.search_service import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/podcasts", tags=["podcasts"])

# Media type constants for audio formats
AUDIO_MEDIA_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
}


def _extract_user_id_from_jwt(current_user: dict) -> UUID:
    """
    Extract and validate user_id from JWT token with HTTP exception handling.

    This is a thin wrapper around IdentityService.extract_user_id_from_jwt()
    that converts ValueError to HTTPException for FastAPI endpoints.

    Args:
        current_user: JWT token payload from get_current_user() dependency

    Returns:
        UUID: Validated user ID as UUID object

    Raises:
        HTTPException 401: If user_id is missing or has invalid format
    """
    try:
        return IdentityService.extract_user_id_from_jwt(current_user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


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
    user_id = _extract_user_id_from_jwt(current_user)

    # Create validated input with authenticated user_id (ensures user_id is never None)
    validated_input = podcast_input.model_copy(update={"user_id": user_id})

    return await podcast_service.generate_podcast(validated_input, background_tasks)


@router.post(
    "/generate-script",
    response_model=PodcastScriptOutput,
    status_code=200,
    summary="Generate podcast script only (no audio)",
    description="""
    Generate podcast script without audio synthesis.

    **Use Cases:**
    - Validate script quality before committing to TTS
    - Faster iteration (script generation ~30s vs full podcast ~90s)
    - Cost savings (skip TTS API calls during development/testing)
    - Script editing workflows (generate → review → edit → synthesize)

    **Quality Metrics Returned:**
    - word_count: Actual words in generated script
    - target_word_count: Expected words for duration
    - estimated_duration_minutes: Actual duration estimate (word_count / 150)
    - has_proper_format: Whether script has HOST/EXPERT dialogue structure

    **Workflow:**
    1. Call this endpoint to generate script
    2. Review script quality and metrics
    3. If satisfied, call POST /generate with same parameters for full podcast
    4. If not satisfied, adjust parameters and retry

    Cost: ~$0.01-0.05 (LLM only, no TTS)
    Time: ~30 seconds
    """,
)
async def generate_script_only(
    script_input: PodcastScriptGenerationInput,
    podcast_service: Annotated[PodcastService, Depends(get_podcast_service)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> PodcastScriptOutput:
    """
    Generate podcast script without audio synthesis.

    Args:
        script_input: Script generation request
        podcast_service: Injected podcast service
        current_user: Authenticated user from JWT token

    Returns:
        PodcastScriptOutput with generated script and quality metrics

    Raises:
        HTTPException 400: Validation failed
        HTTPException 401: Unauthorized
        HTTPException 404: Collection not found
        HTTPException 500: Internal error
    """
    # Set user_id from authenticated session
    user_id = _extract_user_id_from_jwt(current_user)

    # Create validated input with authenticated user_id
    validated_input = script_input.model_copy(update={"user_id": user_id})

    try:
        return await podcast_service.generate_script_only(validated_input)
    except Exception as e:
        logger.exception("Failed to generate script for collection %s", script_input.collection_id)
        raise HTTPException(
            status_code=500,
            detail=f"Script generation failed: {e!s}",
        ) from e


@router.post(
    "/script-to-audio",
    response_model=PodcastGenerationOutput,
    status_code=202,
    summary="Generate audio from existing script (no script generation)",
    description="""
    Convert an existing podcast script to audio without LLM script generation.

    **Use Cases:**
    - Generate audio from previously generated script
    - Generate audio from user-edited script
    - Re-generate audio with different voices/settings
    - Faster/cheaper processing (TTS only, no LLM)

    **Workflow:**
    1. Call POST /generate-script to get script
    2. Review/edit script (optional)
    3. Call this endpoint to convert script to audio

    **Benefits:**
    - **Quality Control**: Review scripts before paying for TTS
    - **Cost Savings**: ~60% cheaper (TTS only, no LLM)
    - **User Editing**: Let users edit scripts before audio generation
    - **Faster Processing**: ~30-90 seconds (vs ~90-120 for full generation)

    **Requirements:**
    - Script must have HOST/EXPERT dialogue format
    - Collection must exist and user must have access

    **Cost (OpenAI TTS):**
    - 5 min: ~$0.05
    - 15 min: ~$0.15
    - 30 min: ~$0.30

    **Time:** ~30-90 seconds depending on duration

    The request is processed asynchronously:
    1. Returns immediately with status QUEUED
    2. Background task generates audio (30-90 seconds)
    3. Poll GET /podcasts/{podcast_id} to check status
    4. When COMPLETED, audio_url contains the podcast file
    """,
)
async def generate_audio_from_script(
    audio_input: PodcastAudioGenerationInput,
    background_tasks: BackgroundTasks,
    podcast_service: Annotated[PodcastService, Depends(get_podcast_service)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> PodcastGenerationOutput:
    """
    Generate podcast audio from existing script (skip LLM script generation).

    Args:
        audio_input: Audio generation request with script
        background_tasks: FastAPI background tasks
        podcast_service: Injected podcast service
        current_user: Authenticated user from JWT token

    Returns:
        PodcastGenerationOutput with QUEUED status and podcast_id

    Raises:
        HTTPException 400: Validation failed or invalid script format
        HTTPException 401: Unauthorized
        HTTPException 404: Collection not found
        HTTPException 500: Internal error
    """
    # Set user_id from authenticated session
    user_id = _extract_user_id_from_jwt(current_user)

    # Create validated input with authenticated user_id
    validated_input = audio_input.model_copy(update={"user_id": user_id})

    try:
        return await podcast_service.generate_audio_from_script(validated_input, background_tasks)
    except ValidationError as e:
        logger.exception("Validation error for script-to-audio")
        raise HTTPException(
            status_code=400,
            detail=f"Validation failed: {e!s}",
        ) from e
    except NotFoundError as e:
        logger.exception("Collection not found for script-to-audio")
        raise HTTPException(
            status_code=404,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Failed to generate audio from script for collection %s", audio_input.collection_id)
        raise HTTPException(
            status_code=500,
            detail=f"Audio generation failed: {e!s}",
        ) from e


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
    user_id = _extract_user_id_from_jwt(current_user)
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
    # Get user_id from current_user, with proper UUID validation
    # Standardize JWT user ID extraction - use "uuid" as the standard field
    user_id_str = current_user.get("uuid")

    if not user_id_str:
        raise HTTPException(status_code=401, detail="User ID not found in authentication context")

    # Validate UUID format
    try:
        user_id = UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
    except (ValueError, AttributeError) as e:
        logger.error("Invalid user ID format: %s", user_id_str)
        raise HTTPException(status_code=401, detail=f"Invalid user ID format: {user_id_str}") from e

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
    user_id = _extract_user_id_from_jwt(current_user)
    await podcast_service.delete_podcast(podcast_id, user_id)


# Valid voice IDs for OpenAI TTS voices
VALID_VOICE_IDS = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}


def _parse_range_header(range_header: str, file_size: int) -> tuple[int, int] | None:
    """
    Parse HTTP Range header.

    Args:
        range_header: Range header value (e.g., "bytes=0-1023")
        file_size: Total file size

    Returns:
        Tuple of (start, end) byte positions, or None if invalid
    """
    try:
        # Range header format: "bytes=start-end"
        if not range_header.startswith("bytes="):
            return None

        range_spec = range_header[6:]  # Remove "bytes=" prefix
        parts = range_spec.split("-")

        if len(parts) != 2:
            return None

        # Parse start and end
        start_str, end_str = parts

        if start_str == "":
            # Suffix range: "-500" means last 500 bytes
            if end_str == "":
                return None
            suffix_length = int(end_str)
            start = max(0, file_size - suffix_length)
            end = file_size - 1
        elif end_str == "":
            # Open range: "500-" means from byte 500 to end
            start = int(start_str)
            end = file_size - 1
        else:
            # Full range: "500-999"
            start = int(start_str)
            end = int(end_str)

        # Validate range
        if start < 0 or end >= file_size or start > end:
            return None

        return (start, end)

    except (ValueError, IndexError):
        return None


@router.get(
    "/{podcast_id}/audio",
    summary="Serve podcast audio file",
    description="""
    Serve the generated podcast audio file.

    This endpoint provides access to the podcast audio file with proper authentication
    and access control. Only the podcast owner can access the audio.

    The response supports:
    - Content streaming for efficient playback
    - HTTP Range requests for seek functionality (RFC 7233)
    - Proper MIME types for different audio formats
    """,
)
async def serve_podcast_audio(
    request: Request,
    podcast_id: UUID4,
    podcast_service: Annotated[PodcastService, Depends(get_podcast_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> Response:
    """
    Serve podcast audio file with Range request support.

    Args:
        request: FastAPI request object (for Range header)
        podcast_id: Podcast UUID
        podcast_service: Injected podcast service
        settings: Application settings
        current_user: Authenticated user from JWT token

    Returns:
        StreamingResponse with audio file (206 for Range, 200 for full)

    Raises:
        HTTPException 401: Unauthorized
        HTTPException 403: Access denied (not podcast owner)
        HTTPException 404: Podcast or audio file not found
        HTTPException 416: Range not satisfiable
    """
    user_id = _extract_user_id_from_jwt(current_user)

    # Get podcast to verify ownership and get audio format
    podcast = await podcast_service.get_podcast(podcast_id, user_id)

    if podcast.status != "completed":
        raise HTTPException(status_code=400, detail=f"Podcast is not ready. Current status: {podcast.status}")

    if not podcast.audio_url:
        raise HTTPException(status_code=404, detail="Audio file not found for this podcast")

    # Construct file path from audio_url
    # audio_url format: "/podcasts/{user_id}/{podcast_id}/audio.{format}"
    base_path = Path(settings.podcast_local_storage_path)

    # Resolve to absolute path to avoid working directory issues
    if not base_path.is_absolute():
        # Use __file__ to get path relative to this router file
        # This is more robust than relying on working directory
        router_file = Path(__file__).resolve()
        project_root = (
            router_file.parent.parent.parent.parent
        )  # rag_solution/router/ -> rag_solution/ -> backend/ -> project_root/
        base_path = (project_root / base_path).resolve()

    # Get format as string (handle both enum and string values)
    audio_format = podcast.format.value if hasattr(podcast.format, "value") else str(podcast.format)
    audio_path = base_path / str(user_id) / str(podcast_id) / f"audio.{audio_format}"

    # Resolve and validate path to prevent directory traversal
    try:
        audio_path = audio_path.resolve(strict=False)
        # Ensure resolved path is within base_path (security check)
        if not str(audio_path).startswith(str(base_path.resolve())):
            logger.error(f"Path traversal attempt detected: {audio_path}")
            raise HTTPException(status_code=403, detail="Access denied")
    except (ValueError, OSError) as e:
        logger.error(f"Invalid path resolution: {e}")
        raise HTTPException(status_code=400, detail="Invalid file path") from e

    # Debug logging
    logger.info(f"Looking for audio file at: {audio_path}")
    logger.info(f"File exists: {audio_path.exists()}")
    if not audio_path.exists():
        logger.error(f"Audio file not found. Path checked: {audio_path}")
        logger.error(f"Base path: {base_path}, User ID: {user_id}, Podcast ID: {podcast_id}")
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    # Get file size
    file_size = audio_path.stat().st_size

    # Determine media type based on format
    media_type = AUDIO_MEDIA_TYPES.get(audio_format, "audio/mpeg")

    # Parse Range header
    range_header = request.headers.get("range")

    if range_header:
        # Handle Range request
        byte_range = _parse_range_header(range_header, file_size)

        if byte_range is None:
            # Invalid range
            raise HTTPException(
                status_code=416,
                detail="Range not satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"},
            )

        start, end = byte_range
        content_length = end - start + 1

        # Create streaming response for byte range
        def iter_file():
            """Stream file chunk by chunk."""
            with open(audio_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                chunk_size = 65536  # 64KB chunks

                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        # Return 206 Partial Content
        return StreamingResponse(
            iter_file(),
            status_code=206,
            media_type=media_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'inline; filename="{podcast.title or f"podcast-{str(podcast_id)[:8]}"}.{podcast.format}"',
            },
        )
    else:
        # No Range header - serve full file
        def iter_full_file():
            """Stream full file chunk by chunk."""
            with open(audio_path, "rb") as f:
                chunk_size = 65536  # 64KB chunks
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        # Return 200 OK with full content
        return StreamingResponse(
            iter_full_file(),
            status_code=200,
            media_type=media_type,
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'inline; filename="{podcast.title or f"podcast-{str(podcast_id)[:8]}"}.{podcast.format}"',
            },
        )


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
