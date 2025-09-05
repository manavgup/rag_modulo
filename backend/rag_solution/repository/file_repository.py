# file_repository.py

import logging
from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError, ValidationError
from rag_solution.models.file import File
from rag_solution.schemas.file_schema import FileInput, FileMetadata, FileOutput

logger = logging.getLogger(__name__)


class FileRepository:
    def __init__(self: Any, db: Session) -> None:
        self.db = db

    def create(self, file: FileInput, user_id: UUID4) -> FileOutput:
        try:
            db_file = File(
                user_id=user_id,
                collection_id=file.collection_id,
                filename=file.filename,
                file_type=file.file_type,
                file_path=file.file_path,
                metadata=file.metadata.model_dump() if file.metadata else {},
                document_id=file.document_id,
            )
            self.db.add(db_file)
            self.db.commit()
            self.db.refresh(db_file)
            return self._file_to_output(db_file)
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error creating file record: {e!s}")
            self.db.rollback()
            raise

    def get(self, file_id: UUID4) -> FileOutput:
        try:
            file = self.db.query(File).filter(File.id == file_id).first()
            if not file:
                raise NotFoundError(resource_type="File", resource_id=str(file_id))
            return self._file_to_output(file)
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting file record {file_id}: {e!s}")
            raise

    def get_file(self, collection_id: UUID4, filename: str) -> FileOutput:
        try:
            file = self.db.query(File).filter(File.collection_id == collection_id, File.filename == filename).first()
            if not file:
                raise NotFoundError(resource_type="File", identifier=f"{filename} in collection {collection_id}")
            return self._file_to_output(file)
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting file {filename} from collection {collection_id}: {e!s}")
            raise

    def get_files(self, collection_id: UUID4) -> list[FileOutput]:
        try:
            files = self.db.query(File).filter(File.collection_id == collection_id).all()
            return [self._file_to_output(file) for file in files]
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting files for collection {collection_id}: {e!s}")
            raise

    def update(self, file_id: UUID4, file_update: FileInput) -> FileOutput:
        try:
            file = self.db.query(File).filter(File.id == file_id).first()
            if not file:
                raise NotFoundError(resource_type="File", resource_id=str(file_id))
            update_data = file_update.model_dump(exclude_unset=True)
            if "metadata" in update_data and update_data["metadata"] is not None:
                file.file_metadata = update_data["metadata"].model_dump()
                del update_data["metadata"]
            for key, value in update_data.items():
                setattr(file, key, value)
            self.db.commit()
            self.db.refresh(file)
            return self._file_to_output(file)
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error updating file record {file_id}: {e!s}")
            self.db.rollback()
            raise

    def delete(self, file_id: UUID4) -> None:
        try:
            file = self.db.query(File).filter(File.id == file_id).first()
            if not file:
                raise NotFoundError(resource_type="File", resource_id=str(file_id))
            self.db.delete(file)
            self.db.commit()
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error deleting file record {file_id}: {e!s}")
            self.db.rollback()
            raise

    def get_collection_files(self, collection_id: UUID4) -> list[FileOutput]:
        try:
            files = self.db.query(File).filter(File.collection_id == collection_id).all()
            return [self._file_to_output(file) for file in files]
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting files for collection {collection_id}: {e!s}")
            raise

    def get_user_files(self, user_id: UUID4) -> list[FileOutput]:
        try:
            files = self.db.query(File).filter(File.user_id == user_id).all()
            return [self._file_to_output(file) for file in files]
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting files for user {user_id}: {e!s}")
            raise

    def get_file_by_name(self, collection_id: UUID4, filename: str) -> FileOutput:
        try:
            file = self.db.query(File).filter(File.collection_id == collection_id, File.filename == filename).first()
            if not file:
                raise NotFoundError(resource_type="File", identifier=f"{filename} in collection {collection_id}")
            return self._file_to_output(file)
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting file record for {filename} in collection {collection_id}: {e!s}")
            raise

    def file_exists(self, collection_id: UUID4, filename: str) -> bool:
        try:
            return self.db.query(File).filter(File.collection_id == collection_id, File.filename == filename).first() is not None
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error checking existence of file {filename} in collection {collection_id}: {e!s}")
            raise

    @staticmethod
    def _file_to_output(file: File) -> FileOutput:
        return FileOutput(
            id=file.id,
            collection_id=file.collection_id,
            filename=file.filename,
            file_type=file.file_type,
            file_path=file.file_path,
            metadata=FileMetadata(**file.file_metadata) if file.file_metadata else None,  # type: ignore[arg-type]
            document_id=file.document_id,
        )
