"""
Audio storage abstraction for podcast audio files.

Provides unified interface for storing podcast audio files across different
storage backends (local filesystem, MinIO, S3, Cloudflare R2).
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

logger = logging.getLogger(__name__)


class AudioStorageError(Exception):
    """Base exception for audio storage operations."""


class AudioStorageBase(ABC):
    """Abstract base class for audio storage providers."""

    @abstractmethod
    async def store_audio(
        self,
        podcast_id: UUID,
        user_id: UUID,
        audio_data: bytes,
        audio_format: str,
    ) -> str:
        """
        Store podcast audio file.

        Args:
            podcast_id: Unique podcast identifier
            user_id: User who owns the podcast
            audio_data: Audio file bytes
            audio_format: Audio format (mp3, wav, etc.)

        Returns:
            URL or path to access the stored audio

        Raises:
            AudioStorageError: If storage operation fails
        """

    @abstractmethod
    async def retrieve_audio(self, podcast_id: UUID, user_id: UUID) -> bytes:
        """
        Retrieve podcast audio file.

        Args:
            podcast_id: Podcast identifier
            user_id: User identifier for access control

        Returns:
            Audio file bytes

        Raises:
            AudioStorageError: If retrieval fails
        """

    @abstractmethod
    async def delete_audio(self, podcast_id: UUID, user_id: UUID) -> bool:
        """
        Delete podcast audio file.

        Args:
            podcast_id: Podcast identifier
            user_id: User identifier for access control

        Returns:
            True if deleted, False if not found

        Raises:
            AudioStorageError: If deletion fails
        """

    @abstractmethod
    async def exists(self, podcast_id: UUID, user_id: UUID) -> bool:
        """
        Check if audio file exists.

        Args:
            podcast_id: Podcast identifier
            user_id: User identifier

        Returns:
            True if file exists, False otherwise
        """


class LocalFileStorage(AudioStorageBase):
    """Local filesystem storage for podcast audio files (development)."""

    def __init__(self, base_path: str = "./data/podcasts"):
        """
        Initialize local file storage.

        Args:
            base_path: Base directory for storing audio files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info("Initialized LocalFileStorage at %s", self.base_path.absolute())

    def _get_audio_path(self, podcast_id: UUID, user_id: UUID, audio_format: str = "mp3") -> Path:
        """
        Get path for audio file.

        Structure: {base_path}/{user_id}/{podcast_id}/audio.{format}

        Args:
            podcast_id: Podcast identifier
            user_id: User identifier
            audio_format: Audio format extension

        Returns:
            Path object for audio file
        """
        user_dir = self.base_path / str(user_id)
        podcast_dir = user_dir / str(podcast_id)
        return podcast_dir / f"audio.{audio_format}"

    async def store_audio(
        self,
        podcast_id: UUID,
        user_id: UUID,
        audio_data: bytes,
        audio_format: str,
    ) -> str:
        """
        Store audio file to local filesystem.

        Args:
            podcast_id: Podcast identifier
            user_id: User identifier
            audio_data: Audio file bytes
            audio_format: Audio format (mp3, wav, etc.)

        Returns:
            Relative file path as URL

        Raises:
            AudioStorageError: If write fails
        """
        try:
            audio_path = self._get_audio_path(podcast_id, user_id, audio_format)

            # Create directory structure
            audio_path.parent.mkdir(parents=True, exist_ok=True)

            # Write audio file
            with open(audio_path, "wb") as f:
                f.write(audio_data)

            logger.info(
                "Stored audio for podcast %s at %s (%d bytes)",
                podcast_id,
                audio_path,
                len(audio_data),
            )

            # Return API endpoint URL for accessing the audio
            return f"/api/podcasts/{podcast_id}/audio"

        except OSError as e:
            error_msg = f"Failed to store audio for podcast {podcast_id}: {e}"
            logger.error(error_msg)
            raise AudioStorageError(error_msg) from e

    async def retrieve_audio(self, podcast_id: UUID, user_id: UUID) -> bytes:
        """
        Retrieve audio file from local filesystem.

        Args:
            podcast_id: Podcast identifier
            user_id: User identifier

        Returns:
            Audio file bytes

        Raises:
            AudioStorageError: If file not found or read fails
        """
        try:
            # Try common formats
            for audio_format in ["mp3", "wav", "opus", "aac", "flac"]:
                audio_path = self._get_audio_path(podcast_id, user_id, audio_format)
                if audio_path.exists():
                    with open(audio_path, "rb") as f:
                        audio_data = f.read()

                    logger.info(
                        "Retrieved audio for podcast %s (%d bytes)",
                        podcast_id,
                        len(audio_data),
                    )
                    return audio_data

            # If no format found
            raise FileNotFoundError(f"Audio file for podcast {podcast_id} not found")

        except FileNotFoundError as e:
            error_msg = f"Audio file for podcast {podcast_id} not found: {e}"
            logger.error(error_msg)
            raise AudioStorageError(error_msg) from e
        except OSError as e:
            error_msg = f"Failed to retrieve audio for podcast {podcast_id}: {e}"
            logger.error(error_msg)
            raise AudioStorageError(error_msg) from e

    async def delete_audio(self, podcast_id: UUID, user_id: UUID) -> bool:
        """
        Delete audio file from local filesystem.

        Args:
            podcast_id: Podcast identifier
            user_id: User identifier

        Returns:
            True if deleted, False if not found

        Raises:
            AudioStorageError: If deletion fails
        """
        try:
            # Try common formats
            deleted = False
            for audio_format in ["mp3", "wav", "opus", "aac", "flac"]:
                audio_path = self._get_audio_path(podcast_id, user_id, audio_format)
                if audio_path.exists():
                    audio_path.unlink()
                    deleted = True
                    logger.info("Deleted audio file: %s", audio_path)

            # Try to remove empty directories
            if deleted:
                podcast_dir = audio_path.parent
                if podcast_dir.exists() and not any(podcast_dir.iterdir()):
                    podcast_dir.rmdir()
                    logger.debug("Removed empty podcast directory: %s", podcast_dir)

                user_dir = podcast_dir.parent
                if user_dir.exists() and not any(user_dir.iterdir()):
                    user_dir.rmdir()
                    logger.debug("Removed empty user directory: %s", user_dir)

            return deleted

        except OSError as e:
            error_msg = f"Failed to delete audio for podcast {podcast_id}: {e}"
            logger.error(error_msg)
            raise AudioStorageError(error_msg) from e

    async def exists(self, podcast_id: UUID, user_id: UUID) -> bool:
        """
        Check if audio file exists.

        Args:
            podcast_id: Podcast identifier
            user_id: User identifier

        Returns:
            True if file exists in any format
        """
        for audio_format in ["mp3", "wav", "opus", "aac", "flac"]:
            audio_path = self._get_audio_path(podcast_id, user_id, audio_format)
            if audio_path.exists():
                return True
        return False
