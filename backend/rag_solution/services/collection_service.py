from uuid import UUID, uuid4
from typing import List, Optional
from fastapi import UploadFile, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.user_collection_service import UserCollectionService
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput
from rag_solution.repository.collection_repository import CollectionRepository
from vectordbs.error_types import CollectionError
from vectordbs.factory import get_datastore
from rag_solution.data_ingestion.ingestion import ingest_documents
import logging
from core.config import settings
import os
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CollectionService:
    """
    Service class for managing collections and their associated documents.
    """

    def __init__(self,
                 db: Session,
                 file_management_service: FileManagementService,
                 user_collection_service: UserCollectionService):
        self.collection_repository = CollectionRepository(db)
        self.file_management_service = file_management_service
        self.user_collection_service = user_collection_service
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
        collection_name = self._generate_valid_collection_name()
        try:
             # Check if all users exist
            for user_id in collection.users:
                user = self.user_collection_service.get_collection_users(user_id)
                if not user:
                    raise HTTPException(status_code=400, detail=f"User with id {user_id} does not exist")
            # 1. Create in relational database. This will also create a user-collection record.
            new_collection = self.collection_repository.create(collection)

            # 2. Create in vector database
            self.vector_store.create_collection(collection_name, {"is_private": collection.is_private})

            return new_collection
        except Exception as e:
            # Delete from vector database if it was created
            try:
                self.vector_store.delete_collection(collection_name)
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

            updated_collection = self.collection_repository.update(collection_id, collection_update)

            # Update in vector database
            if existing_collection.is_private != collection_update.is_private:
                self.vector_store.delete_collection(existing_collection.name)
                self.vector_store.create_collection(existing_collection.name, {"is_private": collection_update.is_private})

            return updated_collection
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

            # Delete from PostgreSQL
            deleted = self.collection_repository.delete(collection_id)
            if not deleted:
                raise Exception("Failed to delete collection from PostgreSQL")

            # Delete from vector database
            self.vector_store.delete_collection(collection.name)
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
            background_tasks.add_task(ingest_documents, file_paths, self.vector_store, str(collection.id))
            logger.info(f"Collection with documents created successfully: {collection.id}")

            return collection
        except Exception as e:
            # Delete from vector database if it was created
            try:
                self.vector_store.delete_collection(collection_name)
            except CollectionError as exc:
                logger.error(f"Error in create_collection_with_documents: {str(exc)}")
            logger.error(f"Error in create_collection_with_documents: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to create collection with documents: {str(e)}")
