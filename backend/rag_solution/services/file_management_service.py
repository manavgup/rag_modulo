# file_management_service.py

import logging
from mimetypes import guess_type
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.core.exceptions import NotFoundError, ValidationError
from rag_solution.repository.file_repository import FileRepository
from rag_solution.schemas.file_schema import FileInput, FileMetadata, FileOutput

logger = logging.getLogger(__name__)


class FileManagementService:
    def __init__(self: Any, db: Session, settings: Settings) -> None:
        self.file_repository = FileRepository(db)
        self.settings = settings

    def create_file(self, file_input: FileInput, user_id: UUID4) -> FileOutput:
        logger.info(f"Creating file record: {file_input.filename}")
        file = self.file_repository.create(file_input, user_id)
        logger.info(f"File record created successfully: {file.file_path}")
        return file

    def get_file_by_id(self, file_id: UUID4) -> FileOutput:
        logger.info(f"Fetching file with id: {file_id}")
        return self.file_repository.get(file_id)

    def save_file(self, file: UploadFile, collection_id: UUID4, user_id: UUID4) -> str:
        file_content = file.file.read()
        file_path = self.upload_file(user_id, collection_id, file_content, file.filename or "unknown")

        filename = file.filename or "unknown"
        file_input = FileInput(
            collection_id=collection_id,
            filename=filename,
            file_path=str(file_path),
            file_type=self.determine_file_type(filename),
            metadata=None,  # We'll update this later when processing is complete
        )
        self.create_file(file_input, user_id)

        return str(file_path)

    def get_file_by_name(self, collection_id: UUID4, filename: str) -> FileOutput:
        try:
            logger.info(f"Fetching file {filename} from collection {collection_id}")
            file = self.file_repository.get_file_by_name(collection_id, filename)
            return file
        except NotFoundError:
            logger.warning(f"File not found: {filename} in collection {collection_id}")
            raise  # Propagate the NotFoundError
        except Exception as e:
            logger.error(f"Unexpected error getting file by name {filename} in collection {collection_id}: {e!s}")
            raise

    def update_file(self, file_id: UUID4, file_update: FileInput) -> FileOutput:
        logger.info(f"Updating file {file_id}")
        updated_file = self.file_repository.update(file_id, file_update)  # Will raise NotFoundError if not found
        logger.info(f"File {file_id} updated successfully")
        return updated_file

    def delete_file(self, file_id: UUID4) -> None:
        logger.info(f"Deleting file: {file_id}")
        file = self.file_repository.get(file_id)  # Will raise NotFoundError if not found

        self.file_repository.delete(file_id)
        if file.file_path:
            file_path = Path(file.file_path)
            if file_path.exists():
                file_path.unlink()

        logger.info(f"File {file_id} deleted successfully")

    def delete_files(self, collection_id: UUID4, filenames: list[str]) -> bool:
        try:
            logger.info(f"Deleting files {filenames} from collection {collection_id}")
            for filename in filenames:
                file = self.file_repository.get_file_by_name(collection_id, filename)
                if file:
                    self.delete_file(file.id)
            return True
        except Exception as e:
            logger.error(f"Unexpected error deleting files: {e!s}")
            raise

    def delete_file_by_id(self, collection_id: UUID4, file_id: UUID4) -> None:
        """
        Delete a file by its ID, verifying it belongs to the specified collection.

        Args:
            collection_id (UUID): The ID of the collection.
            file_id (UUID): The ID of the file to delete.

        Raises:
            NotFoundError: If the file is not found.
            ValidationError: If the file does not belong to the collection.
        """
        logger.info(f"Deleting file {file_id} from collection {collection_id}")
        # Get the file and verify it exists
        file = self.file_repository.get(file_id)  # Will raise NotFoundError if not found

        # Verify the file belongs to the specified collection
        if file.collection_id != collection_id:
            logger.warning(f"File {file_id} does not belong to collection {collection_id}")
            raise NotFoundError(
                resource_type="File",
                resource_id=str(file_id),
                message=f"File {file_id} not found in collection {collection_id}",
            )

        # Delete the file
        self.delete_file(file_id)
        logger.info(f"File {file_id} deleted successfully from collection {collection_id}")

    def get_files_by_collection(self, collection_id: UUID4) -> list[FileOutput]:
        try:
            logger.info(f"Fetching files for collection: {collection_id}")
            files = self.file_repository.get_files(collection_id)
            logger.info(f"Retrieved {len(files)} files for collection {collection_id}")
            return files
        except Exception as e:
            logger.error(f"Unexpected error getting files for collection {collection_id}: {e!s}")
            raise

    def get_files(self, collection_id: UUID4) -> list[str]:
        """
        Get a list of files in a specific collection.

        Args:
            collection_id (UUID): The ID of the collection.

        Returns:
            List[str]: A list of filenames in the collection.

        Raises:
            NotFoundError: If the collection or files are not found.
            Domain exceptions: NotFoundError if files are not found.
        """
        try:
            files = self.get_files_by_collection(collection_id)
            if not files:
                raise NotFoundError(
                    resource_type="File",
                    resource_id=str(collection_id),
                )
            return [file.filename for file in files if file.filename is not None]
        except NotFoundError as e:
            logger.error(f"Not found error getting files for collection {collection_id}: {e!s}")
            raise  # Propagate the NotFoundError
        except Exception as e:
            logger.error(f"Unexpected error getting files for collection {collection_id}: {e!s}")
            raise

    def upload_and_create_file_record(
        self,
        file: UploadFile,
        user_id: UUID4,
        collection_id: UUID4,
        document_id: str,
        metadata: FileMetadata | None = None,
    ) -> FileOutput:
        try:
            logger.info(
                f"Uploading file {file.filename} for user {user_id} in collection {collection_id} with document_id {document_id}"
            )
            if file.filename is None:
                raise ValidationError("File name cannot be empty", field="filename")

            file_content = file.file.read()
            file_path = self.upload_file(user_id, collection_id, file_content, file.filename)
            logger.info(f"{file.filename} path: {file_path}")
            file_type = self.determine_file_type(file.filename)
            file_input = FileInput(
                collection_id=collection_id,
                filename=file.filename,
                file_path=str(file_path),
                file_type=file_type,
                metadata=metadata or FileMetadata(),
                document_id=document_id,
            )
            return self.create_file(file_input, user_id)
        except Exception as e:
            logger.error(f"Unexpected error uploading and creating file record: {e!s}")
            raise

    def upload_file(self, user_id: UUID4, collection_id: UUID4, file_content: bytes, filename: str) -> Path:
        try:
            if self.settings is None:
                raise ValueError("Settings must be provided to FileManagementService")
            user_folder = Path(f"{self.settings.file_storage_path}/{user_id}")
            collection_folder = user_folder / str(collection_id)
            collection_folder.mkdir(parents=True, exist_ok=True)

            file_path = collection_folder / filename
            with file_path.open("wb") as f:
                f.write(file_content)
            logger.info(f"File {filename} uploaded successfully to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e!s}")
            raise

    def update_file_metadata(self, collection_id: UUID4, file_id: UUID4, metadata: FileMetadata) -> FileOutput:
        logger.info(f"Updating metadata for file {file_id}")
        file = self.file_repository.get(file_id)  # Will raise NotFoundError if not found

        if file.collection_id != collection_id:
            logger.warning(f"File {file_id} does not belong to collection {collection_id}")
            raise ValidationError(
                f"File does not belong to collection {collection_id}",
                field="collection_id",
            )

        file_update = FileInput(
            collection_id=file.collection_id,
            filename=file.filename or "unknown",
            file_path=file.file_path or "",
            file_type=file.file_type or "unknown",
            metadata=metadata,
        )
        updated_file = self.file_repository.update(file_id, file_update)
        logger.info(f"Metadata for file {file_id} updated successfully")
        return updated_file

    @staticmethod
    def determine_file_type(filename: str) -> str:
        file_type, _ = guess_type(filename)
        return file_type or "application/octet-stream"

    def get_file_path(self, collection_id: UUID4, filename: str) -> Path:
        try:
            logger.info(f"Getting file path for {filename} in collection {collection_id}")

            # Sanitize filename to prevent path traversal
            clean_filename = Path(filename).name
            if clean_filename != filename:
                raise ValidationError("Invalid filename provided", field="filename")

            file = self.get_file_by_name(collection_id, clean_filename)
            logger.info(f"found {file.file_path} for {file}")
            if file.file_path is None:
                raise ValueError(f"File {clean_filename} has no file path")

            # Final security check: ensure the path is within the designated storage area
            file_path = Path(file.file_path).resolve()
            storage_root = Path(self.settings.file_storage_path).resolve()

            if storage_root not in file_path.parents:
                logger.error(
                    f"Security alert: Attempt to access file outside storage root. Path: {file_path}, Root: {storage_root}"
                )
                raise NotFoundError(resource_type="File", resource_id=filename)

            return file_path
        except Exception as e:
            logger.error(f"Unexpected error getting file path: {e!s}")
            raise

    # Voice-specific file management methods

    def save_voice_file(self, user_id: UUID4, voice_id: UUID4, file_content: bytes, audio_format: str) -> Path:
        """
        Save voice sample file for a user's custom voice.

        Structure: {storage_path}/{user_id}/voices/{voice_id}/sample.{format}

        Args:
            user_id: User ID who owns the voice
            voice_id: Voice ID
            file_content: Audio file bytes
            audio_format: Audio format (mp3, wav, m4a, flac, ogg)

        Returns:
            Path to the saved voice sample file

        Raises:
            ValueError: If settings not configured or invalid format
            OSError: If file write fails
        """
        try:
            if self.settings is None:
                raise ValueError("Settings must be provided to FileManagementService")

            # Supported formats for voice samples
            supported_formats = ["mp3", "wav", "m4a", "flac", "ogg"]
            if audio_format.lower() not in supported_formats:
                raise ValueError(
                    f"Unsupported audio format '{audio_format}'. Supported: {', '.join(supported_formats)}"
                )

            # Create voice-specific folder structure
            user_folder = Path(f"{self.settings.file_storage_path}/{user_id}")
            voices_folder = user_folder / "voices"
            voice_folder = voices_folder / str(voice_id)
            voice_folder.mkdir(parents=True, exist_ok=True)

            # Save file as sample.{format}
            file_path = voice_folder / f"sample.{audio_format}"
            with file_path.open("wb") as f:
                f.write(file_content)

            logger.info(f"Voice sample saved for voice {voice_id} at {file_path} ({len(file_content)} bytes)")
            return file_path

        except Exception as e:
            logger.error(f"Error saving voice file for voice {voice_id}: {e!s}")
            raise

    def get_voice_file_path(self, user_id: UUID4, voice_id: UUID4) -> Path | None:
        """
        Get path to voice sample file.

        Searches for voice sample in supported formats.

        Args:
            user_id: User ID
            voice_id: Voice ID

        Returns:
            Path to voice sample file, or None if not found
        """
        try:
            if self.settings is None:
                raise ValueError("Settings must be provided to FileManagementService")

            user_folder = Path(f"{self.settings.file_storage_path}/{user_id}")
            voice_folder = user_folder / "voices" / str(voice_id)

            # Try supported formats
            for audio_format in ["mp3", "wav", "m4a", "flac", "ogg"]:
                file_path = voice_folder / f"sample.{audio_format}"
                if file_path.exists():
                    logger.debug(f"Found voice sample at {file_path}")
                    return file_path

            logger.warning(f"Voice sample not found for voice {voice_id}")
            return None

        except Exception as e:
            logger.error(f"Error getting voice file path for voice {voice_id}: {e!s}")
            raise

    def delete_voice_file(self, user_id: UUID4, voice_id: UUID4) -> bool:
        """
        Delete voice sample file.

        Args:
            user_id: User ID
            voice_id: Voice ID

        Returns:
            True if file was deleted, False if not found

        Raises:
            OSError: If deletion fails
        """
        try:
            if self.settings is None:
                raise ValueError("Settings must be provided to FileManagementService")

            user_folder = Path(f"{self.settings.file_storage_path}/{user_id}")
            voice_folder = user_folder / "voices" / str(voice_id)

            if not voice_folder.exists():
                logger.debug(f"Voice folder not found for voice {voice_id}")
                return False

            deleted = False

            # Delete all voice sample files (any format)
            for audio_format in ["mp3", "wav", "m4a", "flac", "ogg"]:
                file_path = voice_folder / f"sample.{audio_format}"
                if file_path.exists():
                    file_path.unlink()
                    deleted = True
                    logger.info(f"Deleted voice sample file: {file_path}")

            # Remove empty directories
            if deleted and voice_folder.exists():
                if not any(voice_folder.iterdir()):
                    voice_folder.rmdir()
                    logger.debug(f"Removed empty voice folder: {voice_folder}")

                voices_folder = voice_folder.parent
                if voices_folder.exists() and not any(voices_folder.iterdir()):
                    voices_folder.rmdir()
                    logger.debug(f"Removed empty voices folder: {voices_folder}")

            return deleted

        except Exception as e:
            logger.error(f"Error deleting voice file for voice {voice_id}: {e!s}")
            raise

    def voice_file_exists(self, user_id: UUID4, voice_id: UUID4) -> bool:
        """
        Check if voice sample file exists.

        Args:
            user_id: User ID
            voice_id: Voice ID

        Returns:
            True if voice sample file exists in any format
        """
        try:
            return self.get_voice_file_path(user_id, voice_id) is not None
        except Exception as e:
            logger.error(f"Error checking voice file existence for voice {voice_id}: {e!s}")
            return False
