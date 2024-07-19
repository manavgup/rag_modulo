# rag_solution/services/file_management_service.py
import logging
from pathlib import Path
from uuid import UUID
from backend.core.config import settings
from backend.rag_solution.repository.file_repository import FileRepository
from backend.rag_solution.schemas.file_schema import FileInput
from fastapi.datastructures import UploadFile
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileManagementService:
    def __init__(self, db_session):
        self.file_repository = FileRepository(db_session)

    async def save_file(self, upload_file: UploadFile, user_id: UUID, collection_id: UUID) -> Path:
        """
        Save an uploaded file to the file system.

        Args:
            upload_file (UploadFile): The uploaded file to be saved.
            user_id (UUID): The ID of the user who uploaded the file.
            collection_id (UUID): The ID of the collection the file belongs to.

        Returns:
            Path: The path of the saved file.

        Raises:
            ValueError: If file_storage_path is not set or upload_file.filename is None.
            IOError: If there's an error writing the file.
        """
        if not settings.file_storage_path:
            logger.error("file_storage_path is not set in the configuration")
            raise ValueError("file_storage_path is not set in the configuration")

        if not upload_file.filename:
            logger.error("upload_file.filename is None")
            raise ValueError("upload_file.filename is None")

        try:
            base_dir = Path(settings.file_storage_path) / str(user_id) / str(collection_id)
            base_dir.mkdir(parents=True, exist_ok=True)
            file_path = base_dir / upload_file.filename

            with open(file_path, "wb") as output_file:
                while chunk := await upload_file.read(1024 * 1024):  # Read 1 MB at a time
                    output_file.write(chunk)

            logger.info(f"File saved successfully: {file_path}")
            return file_path
        except IOError as e:
            logger.error(f"Error saving file: {str(e)}")
            raise

    async def create_file_record(self, collection_id: UUID, filename: str, filepath: str, file_type: str):
        """
        Create a file record in the database.
        """
        file_input = FileInput(
            collection_id=collection_id,
            filename=filename,
            filepath=filepath,
            file_type=file_type
        )
        return await self.file_repository.create(file_input)

    def get_file_path(self, user_id: UUID, collection_id: UUID, filename: str) -> Path:
        """
        Get the file path for a given user, collection, and filename.

        Args:
            user_id (UUID): The ID of the user.
            collection_id (UUID): The ID of the collection.
            filename (str): The name of the file.

        Returns:
            Path: The file path.
        """
        return Path(settings.file_storage_path) / str(user_id) / str(collection_id) / filename

    async def get_files(self, user_id: UUID, collection_id: UUID) -> List[str]:
        """
        Get a list of files for a given user and collection.

        Args:
            user_id (UUID): The ID of the user.
            collection_id (UUID): The ID of the collection.

        Returns:
            List[str]: A list of file names.

        Raises:
            FileNotFoundError: If the directory for the user and collection doesn't exist.
        """
        try:
            base_dir = Path(settings.file_storage_path) / str(user_id) / str(collection_id)
            filesystem_files = [file.name for file in base_dir.iterdir() if file.is_file()]

            # Get file records from the database
            db_files = await self.file_repository.get_collection_files(collection_id)

            # Combine and deduplicate
            all_files = list(set(filesystem_files + [file.filename for file in db_files]))

            return all_files
        except FileNotFoundError:
            logger.warning(f"Directory not found for user {user_id} and collection {collection_id}")
            return []

def get_file_management_service() -> FileManagementService:
    return FileManagementService()
