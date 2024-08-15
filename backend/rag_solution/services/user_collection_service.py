import logging
from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.rag_solution.repository.user_collection_repository import UserCollectionRepository
from backend.rag_solution.schemas.collection_schema import CollectionOutput
from backend.rag_solution.schemas.user_collection_schema import UserCollectionOutput
from backend.rag_solution.schemas.user_schema import UserOutput

logger = logging.getLogger(__name__)

class UserCollectionService:
    def __init__(self, db: Session):
        self.user_collection_repository = UserCollectionRepository(db)

    def add_user_to_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        try:
            logger.info(f"Adding user {user_id} to collection {collection_id}")
            result = self.user_collection_repository.add_user_to_collection(user_id, collection_id)
            if result:
                logger.info(f"Successfully added user {user_id} to collection {collection_id}")
            else:
                logger.warning(f"Failed to add user {user_id} to collection {collection_id}")
                raise HTTPException(status_code=404, detail="User or collection not found")
            return result
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error adding user {user_id} to collection {collection_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def remove_user_from_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        try:
            logger.info(f"Removing user {user_id} from collection {collection_id}")
            result = self.user_collection_repository.remove_user_from_collection(user_id, collection_id)
            if result:
                logger.info(f"Successfully removed user {user_id} from collection {collection_id}")
            else:
                logger.warning(f"Failed to remove user {user_id} from collection {collection_id}")
                raise HTTPException(status_code=404, detail="User or collection not found")
            return result
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error removing user {user_id} from collection {collection_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_user_collections(self, user_id: UUID) -> List[UserCollectionOutput]:
        try:
            logger.info(f"Fetching collections for user {user_id}")
            collections = self.user_collection_repository.get_user_collections(user_id)
            logger.info(f"Retrieved {len(collections)} collections for user {user_id}")
            return collections
        except Exception as e:
            logger.error(f"Error fetching collections for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_collection_users(self, collection_id: UUID) -> List[UserCollectionOutput]:
        try:
            logger.info(f"Fetching users for collection {collection_id}")
            user_collections = self.user_collection_repository.get_collection_users(collection_id)
            logger.info(f"Retrieved {len(user_collections)} users for collection {collection_id}")
            return user_collections
        except Exception as e:
            logger.error(f"Error fetching users for collection {collection_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def remove_all_users_from_collection(self, collection_id: UUID) -> bool:
        try:
            logger.info(f"Removing all users from collection {collection_id}")
            result = self.user_collection_repository.remove_all_users_from_collection(collection_id)
            if result:
                logger.info(f"Successfully removed all users from collection {collection_id}")
            else:
                logger.warning(f"No users were removed from collection {collection_id}")
            return result
        except Exception as e:
            logger.error(f"Error removing all users from collection {collection_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def _get_user_output(self, user_id: UUID) -> UserOutput:
        # This method should fetch the user details and return a UserOutput
        return UserOutput(user_id=user_id)

