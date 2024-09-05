import logging
from typing import List
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.rag_solution.repository.user_collection_repository import UserCollectionRepository
from backend.rag_solution.repository.collection_repository import CollectionRepository
from backend.rag_solution.schemas.user_collection_schema import UserCollectionDetailOutput, UserCollectionsOutput
from backend.rag_solution.schemas.collection_schema import CollectionOutput

logger = logging.getLogger(__name__)

class UserCollectionInteractionService:
    def __init__(self, db: Session):
        self.db = db
        self.user_collection_repository = UserCollectionRepository(db)
        self.collection_repository = CollectionRepository(db)

    def get_user_collections_with_files(self, user_id: UUID) -> UserCollectionsOutput:
        """
        Get all collections associated with a user, including file information.
        """
        logger.info(f"Fetching collections with files for user: {user_id}")
        try:
            user_collections = self.user_collection_repository.get_user_collections(user_id)
            if not user_collections:
                return UserCollectionsOutput(user_id=user_id, collections=[])
            
            detailed_collections = []
            for collection in user_collections:
                # Fetch the full collection details including files
                full_collection = self.collection_repository.get(collection.collection_id)
                detailed_collections.append(
                    UserCollectionDetailOutput(
                        collection_id=full_collection.id,
                        name=full_collection.name,
                        is_private=full_collection.is_private,
                        created_at=full_collection.created_at,
                        updated_at=full_collection.updated_at,
                        files=full_collection.files,
                        status=full_collection.status
                    )
                )
            return UserCollectionsOutput(user_id=user_id, collections=detailed_collections)
        except Exception as e:
            logger.error(f"Error fetching collections with files for user {user_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                detail=f"Failed to fetch collections with files: {str(e)}")

    # Add other methods that involve both user and collection operations here