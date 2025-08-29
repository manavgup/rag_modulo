from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.custom_exceptions import DuplicateEntryError, NotFoundError, RepositoryError
from core.logging_utils import get_logger
from rag_solution.models.collection import Collection
from rag_solution.models.user import User
from rag_solution.models.user_collection import UserCollection
from rag_solution.schemas.user_collection_schema import FileInfo, UserCollectionOutput

logger = get_logger(__name__)


class UserCollectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_user_to_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        # First check if collection exists
        collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            raise NotFoundError(
                resource_id=str(collection_id),
                resource_type="Collection",
                message=f"Collection with id {collection_id} not found.",
            )

        # Check if user exists (assuming you have a User model)
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError(
                resource_id=str(user_id), resource_type="User", message=f"User with id {user_id} not found."
            )

        existing_entry = (
            self.db.query(UserCollection)
            .filter(UserCollection.user_id == user_id, UserCollection.collection_id == collection_id)
            .first()
        )

        if existing_entry:
            logger.info(f"User {user_id} is already in collection {collection_id}.")
            return True

        try:
            user_collection = UserCollection(user_id=user_id, collection_id=collection_id)
            self.db.add(user_collection)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"IntegrityError: {e!s}")
            raise DuplicateEntryError(
                param_name="UserCollection", message=f"User {user_id} is already in collection {collection_id}"
            ) from e

    def remove_user_from_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        # First check if the relationship exists
        user_collection = (
            self.db.query(UserCollection)
            .filter(UserCollection.user_id == user_id, UserCollection.collection_id == collection_id)
            .first()
        )

        if not user_collection:
            raise NotFoundError(
                resource_id=str(user_id),
                resource_type="UserCollection",
                message=f"User {user_id} is not in collection {collection_id}",
            )

        try:
            self.db.delete(user_collection)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database error: {e!s}")
            raise RepositoryError(f"Failed to remove user from collection: {e!s}") from e

    def get_user_collections(self, user_id: UUID) -> list[UserCollectionOutput]:
        try:
            user_collections = self.db.query(UserCollection).filter(UserCollection.user_id == user_id).all()
            return [self._to_output(uc) for uc in user_collections]
        except Exception as e:
            logger.error(f"Database error: {e!s}")
            raise RepositoryError(f"Failed to get user collections: {e!s}") from e

    def get_collection_users(self, collection_id: UUID) -> list[UserCollectionOutput]:
        try:
            user_collections = self.db.query(UserCollection).filter(UserCollection.collection_id == collection_id).all()
            return [self._to_output(uc) for uc in user_collections]
        except Exception as e:
            logger.error(f"Database error: {e!s}")
            raise RepositoryError(f"Failed to get collection users: {e!s}") from e

    def remove_all_users_from_collection(self, collection_id: UUID) -> bool:
        try:
            result = self.db.query(UserCollection).filter(UserCollection.collection_id == collection_id).delete()
            self.db.commit()
            return result > 0
        except Exception as e:
            logger.error(f"Database error: {e!s}")
            self.db.rollback()
            raise RepositoryError(f"Failed to remove all users from collection: {e!s}") from e

    def get_user_collection(self, user_id: UUID, collection_id: UUID) -> UserCollectionOutput | None:
        try:
            user_collection = (
                self.db.query(UserCollection)
                .filter(UserCollection.user_id == user_id, UserCollection.collection_id == collection_id)
                .first()
            )
            return self._to_output(user_collection) if user_collection else None
        except Exception as e:
            logger.error(f"Database error: {e!s}")
            raise RepositoryError(f"Failed to get user collection: {e!s}") from e

    def _to_output(self, user_collection: UserCollection) -> UserCollectionOutput:
        collection = user_collection.collection
        if not collection:
            logger.error(f"Collection {user_collection.collection_id} not found")
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
