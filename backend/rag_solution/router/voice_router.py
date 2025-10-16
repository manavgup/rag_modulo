"""
Voice management API endpoints.

Provides RESTful API for custom voice upload, processing, and management.
"""

import logging
from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from rag_solution.core.dependencies import get_current_user
from rag_solution.file_management.database import get_db
from rag_solution.schemas.voice_schema import (
    VoiceListResponse,
    VoiceOutput,
    VoiceProcessingInput,
    VoiceUpdateInput,
    VoiceUploadInput,
)
from rag_solution.services.voice_service import VoiceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voices", tags=["voices"])

# Media type constants for audio formats
AUDIO_MEDIA_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
}


# Dependency to get VoiceService
def get_voice_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VoiceService:
    """
    Create VoiceService instance with dependencies.

    Args:
        session: Database session
        settings: Application settings

    Returns:
        Configured VoiceService
    """
    return VoiceService(session=session, settings=settings)


@router.post(
    "/upload",
    response_model=VoiceOutput,
    status_code=201,
    summary="Upload voice sample for custom voice",
    description="""
    Upload a voice sample file to create a custom voice for podcast generation.

    **Requirements**:
    - Audio file in supported format (MP3, WAV, M4A, FLAC, OGG)
    - File size: max 10 MB
    - Sample duration: 5 seconds to 5 minutes recommended
    - Clear audio quality, minimal background noise

    **Process**:
    1. Upload voice sample with metadata
    2. File is stored and voice record created (status: UPLOADING)
    3. Call POST /voices/{voice_id}/process to clone voice with TTS provider
    4. Once status is READY, use in podcast generation

    **Limits**:
    - Maximum 10 voices per user (configurable)
    - Delete unused voices to upload new ones

    **Next Steps**:
    - After upload completes, call POST /voices/{voice_id}/process
    - Select TTS provider (Phase 1: elevenlabs, Phase 2: f5-tts)
    """,
)
async def upload_voice(
    name: Annotated[str, Form(description="Voice name (1-200 characters)")],
    audio_file: Annotated[UploadFile, File(description="Voice sample audio file")],
    voice_service: Annotated[VoiceService, Depends(get_voice_service)],
    current_user: Annotated[dict, Depends(get_current_user)],
    description: Annotated[str | None, Form(description="Optional voice description (max 1000 characters)")] = None,
    gender: Annotated[str, Form(description="Voice gender: male, female, or neutral")] = "neutral",
) -> VoiceOutput:
    """
    Upload voice sample file.

    Args:
        name: Voice name
        audio_file: Voice sample file
        description: Optional description
        gender: Voice gender classification
        voice_service: Injected voice service
        current_user: Authenticated user from JWT token

    Returns:
        VoiceOutput with UPLOADING status

    Raises:
        HTTPException 400: Validation failed (invalid format, file too large, voice limit exceeded)
        HTTPException 401: Unauthorized
        HTTPException 413: File too large
        HTTPException 415: Unsupported media type
        HTTPException 500: Internal error
    """
    # Set user_id from authenticated session
    user_id_from_token = current_user.get("user_id")

    if not user_id_from_token:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in authentication token",
        )

    # Create voice upload input
    voice_input = VoiceUploadInput(
        user_id=user_id_from_token,
        name=name,
        description=description,
        gender=gender,
    )

    return await voice_service.upload_voice(voice_input, audio_file)


@router.post(
    "/{voice_id}/process",
    response_model=VoiceOutput,
    status_code=202,
    summary="Process voice with TTS provider for voice cloning",
    description="""
    Process uploaded voice sample with a TTS provider to create a cloned voice.

    **Phase 1: ElevenLabs** (Current)
    - Provider: `elevenlabs`
    - Processing time: ~30 seconds
    - Cost: ~$0.30 per voice cloning
    - Quality: 5/5 (industry-leading)

    **Phase 2: F5-TTS** (Future)
    - Provider: `f5-tts`
    - Processing time: instant (zero-shot)
    - Cost: self-hosted (no per-voice cost)
    - Quality: 4/5 (very good)

    **Workflow**:
    1. Upload voice sample: POST /voices/upload
    2. Process voice: POST /voices/{voice_id}/process (this endpoint)
    3. Wait for status to become READY: GET /voices/{voice_id}
    4. Use in podcast: Include voice_id in podcast generation request

    **Status Progression**:
    - UPLOADING → PROCESSING → READY
    - If processing fails: UPLOADING → PROCESSING → FAILED (check error_message)

    **Requirements**:
    - Voice must be in UPLOADING status
    - Provider must be configured and available
    """,
)
async def process_voice(
    voice_id: UUID4,
    processing_input: VoiceProcessingInput,
    voice_service: Annotated[VoiceService, Depends(get_voice_service)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> VoiceOutput:
    """
    Process voice with TTS provider.

    Args:
        voice_id: Voice UUID
        processing_input: Processing request (provider name)
        voice_service: Injected voice service
        current_user: Authenticated user from JWT token

    Returns:
        VoiceOutput with PROCESSING status

    Raises:
        HTTPException 400: Unsupported provider or voice not in uploadable state
        HTTPException 401: Unauthorized
        HTTPException 403: Access denied (not voice owner)
        HTTPException 404: Voice not found
        HTTPException 409: Voice already processed or processing
        HTTPException 500: Processing failed
    """
    user_id = current_user.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in authentication token",
        )

    return await voice_service.process_voice(voice_id, processing_input, user_id)


@router.get(
    "/",
    response_model=VoiceListResponse,
    summary="List user's custom voices",
    description="""
    List all custom voices owned by the authenticated user.

    Voices are ordered by creation date (newest first).

    **Pagination**:
    - Use `limit` and `offset` parameters
    - Default: returns up to 100 voices
    - Max limit: 100 voices per request

    **Voice Status**:
    - UPLOADING: File uploaded, not yet processed
    - PROCESSING: Voice being cloned by TTS provider
    - READY: Voice ready to use in podcasts
    - FAILED: Processing failed (see error_message)

    **Filtering** (future):
    - Filter by status: `?status=ready`
    - Filter by gender: `?gender=male`
    - Search by name: `?search=narrator`
    """,
)
async def list_voices(
    voice_service: Annotated[VoiceService, Depends(get_voice_service)],
    current_user: Annotated[dict, Depends(get_current_user)],
    limit: int = 100,
    offset: int = 0,
) -> VoiceListResponse:
    """
    List user's voices with pagination.

    Args:
        limit: Maximum results (1-100, default 100)
        offset: Pagination offset (default 0)
        voice_service: Injected voice service
        current_user: Authenticated user from JWT token

    Returns:
        VoiceListResponse with voices and total count

    Raises:
        HTTPException 400: Invalid pagination parameters
        HTTPException 401: Unauthorized
    """
    user_id = current_user.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in authentication token",
        )

    return await voice_service.list_user_voices(user_id, limit, offset)


@router.get(
    "/{voice_id}",
    response_model=VoiceOutput,
    summary="Get voice details",
    description="""
    Get details of a specific custom voice.

    **Includes**:
    - Voice metadata (name, description, gender)
    - Processing status and provider information
    - Quality score (if available)
    - Usage statistics (times_used counter)
    - Error message (if processing failed)
    - Timestamps (created_at, updated_at, processed_at)

    **Use Cases**:
    - Check voice processing status
    - Verify voice is ready before podcast generation
    - Debug voice processing failures
    - Track voice usage statistics
    """,
)
async def get_voice(
    voice_id: UUID4,
    voice_service: Annotated[VoiceService, Depends(get_voice_service)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> VoiceOutput:
    """
    Get voice by ID.

    Args:
        voice_id: Voice UUID
        voice_service: Injected voice service
        current_user: Authenticated user from JWT token

    Returns:
        VoiceOutput with voice details

    Raises:
        HTTPException 401: Unauthorized
        HTTPException 403: Access denied (not voice owner)
        HTTPException 404: Voice not found
    """
    user_id = current_user.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in authentication token",
        )

    return await voice_service.get_voice(voice_id, user_id)


@router.patch(
    "/{voice_id}",
    response_model=VoiceOutput,
    summary="Update voice metadata",
    description="""
    Update voice name, description, or gender classification.

    **Editable Fields**:
    - `name`: Voice name (1-200 characters)
    - `description`: Voice description (optional, max 1000 characters)
    - `gender`: Voice gender (male, female, neutral)

    **Non-Editable**:
    - Voice sample file (upload new voice instead)
    - Processing status (managed by system)
    - Provider information (set during processing)
    - Usage statistics (tracked automatically)

    **Use Cases**:
    - Fix typos in voice name
    - Add/update voice description
    - Correct gender classification
    - Organize voices for better management

    All fields are optional - only send fields you want to update.
    """,
)
async def update_voice(
    voice_id: UUID4,
    update_input: VoiceUpdateInput,
    voice_service: Annotated[VoiceService, Depends(get_voice_service)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> VoiceOutput:
    """
    Update voice metadata.

    Args:
        voice_id: Voice UUID
        update_input: Update request (all fields optional)
        voice_service: Injected voice service
        current_user: Authenticated user from JWT token

    Returns:
        Updated VoiceOutput

    Raises:
        HTTPException 400: Validation failed (invalid name, gender, etc.)
        HTTPException 401: Unauthorized
        HTTPException 403: Access denied (not voice owner)
        HTTPException 404: Voice not found
        HTTPException 500: Update failed
    """
    user_id = current_user.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in authentication token",
        )

    return await voice_service.update_voice(voice_id, update_input, user_id)


@router.delete(
    "/{voice_id}",
    status_code=204,
    summary="Delete voice",
    description="""
    Delete a custom voice and its associated sample file.

    **This Operation**:
    1. Deletes voice sample file from storage
    2. Deletes voice record from database
    3. Cannot be undone

    **Important Notes**:
    - Existing podcasts using this voice are NOT affected
    - Podcasts retain their generated audio
    - Cannot delete voice if currently being used in active podcast generation
    - Frees up quota for uploading new voices

    **Best Practices**:
    - Delete unused voices to manage quota
    - Download voice sample before deletion if needed
    - Verify voice is not in use before deletion

    **Warning**: This operation cannot be undone. The voice sample file and
    database record will be permanently deleted.
    """,
)
async def delete_voice(
    voice_id: UUID4,
    voice_service: Annotated[VoiceService, Depends(get_voice_service)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> None:
    """
    Delete voice.

    Args:
        voice_id: Voice UUID
        voice_service: Injected voice service
        current_user: Authenticated user from JWT token

    Returns:
        None (204 No Content)

    Raises:
        HTTPException 401: Unauthorized
        HTTPException 403: Access denied (not voice owner)
        HTTPException 404: Voice not found
        HTTPException 409: Voice currently in use
        HTTPException 500: Deletion failed
    """
    user_id = current_user.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in authentication token",
        )

    await voice_service.delete_voice(voice_id, user_id)


@router.get(
    "/{voice_id}/sample",
    summary="Download or stream voice sample file",
    description="""
    Download or stream the voice sample audio file.

    **Features**:
    - Supports HTTP Range requests for seeking/streaming
    - Proper MIME types for different audio formats
    - Access control (only voice owner can download)
    - Efficient streaming for large files

    **Use Cases**:
    - Preview voice sample before using in podcast
    - Download voice sample for backup
    - Stream voice sample in web player
    - Verify audio quality before processing

    **HTTP Range Support**:
    - Request: `Range: bytes=0-1023`
    - Response: 206 Partial Content
    - Use for audio seeking in media players

    **Audio Formats**:
    - MP3: audio/mpeg
    - WAV: audio/wav
    - M4A: audio/mp4
    - FLAC: audio/flac
    - OGG: audio/ogg
    """,
)
async def download_voice_sample(
    request: Request,
    voice_id: UUID4,
    voice_service: Annotated[VoiceService, Depends(get_voice_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> StreamingResponse:
    """
    Download or stream voice sample file.

    Args:
        request: FastAPI request (for Range header)
        voice_id: Voice UUID
        voice_service: Injected voice service
        settings: Application settings
        current_user: Authenticated user from JWT token

    Returns:
        StreamingResponse with audio file (206 for Range, 200 for full)

    Raises:
        HTTPException 401: Unauthorized
        HTTPException 403: Access denied (not voice owner)
        HTTPException 404: Voice or sample file not found
        HTTPException 416: Range not satisfiable
    """
    user_id = current_user.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in authentication token",
        )

    # Get voice to verify ownership
    voice = await voice_service.get_voice(voice_id, user_id)

    # Get voice sample file path
    from rag_solution.services.file_management_service import FileManagementService

    file_service = FileManagementService(voice_service.session, settings)

    # user_id might already be a UUID or string - handle both cases
    user_uuid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
    file_path = file_service.get_voice_file_path(user_id=user_uuid, voice_id=voice_id)

    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Voice sample file not found",
        )

    # Get file size and format
    file_size = file_path.stat().st_size
    audio_format = file_path.suffix[1:]  # Remove leading dot

    # Determine media type
    media_type = AUDIO_MEDIA_TYPES.get(audio_format, "application/octet-stream")

    # Parse Range header
    range_header = request.headers.get("range")

    if range_header:
        # Handle Range request (for streaming/seeking)
        try:
            # Parse range: "bytes=start-end"
            if not range_header.startswith("bytes="):
                raise ValueError("Invalid range format")

            range_spec = range_header[6:]
            parts = range_spec.split("-")

            if len(parts) != 2:
                raise ValueError("Invalid range format")

            start_str, end_str = parts
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1

            # Validate range
            if start < 0 or end >= file_size or start > end:
                raise HTTPException(
                    status_code=416,
                    detail="Range not satisfiable",
                    headers={"Content-Range": f"bytes */{file_size}"},
                )

            content_length = end - start + 1

            # Stream byte range
            def iter_range() -> Generator[bytes, None, None]:
                with open(file_path, "rb") as f:
                    f.seek(start)
                    remaining = content_length
                    chunk_size = 65536  # 64KB chunks

                    while remaining > 0:
                        chunk = f.read(min(chunk_size, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk

            return StreamingResponse(
                iter_range(),
                status_code=206,
                media_type=media_type,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Length": str(content_length),
                    "Accept-Ranges": "bytes",
                    "Content-Disposition": f'inline; filename="{voice.name}.{audio_format}"',
                },
            )

        except (ValueError, IndexError) as e:
            logger.warning("Invalid range header: %s - %s", range_header, e)
            raise HTTPException(
                status_code=416,
                detail="Range not satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"},
            ) from e

    else:
        # No Range header - serve full file
        def iter_file() -> Generator[bytes, None, None]:
            with open(file_path, "rb") as f:
                chunk_size = 65536  # 64KB chunks
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        return StreamingResponse(
            iter_file(),
            status_code=200,
            media_type=media_type,
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'inline; filename="{voice.name}.{audio_format}"',
            },
        )
