"""Service for handling search operations through the RAG pipeline."""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar
from pydantic import UUID4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.custom_exceptions import ConfigurationError, LLMProviderError, NotFoundError, ValidationError
from core.logging_utils import get_logger
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.pipeline_service import PipelineService
from vectordbs.data_types import DocumentMetadata, QueryResult

logger = get_logger("services.search")

T = TypeVar("T")
P = ParamSpec("P")


def handle_search_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle common search errors and convert them to HTTPExceptions."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except NotFoundError as e:
            logger.error(f"Resource not found: {e!s}")
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValidationError as e:
            logger.error(f"Validation error: {e!s}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except LLMProviderError as e:
            logger.error(f"LLM provider error: {e!s}")
            raise HTTPException(status_code=500, detail=str(e)) from e
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e!s}")
            raise HTTPException(status_code=500, detail=str(e)) from e
        except Exception as e:
            logger.error(f"Unexpected error during search: {e!s}")
            raise HTTPException(status_code=500, detail=f"Error processing search: {e!s}") from e

    return wrapper


class SearchService:
    """Service for handling search operations through the RAG pipeline."""

    def __init__(self, db: Session) -> None:
        """Initialize SearchService with dependencies."""
        logger.debug("Initializing SearchService")
        self.db: Session = db
        self._file_service: FileManagementService | None = None
        self._collection_service: CollectionService | None = None
        self._pipeline_service: PipelineService | None = None

    @property
    def file_service(self) -> FileManagementService:
        """Lazy initialization of file management service."""
        if self._file_service is None:
            logger.debug("Lazy initializing file management service")
            self._file_service = FileManagementService(self.db)
        return self._file_service

    @property
    def collection_service(self) -> CollectionService:
        """Lazy initialization of collection service."""
        if self._collection_service is None:
            logger.debug("Lazy initializing collection service")
            self._collection_service = CollectionService(self.db)
        return self._collection_service

    @property
    def pipeline_service(self) -> PipelineService:
        """Lazy initialization of pipeline service."""
        if self._pipeline_service is None:
            logger.debug("Lazy initializing pipeline service")
            self._pipeline_service = PipelineService(self.db)
        return self._pipeline_service

    @handle_search_errors
    async def _initialize_pipeline(self, collection_id: UUID4) -> str:
        """Initialize pipeline with collection."""
        try:
            # Get collection
            collection = self.collection_service.get_collection(collection_id)
            if not collection:
                raise NotFoundError(
                    resource_type="Collection",
                    resource_id=str(collection_id),
                    message=f"Collection with ID {collection_id} not found",
                )

            # Initialize pipeline
            await self.pipeline_service.initialize(collection.vector_db_name)
            return collection.vector_db_name

        except (NotFoundError, ConfigurationError):
            raise
        except Exception as e:
            logger.error(f"Error initializing pipeline: {e!s}")
            raise ConfigurationError(f"Pipeline initialization failed: {e!s}") from e

    def _generate_document_metadata(
        self, query_results: list[QueryResult], collection_id: UUID4
    ) -> list[DocumentMetadata]:
        """Generate metadata from retrieved query results."""
        logger.debug("Generating document metadata")

        # Get unique document IDs from results
        doc_ids = {result.document_id for result in query_results if result.document_id is not None}

        if not doc_ids:
            return []

        # Get file metadata
        files = self.file_service.get_files_by_collection(collection_id)
        if not files:
            # Only return empty list if there are no query results requiring metadata
            if not doc_ids:
                return []
            raise ConfigurationError(f"No files found for collection {collection_id} but documents were referenced")

        file_metadata_by_id: dict[str, DocumentMetadata] = {
            file.document_id: DocumentMetadata(
                document_name=file.filename,
                total_pages=file.metadata.total_pages if file.metadata else None,
                total_chunks=file.metadata.total_chunks if file.metadata else None,
                keywords=file.metadata.keywords if file.metadata else None,
            )
            for file in files
            if file.document_id
        }

        # Map metadata to results
        doc_metadata = []
        missing_docs = []
        for doc_id in doc_ids:
            if doc_id not in file_metadata_by_id:
                missing_docs.append(doc_id)

        if missing_docs:
            raise ConfigurationError(
                f"Metadata generation failed: Documents not found in collection metadata: {', '.join(missing_docs)}"
            )

        for doc_id in doc_ids:
            doc_metadata.append(file_metadata_by_id[doc_id])

        logger.debug(f"Generated metadata for {len(doc_metadata)} documents")
        return doc_metadata

    def _clean_generated_answer(self, answer: str) -> str:
        # Remove AND prefixes and deduplicate
        cleaned = " ".join([part.replace("AND", "").strip() for part in answer.split() if part.strip()])
        # Remove duplicate words
        cleaned = " ".join(dict.fromkeys(cleaned.split()))
        return cleaned

    def _validate_search_input(self, search_input: SearchInput) -> None:
        """Validate search input parameters."""
        if not search_input.question or not search_input.question.strip():
            raise ValidationError("Query cannot be empty")

    def _validate_collection_access(self, collection_id: UUID4, user_id: UUID4 | None) -> None:
        """Validate collection access."""
        try:
            collection = self.collection_service.get_collection(collection_id)
            if not collection:
                raise NotFoundError(
                    resource_type="Collection",
                    resource_id=str(collection_id),
                    message=f"Collection with ID {collection_id} not found",
                )

            if user_id and collection.is_private:
                user_collections = self.collection_service.get_user_collections(user_id)
                if collection.id not in [c.id for c in user_collections]:
                    raise NotFoundError(
                        resource_type="Collection",
                        resource_id=str(collection_id),
                        message="Collection not found or access denied",
                    )
        except HTTPException as e:
            # Convert HTTPException to NotFoundError to ensure consistent error handling
            if e.status_code == 404:
                raise NotFoundError(
                    resource_type="Collection", resource_id=str(collection_id), message=str(e.detail)
                ) from e
            raise

    def _validate_pipeline(self, pipeline_id: UUID4) -> None:
        """Validate pipeline configuration."""
        pipeline_config = self.pipeline_service.get_pipeline_config(pipeline_id)
        if not pipeline_config:
            raise NotFoundError(
                resource_type="Pipeline", resource_id=str(pipeline_id), message="Pipeline configuration not found"
            )

    @handle_search_errors
    async def search(self, search_input: SearchInput) -> SearchOutput:
        """Process a search query through the RAG pipeline."""
        time.time()
        logger.info("Starting search operation")

        # Validate inputs
        self._validate_search_input(search_input)
        self._validate_collection_access(search_input.collection_id, search_input.user_id)
        self._validate_pipeline(search_input.pipeline_id)

        # Initialize pipeline
        collection_name = await self._initialize_pipeline(search_input.collection_id)

        # Execute pipeline
        pipeline_result = await self.pipeline_service.execute_pipeline(
            search_input=search_input, collection_name=collection_name
        )

        if not pipeline_result.success:
            raise ConfigurationError(pipeline_result.error or "Pipeline execution failed")

        # Generate metadata
        if pipeline_result.query_results is None:
            pipeline_result.query_results = []
        document_metadata = self._generate_document_metadata(pipeline_result.query_results, search_input.collection_id)

        # Clean answer
        if pipeline_result.generated_answer is None:
            pipeline_result.generated_answer = ""
        cleaned_answer = self._clean_generated_answer(pipeline_result.generated_answer)

        # Build response
        return SearchOutput(
            answer=cleaned_answer,
            documents=document_metadata,
            query_results=pipeline_result.query_results,
            rewritten_query=pipeline_result.rewritten_query,
            evaluation=pipeline_result.evaluation,
        )
