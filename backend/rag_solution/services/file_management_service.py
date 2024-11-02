# file_management_service.py

import logging
from mimetypes import guess_type
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.config import settings
from rag_solution.repository.file_repository import FileRepository
from rag_solution.schemas.file_schema import FileInput, FileOutput, FileMetadata

logger = logging.getLogger(__name__)

class FileManagementService:
    def __init__(self, db: Session):
        self.file_repository = FileRepository(db)

    def create_file(self, file_input: FileInput, user_id: UUID) -> FileOutput:
        try:
            logger.info(f"Creating file record: {file_input.filename}")
            file = self.file_repository.create(file_input, user_id)
            logger.info(f"File record created successfully: {file.file_path}")
            return file
        except ValueError as e:
            logger.error(f"Value error creating file: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error creating file: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_file_by_id(self, file_id: UUID) -> FileOutput:
        try:
            logger.info(f"Fetching file with id: {file_id}")
            file = self.file_repository.get(file_id)
            if file is None:
                logger.warning(f"File not found: {file_id}")
                raise HTTPException(status_code=404, detail="File not found")
            return file
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting file {file_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def save_file(self, file: UploadFile, collection_id: UUID, user_id: UUID) -> str:
        file_path = self.upload_file(file, collection_id)
        
        file_input = FileInput(
            collection_id=collection_id,
            filename=file.filename,
            file_path=str(file_path),
            file_type=self.determine_file_type(file.filename),
            metadata=None  # We'll update this later when processing is complete
        )
        self.create_file(file_input, user_id)
        
        return file_path

    def get_file_by_name(self, collection_id: UUID, filename: str) -> FileOutput:
        try:
            logger.info(f"Fetching file {filename} from collection {collection_id}")
            file = self.file_repository.get_file_by_name(collection_id, filename)
            if file is None:
                logger.warning(f"File not found: {filename} in collection {collection_id}")
                raise HTTPException(status_code=404, detail="File not found")
            return file
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting file by name {filename} in collection {collection_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def update_file(self, file_id: UUID, file_update: FileInput) -> FileOutput:
        try:
            logger.info(f"Updating file {file_id}")
            updated_file = self.file_repository.update(file_id, file_update)
            if updated_file is None:
                logger.warning(f"File not found for update: {file_id}")
                raise HTTPException(status_code=404, detail="File not found")
            logger.info(f"File {file_id} updated successfully")
            return updated_file
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating file {file_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def delete_file(self, file_id: UUID) -> bool:
        try:
            logger.info(f"Deleting file: {file_id}")
            file = self.file_repository.get(file_id)
            if not file:
                logger.warning(f"File not found for deletion: {file_id}")
                raise HTTPException(status_code=404, detail="File not found")
            
            self.file_repository.delete(file_id)
            file_path = Path(file.file_path)
            if file_path.exists():
                file_path.unlink()
            
            logger.info(f"File {file_id} deleted successfully")
            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting file {file_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def delete_files(self, collection_id: UUID, filenames: List[str]) -> bool:
        try:
            logger.info(f"Deleting files {filenames} from collection {collection_id}")
            for filename in filenames:
                file = self.file_repository.get_file_by_name(collection_id, filename)
                if file:
                    self.delete_file(file.id)
            return True
        except Exception as e:
            logger.error(f"Unexpected error deleting files: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_files_by_collection(self, collection_id: UUID) -> List[FileOutput]:
        try:
            logger.info(f"Fetching files for collection: {collection_id}")
            files = self.file_repository.get_files(collection_id)
            logger.info(f"Retrieved {len(files)} files for collection {collection_id}")
            return files
        except Exception as e:
            logger.error(f"Unexpected error getting files for collection {collection_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_files(self, collection_id: UUID) -> List[str]:
        try:
            files = self.get_files_by_collection(collection_id)
            return [file.filename for file in files]
        except Exception as e:
            logger.error(f"Unexpected error getting files for collection {collection_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def upload_and_create_file_record(self, file: UploadFile, user_id: UUID, collection_id: UUID,  metadata: Optional[FileMetadata] = None) -> FileOutput:
        try:
            logger.info(f"Uploading file {file.filename} for user {user_id} in collection {collection_id}")
            if file.filename is None:
                raise HTTPException(status_code=400, detail="File name cannot be empty")

            file_content = file.file.read()
            file_path = self.upload_file(user_id, collection_id, file_content, file.filename)
            logger.info(f"{file.filename} path: {file_path}")
            file_type = self.determine_file_type(file.filename)
            file_input = FileInput(
                collection_id=collection_id,
                filename=file.filename,
                file_path=str(file_path),
                file_type=file_type,
                metadata=FileMetadata(**(metadata or {})) # Use empty dict if metadata is None
            )
            return self.create_file(file_input, user_id)
        except Exception as e:
            logger.error(f"Unexpected error uploading and creating file record: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def upload_file(self, user_id: UUID, collection_id: UUID, file_content: bytes, filename: str) -> Path:
        try:
            user_folder = Path(f"{settings.file_storage_path}/{user_id}")
            collection_folder = user_folder / str(collection_id)
            collection_folder.mkdir(parents=True, exist_ok=True)

            file_path = collection_folder / filename
            with file_path.open("wb") as f:
                f.write(file_content)
            logger.info(f"File {filename} uploaded successfully to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def update_file_metadata(self, collection_id: UUID, file_id: UUID, metadata: FileMetadata) -> FileOutput:
        try:
            logger.info(f"Updating metadata for file {file_id}")
            file = self.file_repository.get(file_id)
            if file is None:
                logger.warning(f"File not found for metadata update: {file_id}")
                raise HTTPException(status_code=404, detail="File not found")
            
            file_update = FileInput(
                collection_id=file.collection_id,
                filename=file.filename,
                file_path=file.file_path,
                file_type=file.file_type,
                metadata=metadata
            )
            updated_file = self.file_repository.update(file_id, file_update)
            logger.info(f"Metadata for file {file_id} updated successfully")
            return updated_file
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating metadata for file {file_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @staticmethod
    def determine_file_type(filename: str) -> str:
        file_type, _ = guess_type(filename)
        return file_type or "application/octet-stream"

    def get_file_path(self, collection_id: UUID, filename: str) -> Path:
        try:
            logger.info(f"Getting file path for {filename} in collection {collection_id}")
            file = self.get_file_by_name(collection_id, filename)
            logger.info(f"found {file.file_path} for {file}")
            return Path(file.file_path)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting file path: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")