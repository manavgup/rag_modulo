from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.custom_exceptions import DuplicateEntryError, NotFoundError
from core.logging_utils import get_logger
from rag_solution.models.collection import Collection
from rag_solution.repository.user_collection_repository import UserCollectionRepository
from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.schemas.user_collection_schema import UserCollectionOutput

logger = get_logger(__name__)


class UserCollectionService:
    def __init__(self, db: Session):
        self.db = db
        self.user_collection_repository = UserCollectionRepository(db)

    def get_user_collections(self, user_id: UUID) -> list[CollectionOutput]:
        try:
            collections = self.user_collection_repository.get_user_collections(user_id)
            # Need to convert UserCollectionOutput to CollectionOutput
            return [CollectionOutput.model_validate(c) for c in collections]
        except Exception as e:
            logger.error(f"Error fetching collections: {e!s}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def add_user_to_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        try:
            return self.user_collection_repository.add_user_to_collection(user_id, collection_id)
        except NotFoundError as e:
            raise HTTPException(status_code=e.status_code, detail=str(e)) from e
        except DuplicateEntryError as e:
            raise HTTPException(status_code=e.status_code, detail=str(e)) from e
        except Exception as e:
            logger.error(f"Error adding user to collection: {e!s}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def remove_user_from_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        try:
            return self.user_collection_repository.remove_user_from_collection(user_id, collection_id)
        except NotFoundError as e:
            raise HTTPException(status_code=e.status_code, detail=str(e)) from e
        except Exception as e:
            logger.error(f"Error removing user: {e!s}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def get_collection_users(self, collection_id: UUID) -> list[UserCollectionOutput]:
        try:
            # First check if collection exists
            collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
            if not collection:
                raise NotFoundError(
                    resource_id=str(collection_id),
                    resource_type="Collection",
                    message=f"Collection with id {collection_id} not found",
                )

            return self.user_collection_repository.get_collection_users(collection_id)
        except NotFoundError as e:
            raise HTTPException(status_code=e.status_code, detail=str(e)) from e
        except Exception as e:
            logger.error(f"Error fetching users: {e!s}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def remove_all_users_from_collection(self, collection_id: UUID) -> bool:
        try:
            if not self.user_collection_repository.remove_all_users_from_collection(collection_id):
                raise HTTPException(status_code=404, detail="Collection not found")
            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error removing users: {e!s}")
            raise HTTPException(status_code=500, detail="Internal server error") from e
