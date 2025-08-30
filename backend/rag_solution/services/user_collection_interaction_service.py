import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from rag_solution.repository.collection_repository import CollectionRepository
from rag_solution.repository.user_collection_repository import UserCollectionRepository
from rag_solution.schemas.user_collection_schema import UserCollectionDetailOutput, UserCollectionsOutput, FileInfo

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
            for user_collection in user_collections:
                # Fetch the full collection details including files
                full_collection = self.collection_repository.get(user_collection.collection_id)
                if full_collection:
                    logger.info(f"Fetched full collection: {full_collection}")
                    # Files are guaranteed to be valid by the data model
                    files = [FileInfo(id=file.id, filename=file.filename) for file in full_collection.files]
                    logger.info(f"Files Length: {len(files)}")
                    detailed_collections.append(
                        UserCollectionDetailOutput(
                            collection_id=full_collection.id,
                            name=full_collection.name,
                            is_private=full_collection.is_private,
                            created_at=full_collection.created_at,
                            updated_at=full_collection.updated_at,
                            files=files,
                            status=full_collection.status,
                        )
                    )
                    logger.info("Appending collection to detailed collections")
            return UserCollectionsOutput(user_id=user_id, collections=detailed_collections)
        except Exception as e:
            logger.error(f"Error fetching collections with files for user {user_id}: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch collections with files: {e!s}",
            ) from e

    def get_user_collections(self, user_id: UUID) -> UserCollectionsOutput:
        """
        Get all collections associated with a user (without detailed file information).
        """
        logger.info(f"Fetching collections for user: {user_id}")
        try:
            user_collections = self.user_collection_repository.get_user_collections(user_id)
            if not user_collections:
                return UserCollectionsOutput(user_id=user_id, collections=[])

            collections = []
            for user_collection in user_collections:
                collections.append(
                    UserCollectionDetailOutput(
                        collection_id=user_collection.collection_id,
                        name=user_collection.name,
                        is_private=user_collection.is_private,
                        created_at=user_collection.created_at,
                        updated_at=user_collection.updated_at,
                        files=user_collection.files,
                        status=user_collection.status,
                    )
                )
            return UserCollectionsOutput(user_id=user_id, collections=collections)
        except Exception as e:
            logger.error(f"Error fetching collections for user {user_id}: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch collections: {e!s}",
            ) from e

    def add_user_to_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        """
        Add a user to a collection.
        """
        logger.info(f"Adding user {user_id} to collection {collection_id}")
        try:
            return self.user_collection_repository.add_user_to_collection(user_id, collection_id)
        except Exception as e:
            logger.error(f"Error adding user to collection: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add user to collection: {e!s}",
            ) from e

    def remove_user_from_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        """
        Remove a user from a collection.
        """
        logger.info(f"Removing user {user_id} from collection {collection_id}")
        try:
            return self.user_collection_repository.remove_user_from_collection(user_id, collection_id)
        except Exception as e:
            logger.error(f"Error removing user from collection: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to remove user from collection: {e!s}",
            ) from e

    def get_collection_users(self, collection_id: UUID) -> list[UserCollectionDetailOutput]:
        """
        Get all users associated with a collection.
        """
        logger.info(f"Fetching users for collection: {collection_id}")
        try:
            user_collections = self.user_collection_repository.get_collection_users(collection_id)
            return [
                UserCollectionDetailOutput(
                    collection_id=uc.collection_id,
                    name=uc.name,
                    is_private=uc.is_private,
                    created_at=uc.created_at,
                    updated_at=uc.updated_at,
                    files=uc.files,
                    status=uc.status,
                )
                for uc in user_collections
            ]
        except Exception as e:
            logger.error(f"Error fetching collection users: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch collection users: {e!s}",
            ) from e
