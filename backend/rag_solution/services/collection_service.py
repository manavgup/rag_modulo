# collection_service.py
import multiprocessing
import re
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.config import settings
from core.custom_exceptions import (
    CollectionProcessingError,
    DocumentIngestionError,
    DocumentProcessingError,
    DocumentStorageError,
    EmptyDocumentError,
    LLMProviderError,
    NotFoundError,
    NotFoundException,
    QuestionGenerationError,
    UnsupportedFileTypeError,
    ValidationError,
)
from core.logging_utils import get_logger
from rag_solution.data_ingestion.document_processor import DocumentProcessor
from rag_solution.repository.collection_repository import CollectionRepository
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput, CollectionStatus
from rag_solution.schemas.prompt_template_schema import PromptTemplateType
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.llm_model_service import LLMModelService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.question_service import QuestionService
from rag_solution.services.user_collection_service import UserCollectionService
from rag_solution.services.user_provider_service import UserProviderService
from vectordbs.data_types import Document
from vectordbs.error_types import CollectionError
from vectordbs.factory import get_datastore

logger = get_logger("services.collection")


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
        self.user_provider_service = UserProviderService(db)
        self.prompt_template_service = PromptTemplateService(db)
        self.llm_parameters_service = LLMParametersService(db)
        # Initialize question service
        self.question_service = QuestionService(db=db)
        self.llm_model_service = LLMModelService(db)

    @staticmethod
    def _generate_valid_collection_name() -> str:
        """Generate a valid and unique collection name that works for vectordbs"""
        # Generate a UUID-based name
        raw_name = f"collection_{uuid4().hex}"

        # Ensure the name contains only numbers, letters, and underscores
        valid_name = re.sub(r"[^a-zA-Z0-9_]", "", raw_name)

        return valid_name

    def create_collection(self, collection: CollectionInput) -> CollectionOutput:
        """Create a new collection in the database and vectordb"""
        # Check if collection with same name exists
        if self.collection_repository.get_by_name(collection.name):
            raise HTTPException(status_code=400, detail="Collection name already exists")

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
                logger.error(f"Failed to delete collection from vector store: {delete_exception!s}")
            logger.error(f"Error creating collection: {e!s}")
            raise HTTPException(status_code=400, detail=f"Failed to create collection: {e!s}")

    def get_collection(self, collection_id: UUID) -> CollectionOutput:
        """
        Get a collection by its ID.
        """
        try:
            return self.collection_repository.get(collection_id)
        except NotFoundException as e:
            logger.error(f"Collection not found: {e}, status_code={e.status_code}, message={e.message}")
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in service layer: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

    def update_collection(self, collection_id: UUID, collection_update: CollectionInput) -> CollectionOutput | None:
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
            logger.error(f"Error updating collection: {e!s}")
            raise HTTPException(status_code=400, detail=f"Failed to update collection: {e!s}")

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
            logger.error(f"Error deleting collection: {e!s}")
            raise HTTPException(status_code=400, detail=f"Failed to delete collection: {e!s}")

    def get_user_collections(self, user_id: UUID) -> list[CollectionOutput]:
        """
        Get all collections belonging to a user.
        """
        logger.info(f"Fetching collections for user: {user_id}")
        return self.collection_repository.get_user_collections(user_id)

    def create_collection_with_documents(
        self,
        collection_name: str,
        is_private: bool,
        user_id: UUID,
        files: list[UploadFile],
        background_tasks: BackgroundTasks,
    ) -> CollectionOutput:
        """
        Create a new collection with documents.
        """
        collection = None
        try:
            # Create the collection
            collection_input = CollectionInput(
                name=collection_name, is_private=is_private, users=[user_id], status=CollectionStatus.CREATED
            )
            collection = self.create_collection(collection_input)

            # Upload the files and create file records in the database
            document_ids = []
            for file in files:
                document_id = str(uuid4())  # create unique document ID
                self.file_management_service.upload_and_create_file_record(file, user_id, collection.id, document_id)
                document_ids.append(document_id)

            # Update status to PROCESSING
            self.update_collection_status(collection.id, CollectionStatus.PROCESSING)

            # Get file paths
            file_paths = [
                str(self.file_management_service.get_file_path(collection.id, file.filename)) for file in files
            ]

            # Process documents and generate questions as a background task
            background_tasks.add_task(
                self.process_documents, file_paths, collection.id, collection.vector_db_name, document_ids, user_id
            )
            logger.info(f"Collection with documents created successfully: {collection.id}")

            return collection
        except Exception as e:
            # Delete from vector database if it was created
            if collection:
                try:
                    self.vector_store.delete_collection(collection.vector_db_name)
                except CollectionError as exc:
                    logger.error(f"Error deleting collection from vector store: {exc!s}")
            logger.error(f"Error in create_collection_with_documents: {e!s}")
            raise HTTPException(status_code=400, detail=f"Failed to create collection with documents: {e!s}")

    async def process_documents(
        self, file_paths: list[str], collection_id: UUID, vector_db_name: str, document_ids: list[str], user_id: UUID
    ):
        """Process documents and generate questions for a collection.

        Args:
            file_paths: List of paths to documents
            collection_id: Collection UUID
            vector_db_name: Name of vector database collection
            document_ids: List of document IDs
            user_id: User UUID

        Raises:
            LLMProviderError: If no provider is available
            DocumentIngestionError: If document ingestion fails
            EmptyDocumentError: If no valid text chunks are found
            QuestionGenerationError: If question generation fails
            CollectionProcessingError: For other processing errors
        """
        # Get appropriate provider for user
        provider = self.user_provider_service.get_user_provider(user_id)
        if not provider:
            logger.error(f"No available LLM provider found for user {user_id}")
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise LLMProviderError(
                provider="unknown",
                error_type="provider_not_found",
                message=f"No available LLM provider found for user {user_id}",
            )

        # Process documents and get the processed data
        try:
            processed_documents = await self.ingest_documents(file_paths, vector_db_name, document_ids)
        except DocumentIngestionError as e:
            logger.error(f"Document ingestion failed: {e!s}")
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise CollectionProcessingError(
                collection_id=str(collection_id), stage="ingestion", error_type="ingestion_failed", message=str(e)
            )

        # Extract text chunks from processed documents
        logger.info("Extracting document chunks for question generation")
        document_texts = []
        for doc in processed_documents:
            for chunk in doc.chunks:
                if chunk.text:
                    document_texts.append(chunk.text)

        if not document_texts:
            logger.error(f"No valid text chunks found in documents for collection {collection_id}")
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise EmptyDocumentError(collection_id=str(collection_id))

        logger.info("Fetching Template")
        # Get question generation template
        template = self.prompt_template_service.get_by_type(user_id, PromptTemplateType.QUESTION_GENERATION)
        if not template:
            logger.error(f"Question generation template not found for user {user_id}")
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise NotFoundError(
                resource_type="PromptTemplate",
                resource_id=f"type:{PromptTemplateType.QUESTION_GENERATION}",
                message="Question generation template not found. This template should have been created during user initialization. Please try logging out and logging back in to reinitialize your account.",
            )

        # Get LLM parameters
        logger.info("Attempting to get parameters")
        parameters = self.llm_parameters_service.get_latest_or_default_parameters(user_id)
        if not parameters:
            logger.error(f"No LLM parameters found for user {user_id}")
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise ValidationError("No default LLM parameters found")
        logger.info(f"got parameters: {parameters}")
        # Generate questions
        try:
            logger.info("Attempting to generate questions")
            questions = await self.question_service.suggest_questions(
                texts=document_texts,
                collection_id=collection_id,
                user_id=user_id,
                provider_name=provider.name,
                template=template,
                parameters=parameters,
            )

            if not questions:
                logger.warning(f"No questions were generated for collection {collection_id}")
                self.update_collection_status(collection_id, CollectionStatus.ERROR)
                raise QuestionGenerationError(
                    collection_id=str(collection_id), error_type="no_questions", message="No questions were generated"
                )

            logger.info(f"Generated {len(questions)} questions for collection {collection_id}")
            self.update_collection_status(collection_id, CollectionStatus.COMPLETED)

        except (ValidationError, NotFoundError, LLMProviderError) as e:
            error_type = (
                "validation_error"
                if isinstance(e, ValidationError)
                else "template_not_found"
                if isinstance(e, NotFoundError)
                else "provider_error"
            )
            logger.error(f"Question generation failed ({error_type}): {e!s}")
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise QuestionGenerationError(
                collection_id=str(collection_id), error_type=error_type, message=str(e)
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during question generation: {e!s}")
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise QuestionGenerationError(
                collection_id=str(collection_id), error_type="unexpected_error", message=str(e)
            ) from e

    async def ingest_documents(
        self, file_paths: list[str], vector_db_name: str, document_ids: list[str]
    ) -> list[Document]:
        """Ingest documents and store them in the vector store.

        Args:
            file_paths: List of paths to documents
            vector_db_name: Name of vector database collection
            document_ids: List of document IDs

        Returns:
            List of processed Document objects

        Raises:
            DocumentProcessingError: If document processing fails
            DocumentStorageError: If storing in vector store fails
            DocumentIngestionError: For other ingestion-related errors
        """
        processed_documents = []
        with multiprocessing.Manager() as manager:
            processor = DocumentProcessor(manager)

            for file_path, document_id in zip(file_paths, document_ids, strict=False):
                logger.info(f"Processing file: {file_path}")
                try:
                    # Process the document
                    documents_iterator = processor.process_document(file_path, document_id)
                    async for document in documents_iterator:
                        processed_documents.append(document)
                        try:
                            # Store document in vector store
                            self.store_documents_in_vector_store([document], vector_db_name)
                        except DocumentStorageError as e:
                            logger.error(f"Failed to store document {document_id} in vector store: {e!s}")
                            raise DocumentIngestionError(
                                doc_id=document_id, stage="vector_store", error_type="storage_failed", message=str(e)
                            )
                except (UnsupportedFileTypeError, DocumentProcessingError) as e:
                    logger.error(f"Error processing file {file_path}: {e!s}")
                    raise DocumentIngestionError(
                        doc_id=document_id, stage="processing", error_type="processing_failed", message=str(e)
                    )
        logger.info("Document processing complete")
        return processed_documents

    def store_documents_in_vector_store(self, documents: list[Document], collection_name: str):
        """Store documents in the vector store.

        Args:
            documents: List of documents to store
            collection_name: Name of vector store collection

        Raises:
            DocumentStorageError: If storing documents fails
        """
        try:
            logger.info(f"Storing documents in collection {collection_name}")
            self.vector_store.add_documents(collection_name, documents)
            logger.info(f"Successfully stored documents in collection {collection_name}")
        except CollectionError as e:
            logger.error(f"Vector store error: {e!s}")
            raise DocumentStorageError(
                doc_id=documents[0].id if documents else "unknown",
                storage_path=collection_name,
                error_type="vector_store_error",
                message=str(e),
            )
        except Exception as e:
            logger.error(f"Unexpected error storing documents: {e!s}")
            raise DocumentStorageError(
                doc_id=documents[0].id if documents else "unknown",
                storage_path=collection_name,
                error_type="unexpected_error",
                message=str(e),
            )

    def update_collection_status(self, collection_id: UUID, status: CollectionStatus):
        """Update the status of a collection."""
        try:
            self.collection_repository.update(collection_id, {"status": status})
            logger.info(f"Updated collection {collection_id} status to {status}")
        except Exception as e:
            logger.error(f"Error updating status for collection {collection_id}: {e!s}")
