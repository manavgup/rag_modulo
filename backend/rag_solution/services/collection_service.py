"""
Collection service module for managing collections and their associated documents.

This module provides the CollectionService class which handles all operations
related to collections, including creation, updating, deletion, and document
processing.
"""

# collection_service.py

from fastapi import BackgroundTasks, UploadFile
from pydantic import UUID4
from sqlalchemy.orm import Session

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
from core.identity_service import IdentityService
from core.logging_utils import get_logger
from rag_solution.core.exceptions import AlreadyExistsError
from rag_solution.data_ingestion.ingestion import DocumentStore
from rag_solution.repository.collection_repository import CollectionRepository
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput, CollectionStatus, FileInfo
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
from vectordbs.data_types import Document
from vectordbs.error_types import CollectionError
from vectordbs.factory import VectorStoreFactory

logger = get_logger("services.collection")


class CollectionService:  # pylint: disable=too-many-instance-attributes
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
        return IdentityService.generate_collection_name()

    def create_collection(self, collection: CollectionInput) -> CollectionOutput:
        """Create a new collection in the database and vectordb"""
        # Check if collection with same name exists
        existing_collection = self.collection_repository.get_by_name(collection.name)
        if existing_collection:
            # Collection exists, raise error
            raise AlreadyExistsError(resource_type="Collection", field="name", value=collection.name)

        vector_db_name = self._generate_valid_collection_name()
        try:
            logger.info(
                "Creating collection: %s (Vector DB: %s)",
                collection.name,
                vector_db_name,
            )
            # Create in both relational and vector databases
            new_collection = self.collection_repository.create(collection, vector_db_name)
            self.vector_store.create_collection(vector_db_name, {"is_private": collection.is_private})
            logger.info("Collections created in both databases: %s", str(new_collection.id))

            return new_collection
        except (ValueError, KeyError, AttributeError) as e:
            # Delete from vector database if it was created
            try:
                self.vector_store.delete_collection(vector_db_name)
            except CollectionError as delete_exception:
                logger.error(
                    "Failed to delete collection from vector store: %s",
                    str(delete_exception),
                )
            logger.error("Error creating collection: %s", str(e))
            raise

    def get_collection(self, collection_id: UUID4) -> CollectionOutput:
        """
        Get a collection by its ID with chunk counts from vector store.
        """
        collection = self.collection_repository.get(collection_id)

        # Enrich file info with chunk counts from vector store
        collection = self._add_chunk_counts_to_collection(collection)

        return collection

    def _add_chunk_counts_to_collection(self, collection: CollectionOutput) -> CollectionOutput:
        """
        Add chunk counts to file info by querying vector store.

        This method uses batch querying to avoid N+1 query problems. Instead of
        querying each document individually, it collects all document_ids and
        makes a single batch query to get chunk counts for all documents at once.

        Args:
            collection: Collection output to enrich with chunk counts

        Returns:
            Collection output with chunk counts added to each file
        """
        try:
            # Early return if no files
            if not collection.files:
                return collection

            # Collect all document_ids that need chunk counts
            document_ids = [file_info.document_id for file_info in collection.files if file_info.document_id]

            # Early return if no document_ids to query
            if not document_ids:
                # All files have no document_id, so chunk_count is 0 for all
                enriched_files = [
                    FileInfo(
                        id=file_info.id,
                        filename=file_info.filename,
                        file_size_bytes=file_info.file_size_bytes,
                        chunk_count=0,
                        document_id=file_info.document_id,
                    )
                    for file_info in collection.files
                ]
                return CollectionOutput(
                    id=collection.id,
                    name=collection.name,
                    vector_db_name=collection.vector_db_name,
                    is_private=collection.is_private,
                    created_at=collection.created_at,
                    updated_at=collection.updated_at,
                    files=enriched_files,
                    user_ids=collection.user_ids,
                    status=collection.status,
                )

            # OPTIMIZATION: Batch query all document chunk counts at once
            document_chunk_counts = self._get_batch_document_chunk_counts(collection.vector_db_name, document_ids)

            # Enrich files using the pre-computed chunk counts
            enriched_files = []
            for file_info in collection.files:
                chunk_count = 0
                if file_info.document_id:
                    chunk_count = document_chunk_counts.get(file_info.document_id, 0)

                enriched_files.append(
                    FileInfo(
                        id=file_info.id,
                        filename=file_info.filename,
                        file_size_bytes=file_info.file_size_bytes,
                        chunk_count=chunk_count,
                        document_id=file_info.document_id,
                    )
                )

            # Create new collection output with enriched files
            return CollectionOutput(
                id=collection.id,
                name=collection.name,
                vector_db_name=collection.vector_db_name,
                is_private=collection.is_private,
                created_at=collection.created_at,
                updated_at=collection.updated_at,
                files=enriched_files,
                user_ids=collection.user_ids,
                status=collection.status,
            )
        except Exception as e:
            logger.warning(
                "Failed to add chunk counts: %s. Returning collection without chunk counts",
                str(e),
            )
            return collection

    def _get_batch_document_chunk_counts(self, collection_name: str, document_ids: list[str]) -> dict[str, int]:
        """
        Get chunk counts for multiple documents with pagination support.

        This method optimizes performance by querying all document chunk counts
        at once using Milvus IN operator. For collections with >16,384 chunks,
        it automatically paginates to retrieve all results.

        Performance: 100 documents takes <1 second vs 5-50 seconds with individual queries.

        Args:
            collection_name: Vector store collection name
            document_ids: List of document IDs to count chunks for

        Returns:
            Dictionary mapping document_id to chunk count
        """
        try:
            # For Milvus, use pymilvus to query with IN expression filter
            from pymilvus import Collection

            # Early return if no document_ids
            if not document_ids:
                return {}

            # Load collection
            milvus_collection = Collection(collection_name)

            # Build batch query expression using IN operator
            # Format: document_id in ["id1", "id2", "id3"]
            import json

            document_ids_json = json.dumps(document_ids)
            expr = f"document_id in {document_ids_json}"

            # Paginate through results to handle collections with >16,384 chunks
            # Milvus constraint: offset + limit <= 16384
            document_chunk_counts: dict[str, int] = {}
            offset = 0
            page_size = 16384  # Milvus maximum
            total_chunks_retrieved = 0

            while True:
                # Query one page of results
                results = milvus_collection.query(
                    expr=expr,
                    output_fields=["document_id"],
                    limit=page_size,
                    offset=offset,
                )

                # Break if no more results
                if not results:
                    break

                # Count chunks per document_id in this page
                for result in results:
                    doc_id = result.get("document_id", "")
                    if doc_id:
                        document_chunk_counts[doc_id] = document_chunk_counts.get(doc_id, 0) + 1

                total_chunks_retrieved += len(results)

                # Break if we got fewer results than page_size (last page)
                if len(results) < page_size:
                    break

                # Move to next page
                offset += page_size

                # Safety check: Milvus constraint is offset + limit <= 16384
                # If next offset would exceed this, we can't paginate further
                if offset >= 16384:
                    logger.warning(
                        "Reached Milvus pagination limit (offset=%d) for collection %s. "
                        "Chunk counts may be incomplete if collection has >16,384 chunks.",
                        offset,
                        collection_name,
                    )
                    break

            logger.info(
                "Batch query for %d documents returned %d total chunks from collection %s (pages: %d)",
                len(document_ids),
                total_chunks_retrieved,
                collection_name,
                (offset // page_size) + 1,
            )

            return document_chunk_counts

        except ImportError:
            logger.warning("pymilvus not available, cannot count chunks")
            return dict.fromkeys(document_ids, 0)
        except Exception as e:
            logger.warning("Error getting batch chunk counts for collection %s: %s", collection_name, str(e))
            return dict.fromkeys(document_ids, 0)

    def update_collection(self, collection_id: UUID4, collection_update: CollectionInput) -> CollectionOutput:
        """
        Update an existing collection.
        """
        try:
            # This will raise NotFoundError if not found - no need to check
            self.collection_repository.get(collection_id)

            # Fetch User instances corresponding to the UUIDs in collection_update.users
            logger.info("Fetching users for collection: %s", str(collection_id))
            user_collection_outputs = self.user_collection_service.get_collection_users(collection_id)
            logger.info("User instances fetched successfully: %d", len(user_collection_outputs))

            # Update the existing collection with the new data
            logger.info(
                "Updating collection with %s and %d users",
                collection_update.name,
                len(user_collection_outputs),
            )
            update_data = {
                "name": collection_update.name,
                "is_private": collection_update.is_private,
            }

            # Update the database
            self.collection_repository.update(collection_id, update_data)

            # Update user associations
            existing_user_ids = {uco.user_id for uco in user_collection_outputs}
            updated_user_ids = set(collection_update.users)
            logger.info(
                "Existing users: %s, Updated users: %s",
                str(existing_user_ids),
                str(updated_user_ids),
            )

            users_to_add = updated_user_ids - existing_user_ids
            users_to_remove = existing_user_ids - updated_user_ids

            logger.info("Adding %d users.", len(users_to_add))
            for user_id in users_to_add:
                self.user_collection_service.add_user_to_collection(user_id, collection_id)

            logger.info("Removing %d users.", len(users_to_remove))
            for user_id in users_to_remove:
                self.user_collection_service.remove_user_from_collection(user_id, collection_id)

            return self.collection_repository.get(collection_id)
        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error updating collection: %s", str(e))
            raise

    def delete_collection(self, collection_id: UUID4) -> bool:
        """
        Delete a collection by its ID.
        """
        try:
            logger.info("Deleting collection: %s", str(collection_id))
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
            logger.info("Collection %s deleted successfully", str(collection_id))
            return True
        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error deleting collection: %s", str(e))
            raise

    def get_user_collections(self, user_id: UUID4) -> list[CollectionOutput]:
        """
        Get all collections belonging to a user.
        """
        logger.info("Fetching collections for user: %s", user_id)
        return self.collection_repository.get_user_collections(user_id)

    def create_collection_with_documents(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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
                name=collection_name,
                is_private=is_private,
                users=[user_id],
                status=CollectionStatus.CREATED,
            )
            collection = self.create_collection(collection_input)

            # Use shared processing logic for file upload and processing
            self._upload_files_and_trigger_processing(
                files,
                user_id,
                collection.id,
                collection.vector_db_name,
                background_tasks,
            )

            logger.info("Collection with documents created successfully: %s", collection.id)

            return collection
        except (ValueError, KeyError, AttributeError) as e:
            # Delete from vector database if it was created
            if collection:
                try:
                    self.vector_store.delete_collection(collection.vector_db_name)
                except CollectionError as exc:
                    logger.error("Error deleting collection from vector store: %s", str(exc))
            logger.error("Error in create_collection_with_documents: %s", str(e))
            raise

    async def process_documents(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        file_paths: list[str],
        collection_id: UUID4,
        vector_db_name: str,
        document_ids: list[str],
        user_id: UUID4,
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
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(
                "Unexpected error processing documents for collection %s: %s",
                str(collection_id),
                str(e),
            )
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise CollectionProcessingError(
                collection_id=str(collection_id),
                stage="processing",
                error_type="unexpected_error",
                message=str(e),
            ) from e

    async def _process_and_ingest_documents(
        self,
        file_paths: list[str],
        vector_db_name: str,
        document_ids: list[str],
        collection_id: UUID4,
    ) -> list[Document]:
        """Process and ingest documents into vector store."""
        try:
            return await self.ingest_documents(file_paths, vector_db_name, document_ids)
        except DocumentIngestionError as e:
            logger.error("Document ingestion failed: %s", str(e))
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise CollectionProcessingError(
                collection_id=str(collection_id),
                stage="ingestion",
                error_type="ingestion_failed",
                message=str(e),
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
            logger.error(
                "No valid text chunks found in documents for collection %s",
                str(collection_id),
            )
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
                logger.warning("No questions were generated for collection %s", str(collection_id))
                self.update_collection_status(collection_id, CollectionStatus.ERROR)
                raise QuestionGenerationError(
                    collection_id=str(collection_id),
                    error_type="no_questions",
                    message="No questions were generated",
                )

            logger.info(
                "Generated %d questions for collection %s",
                len(questions),
                str(collection_id),
            )
            self.update_collection_status(collection_id, CollectionStatus.COMPLETED)

        except (ValidationError, NotFoundError, LLMProviderError) as e:
            error_type = (
                "validation_error"
                if isinstance(e, ValidationError)
                else "template_not_found"
                if isinstance(e, NotFoundError)
                else "provider_error"
            )
            logger.error("Question generation failed (%s): %s", error_type, str(e))
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise QuestionGenerationError(
                collection_id=str(collection_id), error_type=error_type, message=str(e)
            ) from e
        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Unexpected error during question generation: %s", str(e))
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise QuestionGenerationError(
                collection_id=str(collection_id),
                error_type="unexpected_error",
                message=str(e),
            ) from e

    def _get_question_generation_template(self, user_id: UUID4) -> PromptTemplateOutput | None:
        """Get question generation template for user."""
        logger.info("Fetching Template")
        return self.prompt_template_service.get_by_type(user_id, PromptTemplateType.QUESTION_GENERATION)

    def _get_llm_parameters_input(self, user_id: UUID4) -> LLMParametersInput:
        """Get LLM parameters converted to input format."""
        logger.info("Attempting to get parameters")
        parameters = self.llm_parameters_service.get_latest_or_default_parameters(user_id)
        logger.info("got parameters: %s", parameters)

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
                vector_store=self.vector_store,
                collection_name=vector_db_name,
                settings=self.settings,
            )

            processed_documents = await document_store.load_documents(file_paths, document_ids)
            logger.info(
                "Document processing complete using DocumentStore with document IDs: %s",
                document_ids,
            )
            return processed_documents

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error during document ingestion: %s", str(e))
            # Map to appropriate DocumentIngestionError
            if "processing" in str(e).lower():
                raise DocumentIngestionError(
                    doc_id="batch",
                    stage="processing",
                    error_type="processing_failed",
                    message=str(e),
                ) from e
            if "storage" in str(e).lower() or "vector" in str(e).lower():
                raise DocumentIngestionError(
                    doc_id="batch",
                    stage="vector_store",
                    error_type="storage_failed",
                    message=str(e),
                ) from e
            else:
                raise DocumentIngestionError(
                    doc_id="batch",
                    stage="unknown",
                    error_type="unexpected_error",
                    message=str(e),
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
            logger.info("Storing documents in collection %s", collection_name)
            self.vector_store.add_documents(collection_name, documents)
            logger.info("Successfully stored documents in collection %s", collection_name)
        except CollectionError as e:
            logger.error("Vector store error: %s", str(e))
            raise DocumentStorageError(
                doc_id=documents[0].id if documents else "unknown",
                storage_path=collection_name,
                error_type="vector_store_error",
                message=str(e),
            ) from e
        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Unexpected error storing documents: %s", str(e))
            raise DocumentStorageError(
                doc_id=documents[0].id if documents else "unknown",
                storage_path=collection_name,
                error_type="unexpected_error",
                message=str(e),
            ) from e

    def _upload_files_and_trigger_processing(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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
                document_id = IdentityService.generate_document_id()
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
                self.process_documents,
                file_paths,
                collection_id,
                collection_vector_db_name,
                document_ids,
                user_id,
            )

            logger.info(
                "Files uploaded and processing started for collection: %s",
                str(collection_id),
            )

            return file_records

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error in _upload_files_and_trigger_processing: %s", str(e))
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
                [file],
                user_id,
                collection_id,
                collection.vector_db_name,
                background_tasks,
            )

            return file_records[0]

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error in upload_file_and_process: %s", str(e))
            raise

    def update_collection_status(self, collection_id: UUID4, status: CollectionStatus) -> None:
        """Update the status of a collection."""
        try:
            self.collection_repository.update(collection_id, {"status": status})
            logger.info("Updated collection %s status to %s", str(collection_id), status)
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(
                "Error updating status for collection %s: %s",
                str(collection_id),
                str(e),
            )

    def cleanup_orphaned_vector_collections(self) -> dict[str, int]:
        """
        Clean up orphaned collections in the vector database.

        Identifies collections that exist in the vector database (Milvus) but have no
        corresponding record in the PostgreSQL collections table, and removes them.

        Returns:
            dict: Summary with counts of found and deleted collections

        Raises:
            CollectionError: If cleanup operation fails
        """
        try:
            # Get all collections from vector database
            if not hasattr(self.vector_store, "list_collections"):
                logger.warning("Vector store does not support listing collections - skipping cleanup")
                return {"found": 0, "deleted": 0, "errors": []}  # type: ignore[dict-item]

            vector_db_collections = self.vector_store.list_collections()
            logger.info("Found %d collections in vector database", len(vector_db_collections))

            # Get all collection vector_db_names from PostgreSQL
            pg_collections = self.collection_repository.get_all_collections()
            valid_vector_db_names = {col.vector_db_name for col in pg_collections}
            logger.info("Found %d valid collections in PostgreSQL", len(valid_vector_db_names))

            # Find orphaned collections
            orphaned_collections = []
            for vector_collection in vector_db_collections:
                if vector_collection not in valid_vector_db_names:
                    orphaned_collections.append(vector_collection)

            logger.info(
                "Identified %d orphaned collections: %s",
                len(orphaned_collections),
                orphaned_collections,
            )

            # Delete orphaned collections
            deleted_count = 0
            errors = []

            for orphaned_collection in orphaned_collections:
                try:
                    self.vector_store.delete_collection(orphaned_collection)
                    deleted_count += 1
                    logger.info("Deleted orphaned collection: %s", orphaned_collection)
                except (ValueError, KeyError, AttributeError) as e:
                    error_msg = f"Failed to delete collection {orphaned_collection}: {e!s}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            summary = {
                "found": len(orphaned_collections),
                "deleted": deleted_count,
                "errors": errors,
            }

            logger.info("Cleanup complete: %s", summary)
            return summary  # type: ignore[return-value]

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error during orphaned collection cleanup: %s", str(e))
            raise CollectionProcessingError(
                collection_id="cleanup",
                stage="orphan_cleanup",
                error_type="cleanup_error",
                message=f"Orphaned collection cleanup failed: {e!s}",
            ) from e

    async def reindex_collection(self, collection_id: UUID4, user_id: UUID4) -> None:
        """
        Reindex all documents in a collection using current chunking settings.

        This method:
        1. Deletes all existing chunks from the vector database
        2. Reprocesses all documents with current chunking configuration from .env
        3. Re-indexes all chunks into the vector database
        4. Regenerates suggested questions

        Args:
            collection_id: Collection UUID to reindex
            user_id: User UUID requesting the reindex

        Raises:
            NotFoundError: If collection not found
            CollectionProcessingError: If reindexing fails
        """
        try:
            logger.info(
                "Starting reindex for collection %s (user %s)",
                str(collection_id),
                str(user_id),
            )

            # Get collection
            collection = self.get_collection(collection_id)

            # Update status to PROCESSING
            self.update_collection_status(collection_id, CollectionStatus.PROCESSING)

            # Get all file records for this collection
            file_records = self.file_management_service.get_files_by_collection(collection_id)

            if not file_records:
                logger.warning(
                    "No files found for collection %s - nothing to reindex",
                    str(collection_id),
                )
                self.update_collection_status(collection_id, CollectionStatus.COMPLETED)
                return

            logger.info(
                "Found %d files to reindex for collection %s",
                len(file_records),
                str(collection_id),
            )

            # Delete existing data from vector database
            logger.info(
                "Deleting existing vector data for collection %s",
                collection.vector_db_name,
            )
            try:
                self.vector_store.delete_collection(collection.vector_db_name)
                # Recreate the collection with same metadata
                self.vector_store.create_collection(collection.vector_db_name, {"is_private": collection.is_private})
                logger.info("Vector collection recreated: %s", collection.vector_db_name)
            except CollectionError as e:
                logger.error("Error recreating vector collection: %s", str(e))
                self.update_collection_status(collection_id, CollectionStatus.ERROR)
                raise CollectionProcessingError(
                    collection_id=str(collection_id),
                    stage="reindex_cleanup",
                    error_type="vector_db_error",
                    message=f"Failed to recreate vector collection: {e!s}",
                ) from e

            # Build lists of file paths and document IDs
            file_paths = []
            document_ids = []

            for file_record in file_records:
                if file_record.filename:
                    # Get the current file path (based on current file_storage_path setting)
                    # Don't use file_record.file_path as it may be outdated/temporary
                    file_path = self.file_management_service.get_file_path(collection_id, file_record.filename)
                    file_paths.append(str(file_path))
                    # Use document_id if available, otherwise use file id as string
                    document_ids.append(file_record.document_id if file_record.document_id else str(file_record.id))

            logger.info(
                "Reprocessing %d documents with current chunking settings",
                len(file_paths),
            )

            # Reprocess documents using current chunking settings
            # This will use the updated MIN_CHUNK_SIZE, MAX_CHUNK_SIZE, etc. from .env
            await self.process_documents(
                file_paths,
                collection_id,
                collection.vector_db_name,
                document_ids,
                user_id,
            )

            logger.info(
                "Reindexing completed successfully for collection %s",
                str(collection_id),
            )

        except NotFoundError:
            logger.error("Collection not found for reindexing: %s", str(collection_id))
            raise
        except CollectionProcessingError:
            # Already logged and status updated
            raise
        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Unexpected error during reindexing: %s", str(e))
            self.update_collection_status(collection_id, CollectionStatus.ERROR)
            raise CollectionProcessingError(
                collection_id=str(collection_id),
                stage="reindex",
                error_type="unexpected_error",
                message=f"Reindexing failed: {e!s}",
            ) from e
