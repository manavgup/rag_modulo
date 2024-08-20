import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from backend.rag_solution.models.collection import Collection
from backend.rag_solution.models.user import User
from backend.rag_solution.models.user_collection import UserCollection
from backend.rag_solution.schemas.collection_schema import (CollectionInput,
                                                            CollectionOutput,
                                                            FileInfo)

logger = logging.getLogger(__name__)

class CollectionRepository:
    """Repository for managing Collection entities in the database."""

    def __init__(self, db: Session):
        """
        Initialize the CollectionRepository.

        Args:
            db (Session): The database session.
        """
        self.db = db

    def create(self, collection: CollectionInput, vector_db_name: str) -> CollectionOutput:
        """
        Create a new collection in the database.

        Args:
            collection (CollectionInput): The collection data to create.

        Returns:
            CollectionInDB: The created collection.

        Raises:
            SQLAlchemyError: If there's an error during database operations.
        """
        db_collection = Collection(
            name=collection.name,
            vector_db_name=vector_db_name,
            is_private=collection.is_private
        )
        self.db.add(db_collection)
        self.db.commit()
        self.db.refresh(db_collection)
        return self._collection_to_output(db_collection)

    def get(self, collection_id: UUID) -> Optional[CollectionOutput]:
        """
        Retrieve a collection by its ID.

        Args:
            collection_id (UUID): The ID of the collection to retrieve.

        Returns:
            Optional[CollectionInDB]: The collection if found, None otherwise.

        Raises:
            SQLAlchemyError: If there's an error during database operations.
        """
        try:
            collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
            return self._collection_to_output(collection) if collection else None
        except SQLAlchemyError as e:
            logger.error(f"Error getting collection {collection_id}: {str(e)}")
            raise

    def get_user_collections(self, user_id: UUID) -> List[CollectionOutput]:
        try:
            collections = self.db.query(Collection).join(UserCollection).filter(UserCollection.user_id == user_id).all()
            return [self._collection_to_output(collection) for collection in collections]
        except SQLAlchemyError as e:
            logger.error(f"Error getting collections for user {user_id}: {str(e)}")
            raise

    def update(self, collection_id: UUID, collection_update: CollectionInput) -> Optional[CollectionInput]:
        """
        Update an existing collection.

        Args:
            collection_id (UUID): The ID of the collection to update.
            collection_update (CollectionInput): The updated collection data.

        Returns:
            Optional[CollectionInDB]: The updated collection if found, None otherwise.

        Raises:
            SQLAlchemyError: If there's an error during database operations.
        """
        try:
            collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
            if collection:
                for key, value in collection_update.items():
                    setattr(collection, key, value)
                self.db.commit()
                self.db.refresh(collection)
                return self._collection_to_output(collection)
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error updating collection {collection_id}: {str(e)}")
            self.db.rollback()
            raise

    def delete(self, collection_id: UUID) -> bool:
        """
        Delete a collection by its ID.

        Args:
            collection_id (UUID): The ID of the collection to delete.

        Returns:
            bool: True if the collection was deleted, False if not found.

        Raises:
            SQLAlchemyError: If there's an error during database operations.
        """
        try:
            collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
            if collection:
                self.db.delete(collection)
                self.db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting collection {collection_id}: {str(e)}")
            self.db.rollback()
            raise

    def list(self, skip: int = 0, limit: int = 100) -> List[CollectionOutput]:
        try:
            collections = self.db.query(Collection).offset(skip).limit(limit).all()
            return [self._collection_to_output(collection) for collection in collections]
        except SQLAlchemyError as e:
            logger.error(f"Error listing collections: {str(e)}")
            raise

    @staticmethod
    def _collection_to_output(collection: Collection) -> CollectionOutput:
        return CollectionOutput(
            id=collection.id,
            name=collection.name,
            vector_db_name=collection.vector_db_name,
            is_private=collection.is_private,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            user_ids=[user.user_id for user in collection.users],
            files=[FileInfo(id=file.id, filename=file.filename) for file in collection.files],
            status=collection.status
        )
