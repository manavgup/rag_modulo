import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from rag_solution.repository.collection_repository import CollectionRepository
from rag_solution.repository.user_collection_repository import UserCollectionRepository
from rag_solution.schemas.collection_schema import FileInfo
from rag_solution.schemas.user_collection_schema import UserCollectionDetailOutput, UserCollectionsOutput

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
                    # Ensure files are instances of FileInfo
                    files = []
                    for file in full_collection.files:
                        logger.info(f"File: id={file.id} filename={file.filename}")
                        if isinstance(file.id, UUID) and isinstance(file.filename, str):
                            files.append(FileInfo(id=file.id, filename=file.filename))
                        else:
                            logger.error(f"Invalid file data: id={file.id}, filename={file.filename}")
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
            )

    # ... (other methods remain the same)
