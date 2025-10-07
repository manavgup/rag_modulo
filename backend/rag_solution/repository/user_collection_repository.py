"""User collection repository for managing user-collection relationships in the database."""

from typing import Any

from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from core.custom_exceptions import RepositoryError
from core.logging_utils import get_logger
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError
from rag_solution.models.collection import Collection
from rag_solution.models.user import User
from rag_solution.models.user_collection import UserCollection
from rag_solution.schemas.user_collection_schema import FileInfo, UserCollectionOutput

logger = get_logger(__name__)


class UserCollectionRepository:
    """Repository for managing user-collection relationships in the database."""

    def __init__(self: Any, db: Session) -> None:
        """Initialize the UserCollectionRepository.

        Args:
            db (Session): The database session.
        """
        self.db = db

    def add_user_to_collection(self, user_id: UUID4, collection_id: UUID4) -> bool:
        """Add a user to a collection.

        Args:
            user_id: The UUID of the user to add
            collection_id: The UUID of the collection to add the user to

        Returns:
            bool: True if the user was added successfully

        Raises:
            NotFoundError: If the user or collection doesn't exist
            AlreadyExistsError: If the user is already in the collection
        """
        # First check if collection exists
        collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            raise NotFoundError(resource_type="Collection", resource_id=str(collection_id))

        # Check if user exists (assuming you have a User model)
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError(resource_type="User", resource_id=str(user_id))

        existing_entry = (
            self.db.query(UserCollection)
            .filter(UserCollection.user_id == user_id, UserCollection.collection_id == collection_id)
            .first()
        )

        if existing_entry:
            logger.info("User %s is already in collection %s.", str(user_id), str(collection_id))
            return True

        try:
            user_collection = UserCollection(user_id=user_id, collection_id=collection_id)
            self.db.add(user_collection)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            logger.error("IntegrityError: %s", str(e))
            raise AlreadyExistsError(
                resource_type="UserCollection", field="user_id:collection_id", value=f"{user_id}:{collection_id}"
            ) from e

    def remove_user_from_collection(self, user_id: UUID4, collection_id: UUID4) -> bool:
        """Remove a user from a collection.

        Args:
            user_id: The UUID of the user to remove
            collection_id: The UUID of the collection to remove the user from

        Returns:
            bool: True if the user was removed successfully

        Raises:
            NotFoundError: If the user-collection relationship doesn't exist
            RepositoryError: If there's a database error
        """
        # First check if the relationship exists
        user_collection = (
            self.db.query(UserCollection)
            .filter(UserCollection.user_id == user_id, UserCollection.collection_id == collection_id)
            .first()
        )

        if not user_collection:
            raise NotFoundError(resource_type="UserCollection", resource_id=f"{user_id}:{collection_id}")

        try:
            self.db.delete(user_collection)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error("Database error: %s", str(e))
            raise RepositoryError(f"Failed to remove user from collection: {e!s}") from e

    def get_user_collections(self, user_id: UUID4) -> list[UserCollectionOutput]:
        """Get all collections for a specific user.

        Args:
            user_id: The UUID of the user

        Returns:
            List of UserCollectionOutput objects for the user

        Raises:
            RepositoryError: If there's a database error
        """
        try:
            user_collections = (
                self.db.query(UserCollection)
                .options(
                    joinedload(UserCollection.collection).joinedload(Collection.users),
                    joinedload(UserCollection.collection).joinedload(Collection.files),
                )
                .filter(UserCollection.user_id == user_id)
                .all()
            )
            return [self._to_output(uc) for uc in user_collections]
        except Exception as e:
            logger.error("Database error: %s", str(e))
            raise RepositoryError(f"Failed to get user collections: {e!s}") from e

    def get_collection_users(self, collection_id: UUID4) -> list[UserCollectionOutput]:
        """Get all users for a specific collection.

        Args:
            collection_id: The UUID of the collection

        Returns:
            List of UserCollectionOutput objects for the collection

        Raises:
            RepositoryError: If there's a database error
        """
        try:
            user_collections = self.db.query(UserCollection).filter(UserCollection.collection_id == collection_id).all()
            return [self._to_output(uc) for uc in user_collections]
        except Exception as e:
            logger.error("Database error: %s", str(e))
            raise RepositoryError(f"Failed to get collection users: {e!s}") from e

    def remove_all_users_from_collection(self, collection_id: UUID4) -> bool:
        """Remove all users from a collection.

        Args:
            collection_id: The UUID of the collection

        Returns:
            bool: True if users were removed successfully

        Raises:
            RepositoryError: If there's a database error
        """
        try:
            result = self.db.query(UserCollection).filter(UserCollection.collection_id == collection_id).delete()
            self.db.commit()
            return result > 0
        except Exception as e:
            logger.error("Database error: %s", str(e))
            self.db.rollback()
            raise RepositoryError(f"Failed to remove all users from collection: {e!s}") from e

    def get_user_collection(self, user_id: UUID4, collection_id: UUID4) -> UserCollectionOutput:
        """Get a specific user-collection relationship.

        Args:
            user_id: The UUID of the user
            collection_id: The UUID of the collection

        Returns:
            UserCollectionOutput object for the relationship

        Raises:
            NotFoundError: If the user-collection relationship doesn't exist
            RepositoryError: If there's a database error
        """
        try:
            user_collection = (
                self.db.query(UserCollection)
                .filter(UserCollection.user_id == user_id, UserCollection.collection_id == collection_id)
                .first()
            )
            if not user_collection:
                raise NotFoundError(resource_type="UserCollection", resource_id=f"{user_id}:{collection_id}")
            return self._to_output(user_collection)
        except Exception as e:
            logger.error("Database error: %s", str(e))
            raise RepositoryError(f"Failed to get user collection: {e!s}") from e

    def _to_output(self, user_collection: UserCollection) -> UserCollectionOutput:
        collection = user_collection.collection
        if not collection:
            logger.error("Collection %s not found", str(user_collection.collection_id))
            raise ValueError(f"Collection {user_collection.collection_id} not found")

        return UserCollectionOutput(
            id=collection.id,
            name=collection.name,
            vector_db_name=collection.vector_db_name,
            is_private=collection.is_private,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            user_ids=[uc.user_id for uc in collection.users],
            files=[FileInfo(id=f.id, filename=f.filename) for f in collection.files],
            status=collection.status,
            user_id=user_collection.user_id,
            collection_id=user_collection.collection_id,
        )
