from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from rag_solution.models.user_collection import UserCollection
from rag_solution.schemas.user_collection_schema import UserCollectionInput, UserCollectionOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.schemas.collection_schema import CollectionOutput
import logging

logger = logging.getLogger(__name__)

class UserCollectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_collection: UserCollectionInput) -> UserCollectionOutput:
        try:
            db_user_collection = UserCollection(user_id=user_collection.user_id, collection_id=user_collection.collection_id)
            self.db.add(db_user_collection)
            self.db.commit()
            self.db.refresh(db_user_collection)
            return self._user_collection_to_output(db_user_collection)
        except Exception as e:
            logger.error(f"Error creating user-collection association: {str(e)}")
            self.db.rollback()
            raise

    def get(self, user_id: UUID, collection_id: UUID) -> Optional[UserCollectionOutput]:
        try:
            user_collection = self.db.query(UserCollection).filter(UserCollection.user_id == user_id,
                                                                   UserCollection.collection_id == collection_id).first()
            return self._user_collection_to_output(user_collection) if user_collection else None
        except Exception as e:
            logger.error(f"Error getting user-collection association: {str(e)}")
            raise

    def delete(self, user_id: UUID, collection_id: UUID) -> bool:
        try:
            user_collection = self.db.query(UserCollection).filter(UserCollection.user_id == user_id,
                                                                   UserCollection.collection_id == collection_id).first()
            if user_collection:
                self.db.delete(user_collection)
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting user-collection association: {str(e)}")
            self.db.rollback()
            raise

    def list_by_user(self, user_id: UUID) -> List[UserCollectionOutput]:
        try:
            user_collections = self.db.query(UserCollection).filter(UserCollection.user_id == user_id).all()
            return [self._user_collection_to_output(user_collection) for user_collection in user_collections]
        except Exception as e:
            logger.error(f"Error listing collections for user {user_id}: {str(e)}")
            raise

    def list_by_collection(self, collection_id: UUID) -> List[UserCollectionOutput]:
        try:
            user_collections = self.db.query(UserCollection).filter(UserCollection.collection_id == collection_id).all()
            return [self._user_collection_to_output(user_collection) for user_collection in user_collections]
        except Exception as e:
            logger.error(f"Error listing users for collection {collection_id}: {str(e)}")
            raise

    @staticmethod
    def _user_collection_to_output(user_collection: UserCollection) -> UserCollectionOutput:
        return UserCollectionOutput(
            user=UserOutput.model_validate(user_collection.user),
            collection=CollectionOutput.model_validate(user_collection.collection)
        )
