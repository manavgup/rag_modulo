"""User collection service for managing user-collection relationships."""

from typing import Any

from core.logging_utils import get_logger
from pydantic import UUID4
from sqlalchemy.orm import Session

from rag_solution.core.exceptions import NotFoundError
from rag_solution.models.collection import Collection
from rag_solution.repository.user_collection_repository import UserCollectionRepository
from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.schemas.user_collection_schema import UserCollectionOutput

logger = get_logger(__name__)


class UserCollectionService:
    """Service for managing user-collection relationships."""

    def __init__(self: Any, db: Session) -> None:
        """Initialize the UserCollectionService.

        Args:
            db (Session): The database session.
        """
        self.db = db
        self.user_collection_repository = UserCollectionRepository(db)

    def get_user_collections(self, user_id: UUID4) -> list[CollectionOutput]:
        """Get all collections for a specific user.

        Args:
            user_id: The UUID of the user

        Returns:
            List of CollectionOutput objects for the user
        """
        user_collections = self.user_collection_repository.get_user_collections(user_id)
        collections = []
        for uc in user_collections:
            # Convert UserCollectionOutput to CollectionOutput
            collection_data = {
                "id": uc.id,
                "name": uc.name,
                "vector_db_name": uc.vector_db_name,
                "is_private": uc.is_private,
                "created_at": uc.created_at,
                "updated_at": uc.updated_at,
                "user_ids": uc.user_ids,
                "files": uc.files,
                "status": uc.status,
            }
            collections.append(CollectionOutput.model_validate(collection_data))
        return collections

    def add_user_to_collection(self, user_id: UUID4, collection_id: UUID4) -> bool:
        """Add a user to a collection.

        Args:
            user_id: The UUID of the user to add
            collection_id: The UUID of the collection

        Returns:
            True if the user was added successfully
        """
        return self.user_collection_repository.add_user_to_collection(user_id, collection_id)

    def remove_user_from_collection(self, user_id: UUID4, collection_id: UUID4) -> bool:
        """Remove a user from a collection.

        Args:
            user_id: The UUID of the user to remove
            collection_id: The UUID of the collection

        Returns:
            True if the user was removed successfully
        """
        return self.user_collection_repository.remove_user_from_collection(user_id, collection_id)

    def get_collection_users(self, collection_id: UUID4) -> list[UserCollectionOutput]:
        """Get all users for a specific collection.

        Args:
            collection_id: The UUID of the collection

        Returns:
            List of UserCollectionOutput objects for the collection

        Raises:
            NotFoundError: If the collection doesn't exist
        """
        collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            raise NotFoundError(resource_type="Collection", resource_id=str(collection_id))
        return self.user_collection_repository.get_collection_users(collection_id)

    def remove_all_users_from_collection(self, collection_id: UUID4) -> bool:
        """Remove all users from a collection.

        Args:
            collection_id: The UUID of the collection

        Returns:
            True if users were removed successfully
        """
        return self.user_collection_repository.remove_all_users_from_collection(collection_id)
