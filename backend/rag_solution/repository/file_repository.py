from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from rag_solution.models.file import File
from rag_solution.schemas.file_schema import FileInput, FileOutput
import logging

logger = logging.getLogger(__name__)

class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, file: FileInput, user_id: UUID) -> FileOutput:
        try:
            db_file = File(
                user_id=user_id,
                collection_id=file.collection_id,
                filename=file.filename,
                file_type=file.file_type,
                file_path=file.file_path,
            )
            self.db.add(db_file)
            self.db.commit()
            self.db.refresh(db_file)
            return self._file_to_output(db_file)
        except Exception as e:
            logger.error(f"Error creating file record: {str(e)}")
            self.db.rollback()
            raise

    def get(self, file_id: UUID) -> Optional[FileOutput]:
        try:
            file = self.db.query(File).filter(File.id == file_id).first()
            return self._file_to_output(file) if file else None
        except Exception as e:
            logger.error(f"Error getting file record {file_id}: {str(e)}")
            raise

    def get_file(self, collection_id: UUID, filename: str) -> Optional[FileOutput]:
        try:
            file = self.db.query(File).filter(File.collection_id == collection_id, File.filename == filename).first()
            return self._file_to_output(file) if file else None
        except Exception as e:
            logger.error(f"Error getting file {filename} from collection {collection_id}: {str(e)}")
            raise

    def get_files(self, collection_id: UUID) -> List[FileOutput]:
        try:
            files = self.db.query(File).filter(File.collection_id == collection_id).all()
            return [self._file_to_output(file) for file in files]
        except Exception as e:
            logger.error(f"Error getting files for collection {collection_id}: {str(e)}")
            raise

    def update(self, file_id: UUID, file_update: FileInput) -> Optional[FileInput]:
        try:
            file = self.db.query(File).filter(File.id == file_id).first()
            if file:
                for key, value in file_update.model_dump().items():
                    setattr(file, key, value)
                self.db.commit()
                self.db.refresh(file)
                return file_update
            return None
        except Exception as e:
            logger.error(f"Error updating file record {file_id}: {str(e)}")
            self.db.rollback()
            raise

    def delete(self, file_id: UUID) -> bool:
        try:
            file = self.db.query(File).filter(File.id == file_id).first()
            if file:
                self.db.delete(file)
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file record {file_id}: {str(e)}")
            self.db.rollback()
            raise

    def get_collection_files(self, collection_id: UUID) -> List[FileOutput]:
        try:
            files = self.db.query(File).filter(File.collection_id == collection_id).all()
            return [self._file_to_output(file) for file in files]
        except Exception as e:
            logger.error(f"Error getting files for collection {collection_id}: {str(e)}")
            raise

    def get_user_files(self, user_id: UUID) -> List[FileOutput]:
        try:
            files = self.db.query(File).join(File.collection).filter(File.collection.has(user_id=user_id)).all()
            return [self._file_to_output(file) for file in files]
        except Exception as e:
            logger.error(f"Error getting files for user {user_id}: {str(e)}")
            raise

    def get_file_by_name(self, collection_id: UUID, filename: str) -> Optional[FileOutput]:
        try:
            file = self.db.query(File).filter(File.collection_id == collection_id, File.filename == filename).first()
            return self._file_to_output(file) if file else None
        except Exception as e:
            logger.error(f"Error getting file record for {filename} in collection {collection_id}: {str(e)}")
            raise

    def file_exists(self, collection_id: UUID, filename: str) -> bool:
        try:
            return self.db.query(File).filter(File.collection_id == collection_id, File.filename == filename).first() is not None
        except Exception as e:
            logger.error(f"Error checking existence of file {filename} in collection {collection_id}: {str(e)}")
            raise

    @staticmethod
    def _file_to_output(file: File) -> FileOutput:
        return FileOutput(
            id=file.id,
            filename=file.filename,
            file_type=file.file_type,
            file_path=file.file_path
        )
