import logging
from typing import List
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from rag_solution.repository.user_collection_repository import UserCollectionRepository
from rag_solution.schemas.user_collection_schema import UserCollectionOutput, UserCollectionDetailOutput, UserCollectionsOutput
from rag_solution.schemas.collection_schema import CollectionOutput

logger = logging.getLogger(__name__)

class UserCollectionService:
    def __init__(self, db: Session):
        self.db = db
        self.user_collection_repository = UserCollectionRepository(db)

    def get_user_collections(self, user_id: UUID) -> List[CollectionOutput]:
        """
        Get all collections associated with a user.
        """
        logger.info(f"Fetching collections for user: {user_id}")
        return self.user_collection_repository.get_user_collections(user_id)

    def add_user_to_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        """
        Add a user to a collection.
        """
        logger.info(f"Adding user {user_id} to collection {collection_id}")
        try:
            # Check if the collection exists
            # if not self.user_collection_repository.get_user_collection(user_id, collection_id):
            #    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
            
            return self.user_collection_repository.add_user_to_collection(user_id, collection_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding user to collection: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Failed to add user to collection: {str(e)}")

    def remove_user_from_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        """
        Remove a user from a collection.
        """
        logger.info(f"Removing user {user_id} from collection {collection_id}")
        try:
            return self.user_collection_repository.remove_user_from_collection(user_id, collection_id)
        except Exception as e:
            logger.error(f"Error removing user from collection: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                detail=f"Failed to remove user from collection: {str(e)}")

    def get_collection_users(self, collection_id: UUID) -> List[UserCollectionOutput]:
        """
        Get all users associated with a collection.
        """
        logger.info(f"Fetching users for collection: {collection_id}")
        try:
            return self.user_collection_repository.get_collection_users(collection_id)
        except Exception as e:
            logger.error(f"Error fetching users for collection: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                detail=f"Failed to fetch users for collection: {str(e)}")

    def remove_all_users_from_collection(self, collection_id: UUID) -> bool:
        """
        Remove all users from a collection.
        """
        logger.info(f"Removing all users from collection {collection_id}")
        try:
            return self.user_collection_repository.remove_all_users_from_collection(collection_id)
        except Exception as e:
            logger.error(f"Error removing all users from collection: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                detail=f"Failed to remove all users from collection: {str(e)}")