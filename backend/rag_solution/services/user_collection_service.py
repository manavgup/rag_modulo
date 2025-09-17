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
    def __init__(self: Any, db: Session) -> None:
        self.db = db
        self.user_collection_repository = UserCollectionRepository(db)

    def get_user_collections(self, user_id: UUID4) -> list[CollectionOutput]:
        collections = self.user_collection_repository.get_user_collections(user_id)
        return [CollectionOutput.model_validate(c) for c in collections]

    def add_user_to_collection(self, user_id: UUID4, collection_id: UUID4) -> bool:
        return self.user_collection_repository.add_user_to_collection(user_id, collection_id)

    def remove_user_from_collection(self, user_id: UUID4, collection_id: UUID4) -> bool:
        return self.user_collection_repository.remove_user_from_collection(user_id, collection_id)

    def get_collection_users(self, collection_id: UUID4) -> list[UserCollectionOutput]:
        collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            raise NotFoundError(resource_type="Collection", resource_id=str(collection_id))
        return self.user_collection_repository.get_collection_users(collection_id)

    def remove_all_users_from_collection(self, collection_id: UUID4) -> bool:
        return self.user_collection_repository.remove_all_users_from_collection(collection_id)
