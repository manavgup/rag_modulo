from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID
from typing import List, Optional

from ..models.file import File
from ..schemas.file_schema import FileInDB, FileInput, FileOutput

class FileRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, file: FileInput) -> FileInDB:
        try:
            db_file = File(**file.model_dump())
            self.session.add(db_file)
            self.session.commit()
            self.session.refresh(db_file)
            return FileInDB.model_validate(db_file)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def get(self, file_id: UUID) -> Optional[FileInDB]:
        file = self.session.query(File).filter(File.id == file_id).first()
        return FileInDB.model_validate(file) if file else None

    def update(self, file_id: UUID, file_data: dict) -> Optional[FileInDB]:
        try:
            db_file = self.session.query(File).filter(File.id == file_id).first()
            if db_file:
                for key, value in file_data.items():
                    setattr(db_file, key, value)
                self.session.commit()
                self.session.refresh(db_file)
                return FileInDB.model_validate(db_file)
            return None
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def delete(self, file_id: UUID) -> bool:
        try:
            db_file = self.session.query(File).filter(File.id == file_id).first()
            if db_file:
                self.session.delete(db_file)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def list(self, skip: int = 0, limit: int = 100) -> List[FileInDB]:
        files = self.session.query(File).offset(skip).limit(limit).all()
        return [FileInDB.model_validate(file) for file in files]

    def get_collection_files(self, collection_id: UUID) -> List[FileInDB]:
        files = self.session.query(File).filter(File.collection_id == collection_id).all()
        return [FileInDB.model_validate(file) for file in files]

    def get_file_output(self, file_id: UUID) -> Optional[FileOutput]:
        file = self.get(file_id)
        if not file:
            return None

        return FileOutput(
            filename=file.filename,
            filepath=file.filepath,
            file_type=file.file_type
        )
