"""
Collection service module for managing collections and their associated documents.

This module provides the CollectionService class which handles all operations
related to collections, including creation, updating, deletion, and document
processing.
"""

# collection_service.py
import re
from uuid import uuid4

from core.config import Settings
from core.custom_exceptions import (
    CollectionProcessingError,
    DocumentIngestionError,
    DocumentStorageError,
    EmptyDocumentError,
    LLMProviderError,
    NotFoundError,
    QuestionGenerationError,
    ValidationError,
)
from core.logging_utils import get_logger
from fastapi import BackgroundTasks, UploadFile
from pydantic import UUID4
from sqlalchemy.orm import Session
from vectordbs.data_types import Document
from vectordbs.error_types import CollectionError
from vectordbs.factory import VectorStoreFactory

from rag_solution.data_ingestion.ingestion import DocumentStore
from rag_solution.repository.collection_repository import CollectionRepository
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput, CollectionStatus
from rag_solution.schemas.file_schema import FileOutput
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateOutput, PromptTemplateType
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.llm_model_service import LLMModelService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.question_service import QuestionService
from rag_solution.services.user_collection_service import UserCollectionService
from rag_solution.services.user_provider_service import UserProviderService

logger = get_logger("services.collection")


class CollectionService:
    """
    Service class for managing collections and their associated documents.
    """

    def __init__(self, db: Session, settings: Settings) -> None:
        """Initialize CollectionService with dependency injection.

        Args
        ----
            db: Database session
            settings: Configuration settings
        """
        self.db = db
        self.settings = settings

        # Initialize repositories and services
        self.collection_repository = CollectionRepository(db)
        self.user_collection_service = UserCollectionService(db)
        self.file_management_service = FileManagementService(db, settings)

        # Create vector store factory and get the configured store
        vector_store_factory = VectorStoreFactory(settings)
        self.vector_store = vector_store_factory.get_datastore(settings.vector_db)

        # Initialize other services
        self.user_provider_service = UserProviderService(db, settings)
        self.prompt_template_service = PromptTemplateService(db)
        self.llm_parameters_service = LLMParametersService(db)
        self.question_service = QuestionService(db, settings)
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
        existing_collection = self.collection_repository.get_by_name(collection.name)
        if existing_collection:
            # Collection exists, raise error
            from rag_solution.core.exceptions import AlreadyExistsError

            raise AlreadyExistsError(resource_type="Collection", field="name", value=collection.name)

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
            raise

    def get_collection(self, collection_id: UUID4) -> CollectionOutput:
        """
        Get a collection by its ID.
        """
        return self.collection_repository.get(collection_id)

    def update_collection(self, collection_id: UUID4, collection_update: CollectionInput) -> CollectionOutput:
        """
        Update an existing collection.
        """
        try:
            # This will raise NotFoundError if not found - no need to check
            self.collection_repository.get(collection_id)

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
            raise

    def delete_collection(self, collection_id: UUID4) -> bool:
        """
        Delete a collection by its ID.
        """
        try:
            logger.info(f"Deleting collection: {collection_id}")
            # This will raise NotFoundError if not found - no need to check
            collection = self.collection_repository.get(collection_id)

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
            raise

    def get_user_collections(self, user_id: UUID4) -> list[CollectionOutput]:
        """
        Get all collections belonging to a user.
        """
        logger.info(f"Fetching collections for user: {user_id}")
        return self.collection_repository.get_user_collections(user_id)

    def create_collection_with_documents(
        self,
        collection_name: str,
        is_private: bool,
        user_id: UUID4,
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

            # Use shared processing logic for file upload and processing
            self._upload_files_and_trigger_processing(
                files, user_id, collection.id, collection.vector_db_name, background_tasks
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
            raise

    async def process_documents(
        self, file_paths: list[str], collection_id: UUID4, vector_db_name: str, document_ids: list[str], user_id: UUID4
    ) -> None:
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
        try:
            # Process documents into vector store
            processed_documents = await self._process_and_ingest_documents(
                file_paths, vector_db_name, document_ids, collection_id
            )

            # Extract document texts for question generation
            document_texts = self._extract_document_texts(processed_documents, collection_id)

            # Generate questions from processed documents
            await self._generate_collection_questions(document_texts, collection_id, user_id)

        except (DocumentIngestionError, EmptyDocumentError, QuestionGenerationError):
            # These exceptions already have proper collection status updates
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing documents for collection {collection_id}: {e!s}")
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise CollectionProcessingError(
                collection_id=str(collection_id), stage="processing", error_type="unexpected_error", message=str(e)
            ) from e

    async def _process_and_ingest_documents(
        self, file_paths: list[str], vector_db_name: str, document_ids: list[str], collection_id: UUID4
    ) -> list[Document]:
        """Process and ingest documents into vector store."""
        try:
            return await self.ingest_documents(file_paths, vector_db_name, document_ids)
        except DocumentIngestionError as e:
            logger.error(f"Document ingestion failed: {e!s}")
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise CollectionProcessingError(
                collection_id=str(collection_id), stage="ingestion", error_type="ingestion_failed", message=str(e)
            ) from e

    def _extract_document_texts(self, processed_documents: list[Document], collection_id: UUID4) -> list[str]:
        """Extract text chunks from processed documents."""
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

        return document_texts

    async def _generate_collection_questions(
        self, document_texts: list[str], collection_id: UUID4, user_id: UUID4
    ) -> None:
        """Generate questions for collection from document texts."""
        # Get provider and generation parameters
        provider = self.user_provider_service.get_user_provider(user_id)
        if provider is None:
            raise ValueError("No LLM provider found for user")

        template = self._get_question_generation_template(user_id)
        if template is None:
            raise ValueError("No question generation template found for user")

        parameters_input = self._get_llm_parameters_input(user_id)

        # Generate questions
        try:
            logger.info("Attempting to generate questions")
            questions = await self.question_service.suggest_questions(
                texts=document_texts,
                collection_id=collection_id,
                user_id=user_id,
                provider_name=provider.name,
                template=template,
                parameters=parameters_input,
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

    def _get_question_generation_template(self, user_id: UUID4) -> PromptTemplateOutput | None:
        """Get question generation template for user."""
        logger.info("Fetching Template")
        return self.prompt_template_service.get_by_type(user_id, PromptTemplateType.QUESTION_GENERATION)

    def _get_llm_parameters_input(self, user_id: UUID4) -> LLMParametersInput:
        """Get LLM parameters converted to input format."""
        logger.info("Attempting to get parameters")
        parameters = self.llm_parameters_service.get_latest_or_default_parameters(user_id)
        logger.info(f"got parameters: {parameters}")

        if parameters is None:
            raise ValueError("No LLM parameters found for user")

        return LLMParametersInput(
            name=parameters.name,
            description=parameters.description,
            user_id=parameters.user_id,
            temperature=parameters.temperature,
            max_new_tokens=parameters.max_new_tokens,
            top_p=parameters.top_p,
            top_k=parameters.top_k,
            repetition_penalty=parameters.repetition_penalty,
        )

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
        # Use DocumentStore for complete pipeline (processing + embedding + storage)
        try:
            document_store = DocumentStore(
                vector_store=self.vector_store, collection_name=vector_db_name, settings=self.settings
            )

            processed_documents = await document_store.load_documents(file_paths, document_ids)
            logger.info(f"Document processing complete using DocumentStore with document IDs: {document_ids}")
            return processed_documents

        except Exception as e:
            logger.error(f"Error during document ingestion: {e!s}")
            # Map to appropriate DocumentIngestionError
            if "processing" in str(e).lower():
                raise DocumentIngestionError(
                    doc_id="batch", stage="processing", error_type="processing_failed", message=str(e)
                ) from e
            elif "storage" in str(e).lower() or "vector" in str(e).lower():
                raise DocumentIngestionError(
                    doc_id="batch", stage="vector_store", error_type="storage_failed", message=str(e)
                ) from e
            else:
                raise DocumentIngestionError(
                    doc_id="batch", stage="unknown", error_type="unexpected_error", message=str(e)
                ) from e

    def store_documents_in_vector_store(self, documents: list[Document], collection_name: str) -> None:
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
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error storing documents: {e!s}")
            raise DocumentStorageError(
                doc_id=documents[0].id if documents else "unknown",
                storage_path=collection_name,
                error_type="unexpected_error",
                message=str(e),
            ) from e

    def _upload_files_and_trigger_processing(
        self,
        files: list[UploadFile],
        user_id: UUID4,
        collection_id: UUID4,
        collection_vector_db_name: str,
        background_tasks: BackgroundTasks,
    ) -> list[FileOutput]:
        """
        Shared method to upload files and trigger document processing.

        This method contains the common logic used by both create_collection_with_documents
        and upload_file_and_process to ensure consistent behavior.

        Args:
            files: List of files to upload
            user_id: User uploading the files
            collection_id: Collection to add files to
            collection_vector_db_name: Vector DB collection name
            background_tasks: Background tasks for processing

        Returns:
            List of FileOutput objects for uploaded files
        """
        try:
            # Upload files and create file records
            file_records = []
            document_ids = []
            file_paths = []

            for file in files:
                # Create unique document ID
                document_id = str(uuid4())
                document_ids.append(document_id)

                # Upload file and create file record
                file_record = self.file_management_service.upload_and_create_file_record(
                    file, user_id, collection_id, document_id
                )
                file_records.append(file_record)

                # Get file path for processing
                if file.filename is None:
                    raise ValueError("File must have a filename")

                file_path = str(self.file_management_service.get_file_path(collection_id, file.filename))
                file_paths.append(file_path)

            # Update collection status to PROCESSING
            self.update_collection_status(collection_id, CollectionStatus.PROCESSING)

            # Process documents and generate questions as a background task
            background_tasks.add_task(
                self.process_documents, file_paths, collection_id, collection_vector_db_name, document_ids, user_id
            )

            logger.info(f"Files uploaded and processing started for collection: {collection_id}")

            return file_records

        except Exception as e:
            logger.error(f"Error in _upload_files_and_trigger_processing: {e!s}")
            raise

    def upload_file_and_process(
        self,
        file: UploadFile,
        user_id: UUID4,
        collection_id: UUID4,
        background_tasks: BackgroundTasks,
    ) -> FileOutput:
        """
        Upload a file to an existing collection and trigger document processing.

        Args:
            file: File to upload
            user_id: User uploading the file
            collection_id: Existing collection to add file to
            background_tasks: Background tasks for processing

        Returns:
            FileOutput object for the uploaded file
        """
        try:
            # Verify collection exists
            collection = self.get_collection(collection_id)

            # Use shared processing logic
            file_records = self._upload_files_and_trigger_processing(
                [file], user_id, collection_id, collection.vector_db_name, background_tasks
            )

            return file_records[0]

        except Exception as e:
            logger.error(f"Error in upload_file_and_process: {e!s}")
            raise

    def update_collection_status(self, collection_id: UUID4, status: CollectionStatus) -> None:
        """Update the status of a collection."""
        try:
            self.collection_repository.update(collection_id, {"status": status})
            logger.info(f"Updated collection {collection_id} status to {status}")
        except Exception as e:
            logger.error(f"Error updating status for collection {collection_id}: {e!s}")
