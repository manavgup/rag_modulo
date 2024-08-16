import logging
import os
import re
from typing import List, Optional
from uuid import UUID, uuid4

from backend.core.config import settings
from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.rag_solution.data_ingestion.ingestion import ingest_documents
from backend.rag_solution.repository.collection_repository import CollectionRepository
from backend.rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput
from backend.rag_solution.services.file_management_service import FileManagementService
from backend.rag_solution.services.user_collection_service import UserCollectionService
from backend.rag_solution.services.user_service import UserService
from backend.vectordbs.error_types import CollectionError
from backend.vectordbs.factory import get_datastore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CollectionService:
    """
    Service class for managing collections and their associated documents.
    """

    def __init__(self,
                 db: Session,
                 file_management_service: FileManagementService = None,
                 user_collection_service: UserCollectionService = None):
        self.collection_repository = CollectionRepository(db)
        self.file_management_service = file_management_service or FileManagementService(db)
        self.user_collection_service = user_collection_service or UserCollectionService(db)
        self.vector_store = get_datastore(settings.vector_db)

    @staticmethod
    def _generate_valid_collection_name() -> str:
        """ Generate a valid and unique collection name that works for vectordbs """
        # Generate a UUID-based name
        raw_name = f"collection_{uuid4().hex}"

        # Ensure the name contains only numbers, letters, and underscores
        valid_name = re.sub(r'[^a-zA-Z0-9_]', '', raw_name)

        return valid_name

    def create_collection(self, collection: CollectionInput) -> CollectionOutput:
        """ Create a new collection in the database and vectordb """
        vector_db_name = self._generate_valid_collection_name()
        try:
            logger.info(f"Creating collection: {collection.name} (Vector DB: {vector_db_name})")
            # 1. Create in relational database. This will also create a user-collection record.
            new_collection = self.collection_repository.create(collection, vector_db_name)

            # 2. Create in vector database
            self.vector_store.create_collection(vector_db_name, {"is_private": collection.is_private})
            logger.info(f"Collections created in both databases: {new_collection.id}")

            # 3. Add the creator to the collection
            for user_id in collection.users:
                self.user_collection_service.add_user_to_collection(user_id, new_collection.id)
                new_collection.user_ids.append(user_id)

            return new_collection
        except Exception as e:
            # Delete from vector database if it was created
            try:
                self.vector_store.delete_collection(vector_db_name)
            except CollectionError as delete_exception:
                logger.error(f"Failed to delete collection from vector store: {str(delete_exception)}")
            logger.error(f"Error creating collection: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to create collection: {str(e)}")

    def get_collection(self, collection_id: UUID) -> Optional[CollectionOutput]:
        """
        Get a collection by its ID.

        Args:
            collection_id (UUID): The ID of the collection to retrieve.

        Returns:
            Optional[CollectionOutput]: The collection if found, None otherwise.
        """
        collection = self.collection_repository.get(collection_id)
        if collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return collection

    def update_collection(self, collection_id: UUID, collection_update: CollectionInput) -> Optional[CollectionOutput]:
        """
        Update an existing collection.

        Args:
            collection_id (UUID): The ID of the collection to update.
            collection_update (CollectionInput): The update data for the collection.

        Returns:
            Optional[CollectionInDB]: The updated collection if found, None otherwise.
        """
        try:
            existing_collection = self.collection_repository.get(collection_id)
            if not existing_collection:
                logger.warning(f"Collection not found for update: {collection_id}")
                raise HTTPException(status_code=404, detail="Collection not found")

            # Fetch User instances corresponding to the UUIDs in collection_update.users
            logger.info(f"fetching users for collection: {collection_id}")
            user_collection_outputs = self.user_collection_service.get_collection_users(collection_id)
            logger.info(f"User instances fetched successfully: {len(user_collection_outputs)}")

            # Update the existing collection with the new data
            logger.info(f"Updating collection with {collection_update.name} and {len(user_collection_outputs)} users")
            update_data = {
                "name": collection_update.name,
                "is_private": collection_update.is_private,
            }

            # update the database
            self.collection_repository.update(collection_id, update_data)

            # Update user associations
            existing_user_ids = {uco.user_id for uco in user_collection_outputs}
            updated_user_ids = set(collection_update.users)
            logger.info(f"existing_users: {existing_user_ids}, updated_uers: {updated_user_ids}")

            users_to_add = updated_user_ids - existing_user_ids
            users_to_remove = existing_user_ids - updated_user_ids

            logger.info(f"Adding {len(users_to_add)} users.")

            for user_id in users_to_add:
                self.user_collection_service.add_user_to_collection(user_id, collection_id)
            logger.info(f"Removing {len(users_to_remove)} users.")
            for user_id in users_to_remove:
                self.user_collection_service.remove_user_from_collection(user_id, collection_id)

            return self.collection_repository.get(collection_id)
        except Exception as e:
            logger.error(f"Error updating collection: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to update collection: {str(e)}")

    def delete_collection(self, collection_id: UUID) -> bool:
        """
        Delete a collection by its ID.

        Args:
            collection_id (UUID): The ID of the collection to delete.

        Returns:
            bool: True if the collection was deleted, False otherwise.

        Raises:
            Exception: If there's an error during collection deletion.
        """
        try:
            logger.info(f"Deleting collection: {collection_id}")
            collection = self.collection_repository.get(collection_id)
            if not collection:
                logger.warning(f"Collection not found for deletion: {collection_id}")
                return False

            # Remove all users from the collection
            self.user_collection_service.remove_all_users_from_collection(collection_id)

            # Delete from PostgreSQL
            deleted = self.collection_repository.delete(collection_id)
            if not deleted:
                raise Exception("Failed to delete collection from PostgreSQL")

            # Delete from vector database
            self.vector_store.delete_collection(collection.vector_db_name)
            logger.info(f"Collection {collection_id} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to delete collection: {str(e)}")

    def get_user_collections(self, user_id: UUID) -> List[CollectionOutput]:
        """
        Get all collections belonging to a user.
        """
        logger.info(f"Fetching collections for user: {user_id}")
        return self.collection_repository.get_user_collections(user_id)

    def create_collection_with_documents(self, collection_name: str, is_private: bool, user_id: UUID,
                                         files: List[UploadFile], background_tasks: BackgroundTasks) -> CollectionOutput:
        """
        Create a new collection with documents.
        """
        try:
            # Create the collection
            collection = self.create_collection(CollectionInput(name=collection_name, is_private=is_private, users=[user_id]))
            # Upload the files and create file records in database

            for file in files:
                self.file_management_service.upload_and_create_file_record(file, user_id, collection.id)

            # Ingest the documents into the collection as background task
            file_paths = [str(self.file_management_service.get_file_path(user_id, collection.id, file.filename)) for file in files]
            background_tasks.add_task(ingest_documents, file_paths, self.vector_store, collection.vector_db_name)
            logger.info(f"Collection with documents created successfully: {collection.id}")

            return collection
        except Exception as e:
            # Delete from vector database if it was created
            try:
                self.vector_store.delete_collection(collection.vector_db_name)
            except CollectionError as exc:
                logger.error(f"Error in create_collection_with_documents: {str(exc)}")
            logger.error(f"Error in create_collection_with_documents: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to create collection with documents: {str(e)}")
