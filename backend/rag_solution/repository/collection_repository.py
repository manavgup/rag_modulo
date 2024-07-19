from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID
from typing import List, Optional

from ..models.collection import Collection
from ..models.file import File
from ..schemas.collection_schema import CollectionInDB, CollectionInput, CollectionOutput
from ..schemas.file_schema import FileOutput

class CollectionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, collection: CollectionInput) -> CollectionInDB:
        try:
            db_collection = Collection(**collection.model_dump())
            self.session.add(db_collection)
            self.session.commit()
            self.session.refresh(db_collection)
            return CollectionInDB.model_validate(db_collection)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def get(self, collection_id: UUID) -> Optional[CollectionInDB]:
        collection = self.session.query(Collection).filter(Collection.id == collection_id).first()
        return CollectionInDB.model_validate(collection) if collection else None

    def update(self, collection_id: UUID, collection_data: dict) -> Optional[CollectionInDB]:
        try:
            db_collection = self.session.query(Collection).filter(Collection.id == collection_id).first()
            if db_collection:
                for key, value in collection_data.items():
                    setattr(db_collection, key, value)
                self.session.commit()
                self.session.refresh(db_collection)
                return CollectionInDB.model_validate(db_collection)
            return None
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def delete(self, collection_id: UUID) -> bool:
        try:
            db_collection = self.session.query(Collection).filter(Collection.id == collection_id).first()
            if db_collection:
                self.session.delete(db_collection)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def list(self, skip: int = 0, limit: int = 100) -> List[CollectionInDB]:
        collections = self.session.query(Collection).offset(skip).limit(limit).all()
        return [CollectionInDB.model_validate(collection) for collection in collections]

    def get_user_collections(self, user_id: UUID) -> List[CollectionInDB]:
        collections = self.session.query(Collection).filter(Collection.user_id == user_id).all()
        return [CollectionInDB.model_validate(collection) for collection in collections]

    def get_collection_output(self, collection_id: UUID) -> Optional[CollectionOutput]:
        collection = self.get(collection_id)
        if not collection:
            return None

        files = self.session.query(File).filter(File.collection_id == collection_id).all()
        file_outputs = [FileOutput.model_validate(file) for file in files]

        return CollectionOutput(
            name=collection.name,
            is_private=collection.is_private,
            files=file_outputs
        )
