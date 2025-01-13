# collection_service.py

import logging
import os
import re
from typing import List, Optional
from uuid import UUID, uuid4

from core.config import settings
from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy.orm import Session

from rag_solution.data_ingestion.document_processor import DocumentProcessor
from rag_solution.repository.collection_repository import CollectionRepository
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput, CollectionStatus
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.user_collection_service import UserCollectionService
from rag_solution.services.question_service import QuestionService
from rag_solution.services.llm_provider_service import LLMProviderService
from vectordbs.error_types import CollectionError
from vectordbs.factory import get_datastore
from vectordbs.data_types import Document
from vectordbs.vector_store import VectorStore
from core.custom_exceptions import DocumentStorageError, LLMProviderError
import multiprocessing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CollectionService:
    """
    Service class for managing collections and their associated documents.
    """

    def __init__(self, db: Session):
        self.db = db
        self.collection_repository = CollectionRepository(db)
        self.user_collection_service = UserCollectionService(db)
        self.file_management_service = FileManagementService(db)
        self.vector_store = get_datastore(settings.vector_db)
        self.llm_provider_service = LLMProviderService(db)
        # Initialize question service
        self.question_service = QuestionService(db=db)

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
            # Create in both relational and vector databases
            new_collection = self.collection_repository.create(collection, vector_db_name)
            self.vector_store.create_collection(vector_db_name, {"is_private": collection.is_private})
            logger.info(f"Collections created in both databases: {new_collection.id}")

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
        """
        collection = self.collection_repository.get(collection_id)
        if collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return collection

    def update_collection(self, collection_id: UUID, collection_update: CollectionInput) -> Optional[CollectionOutput]:
        """
        Update an existing collection.
        """
        try:
            existing_collection = self.collection_repository.get(collection_id)
            if not existing_collection:
                logger.warning(f"Collection not found for update: {collection_id}")
                raise HTTPException(status_code=404, detail="Collection not found")

            # Fetch User instances corresponding to the UUIDs in collection_update.users
            logger.info(f"Fetching users for collection: {collection_id}")
            user_collection_outputs = self.user_collection_service.get_collection_users(collection_id)
            logger.info(f"User instances fetched successfully: {len(user_collection_outputs)}")

            # Update the existing collection with the new data
            logger.info(f"Updating collection with {collection_update.name} and {len(user_collection_outputs)} users")
            update_data = {
                "name": collection_update.name,
                "is_private": collection_update.is_private,
            }

            # Update the database
            self.collection_repository.update(collection_id, update_data)

            # Update user associations
            existing_user_ids = {uco.user_id for uco in user_collection_outputs}
            updated_user_ids = set(collection_update.users)
            logger.info(f"Existing users: {existing_user_ids}, Updated users: {updated_user_ids}")

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
        collection = None
        try:
            # Create the collection
            collection_input = CollectionInput(
                name=collection_name,
                is_private=is_private,
                users=[user_id],
                status=CollectionStatus.CREATED
            )
            collection = self.create_collection(collection_input)

            # Upload the files and create file records in the database
            document_ids = []
            for file in files:
                document_id = str(uuid4()) # create unique document ID
                self.file_management_service.upload_and_create_file_record(file, user_id, collection.id, document_id)
                document_ids.append(document_id)

            # Update status to PROCESSING
            self.update_collection_status(collection.id, CollectionStatus.PROCESSING)

            # Get file paths
            file_paths = [str(self.file_management_service.get_file_path(collection.id, file.filename)) for file in files]

            # Process documents and generate questions as a background task
            background_tasks.add_task(self.process_documents, file_paths, collection.id, collection.vector_db_name, document_ids, user_id)
            logger.info(f"Collection with documents created successfully: {collection.id}")

            return collection
        except Exception as e:
            # Delete from vector database if it was created
            if collection:
                try:
                    self.vector_store.delete_collection(collection.vector_db_name)
                except CollectionError as exc:
                    logger.error(f"Error deleting collection from vector store: {str(exc)}")
            logger.error(f"Error in create_collection_with_documents: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to create collection with documents: {str(e)}")

    async def process_documents(self, file_paths: List[str], collection_id: UUID, 
                                vector_db_name: str, document_ids: List[str], user_id: UUID):
        try:
            # Get appropriate provider for user
            provider = self.llm_provider_service.get_user_provider(user_id)
            if not provider:
                raise LLMProviderError("No available LLM provider found")
            
            # Process documents and get the processed data
            processed_documents = await self.ingest_documents(file_paths, vector_db_name, document_ids)

            # Generate questions using the processed documents
            document_texts = []
            for doc in processed_documents:
                for chunk in doc.chunks:
                    if chunk.text:
                        document_texts.append(chunk.text)
            # Suggest example questions
            await self.question_service.suggest_questions(
                texts=document_texts,
                collection_id=collection_id,
                user_id=user_id,
                provider_name=provider.name
            )
            logger.info(f"Generated questions for collection {collection_id}")

            # Update collection status to COMPLETED
            self.update_collection_status(collection_id, CollectionStatus.COMPLETED)
        except Exception as e:
            logger.error(f"Error processing documents for collection {collection_id}: {str(e)}")
            self.update_collection_status(collection_id, CollectionStatus.ERROR)

    async def ingest_documents(self, file_paths: List[str], vector_db_name: str, document_ids: List[str]) -> List[Document]:
        """Ingest documents and store them in the vector store."""
        processed_documents = []
        with multiprocessing.Manager() as manager:
            processor = DocumentProcessor(manager)

            for file_path, document_id in zip(file_paths, document_ids):
                logger.info(f"Processing file: {file_path}")
                try:
                    # Process the document
                    documents_iterator = processor.process_document(file_path, document_id)
                    async for document in documents_iterator:
                        processed_documents.append(document)
                        # Store document in vector store
                        self.store_documents_in_vector_store([document], vector_db_name)
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}", exc_info=True)
                    raise e
        return processed_documents

    def store_documents_in_vector_store(self, documents: List[Document], collection_name: str):
        """Store documents in the vector store."""
        try:
            logger.info(f"Storing documents in collection {collection_name}")
            self.vector_store.add_documents(collection_name, documents)
            logger.info(f"Successfully stored documents in collection {collection_name}")
        except Exception as e:
            logger.error(f"Error storing documents: {e}", exc_info=True)
            raise DocumentStorageError(f"Error: {e}")

    def update_collection_status(self, collection_id: UUID, status: CollectionStatus):
        """Update the status of a collection."""
        try:
            self.collection_repository.update(collection_id, {"status": status})
            logger.info(f"Updated collection {collection_id} status to {status}")
        except Exception as e:
            logger.error(f"Error updating status for collection {collection_id}: {str(e)}")
