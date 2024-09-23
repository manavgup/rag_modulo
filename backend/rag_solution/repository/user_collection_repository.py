import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from rag_solution.models.user_collection import UserCollection
from rag_solution.schemas.user_collection_schema import \
    UserCollectionOutput

logger = logging.getLogger(__name__)

class UserCollectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_user_to_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        try:
            user_collection = UserCollection(user_id=user_id, collection_id=collection_id)
            self.db.add(user_collection)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding user to collection: {str(e)}")
            raise

    def remove_user_from_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        try:
            result = self.db.query(UserCollection).filter(
                UserCollection.user_id == user_id,
                UserCollection.collection_id == collection_id
            ).delete()
            self.db.commit()
            return result > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing user from collection: {str(e)}")
            raise

    def get_user_collections(self, user_id: UUID) -> List[UserCollectionOutput]:
        try:
            user_collections = self.db.query(UserCollection).filter(UserCollection.user_id == user_id).all()
            return [self._user_collection_to_output(user_collection) for user_collection in user_collections]
        except Exception as e:
            logger.error(f"Error listing collections for user {user_id}: {str(e)}")
            raise

    def get_collection_users(self, collection_id: UUID) -> List[UserCollectionOutput]:
        try:
            user_collections = self.db.query(UserCollection).filter(UserCollection.collection_id == collection_id).all()
            return [self._user_collection_to_output(user_collection) for user_collection in user_collections]
        except Exception as e:
            logger.error(f"Error listing users for collection {collection_id}: {str(e)}")
            raise

    def remove_all_users_from_collection(self, collection_id: UUID) -> bool:
        try:
            result = self.db.query(UserCollection).filter(UserCollection.collection_id == collection_id).delete()
            self.db.commit()
            return result > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing all users from collection {collection_id}: {str(e)}")
            raise

    def get_user_collection(self, user_id: UUID, collection_id: UUID) -> Optional[UserCollectionOutput]:
        try:
            user_collection = self.db.query(UserCollection).filter(
                UserCollection.user_id == user_id,
                UserCollection.collection_id == collection_id
            ).first()
            return self._user_collection_to_output(user_collection) if user_collection else None
        except Exception as e:
            logger.error(f"Error getting user-collection association: {str(e)}")
            raise

    @staticmethod
    def _user_collection_to_output(user_collection: UserCollection) -> UserCollectionOutput:
        return UserCollectionOutput(
            user_id=user_collection.user_id,
            collection_id=user_collection.collection_id,
            joined_at=user_collection.joined_at
        )
