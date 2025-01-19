"""Service for handling search operations through the RAG pipeline."""

from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, Dict, Any, List
import time
import re

from fastapi import HTTPException
from core.config import settings
from core.custom_exceptions import (
    ConfigurationError,
    ValidationError,
    NotFoundError
)
from core.logging_utils import get_logger

from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.pipeline_service import PipelineService
from vectordbs.data_types import QueryResult, DocumentMetadata

logger = get_logger("services.search")


class SearchService:
    """Service for handling search operations through the RAG pipeline."""
    
    def __init__(self, db: Session) -> None:
        """Initialize SearchService with dependencies."""
        logger.debug("Initializing SearchService")
        self.db: Session = db
        self._file_service: Optional[FileManagementService] = None
        self._collection_service: Optional[CollectionService] = None
        self._pipeline_service: Optional[PipelineService] = None

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

    async def _initialize_pipeline(self, collection_id: UUID) -> str:
        """Initialize pipeline for collection and return vector DB name."""
        try:
            # Get collection
            collection = self.collection_service.get_collection(collection_id)

            # Initialize pipeline
            await self.pipeline_service.initialize(collection.vector_db_name)
            return collection.vector_db_name

        except NotFoundError as e:
            logger.error(f"Collection not found: {e}")
            raise HTTPException(status_code=404, detail=str(e))
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"Error initializing pipeline: {e}")
            raise HTTPException(status_code=500, detail=f"Pipeline initialization failed: {str(e)}")

    def _generate_document_metadata(
        self,
        query_results: List[QueryResult],
        collection_id: UUID
    ) -> List[DocumentMetadata]:
        """Generate metadata from retrieved query results."""
        logger.debug("Generating document metadata")
        try:
            # Get unique document IDs from results
            doc_ids = {
                result.document_id
                for result in query_results
                if result.document_id is not None
            }

            # Get file metadata
            files = self.file_service.get_files_by_collection(collection_id)
            file_metadata_by_id: Dict[str, DocumentMetadata] = {
                file.document_id: DocumentMetadata(
                    document_name=file.filename,
                    total_pages=file.metadata.total_pages if file.metadata else None,
                    total_chunks=file.metadata.total_chunks if file.metadata else None,
                    keywords=file.metadata.keywords if file.metadata else None
                )
                for file in files if file.document_id
            }

            # Map metadata to results
            doc_metadata = [
                file_metadata_by_id[doc_id]
                for doc_id in doc_ids if doc_id in file_metadata_by_id
            ]
            logger.debug(f"Generated metadata for {len(doc_metadata)} documents")
            return doc_metadata

        except Exception as e:
            logger.error(f"Error generating document metadata: {e}")
            raise ConfigurationError(f"Metadata generation failed: {str(e)}")

    def _clean_generated_answer(self, answer: str) -> str:
        # Remove AND prefixes and deduplicate
        cleaned = " ".join([part.replace("AND", "").strip() for part in answer.split() if part.strip()])
        # Remove duplicate words
        cleaned = " ".join(dict.fromkeys(cleaned.split()))
        return cleaned

    async def search(
        self,
        search_input: SearchInput,
        user_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> SearchOutput:
        """
        Process a search query through the RAG pipeline.
        
        Args:
            search_input: Search parameters and query
            user_id: Optional user ID for tracking
            context: Optional context information
            
        Returns:
            SearchOutput containing answer and supporting information
            
        Raises:
            HTTPException: For various error conditions
        """
        start_time = time.time()
        logger.info("Starting search operation")

        # Validate query
        if not search_input.question or not search_input.question.strip():
            raise HTTPException(
                status_code=400,
                detail="Query cannot be empty"
            )

        try:
            # Initialize pipeline for collection
            collection_name = await self._initialize_pipeline(search_input.collection_id)

            # Execute pipeline
            pipeline_result = await self.pipeline_service.execute_pipeline(
                search_input=search_input,
                user_id=user_id,
                collection_name=collection_name
            )
            
            if not pipeline_result.success:
                raise ConfigurationError(pipeline_result.error or "Pipeline execution failed")

            # Generate metadata
            document_metadata = self._generate_document_metadata(
                pipeline_result.query_results,
                search_input.collection_id
            )

            # Clean answer
            cleaned_answer = self._clean_generated_answer(
                pipeline_result.generated_answer
            )

            # Build response
            search_output = SearchOutput(
                answer=cleaned_answer,
                documents=document_metadata,
                query_results=pipeline_result.query_results,
                rewritten_query=pipeline_result.rewritten_query,
                evaluation=pipeline_result.evaluation,
                metadata={
                    "execution_time": time.time() - start_time,
                    "num_chunks": len(pipeline_result.query_results),
                    "unique_docs": len(pipeline_result.get_unique_document_ids())
                }
            )

            logger.info(f"Search completed in {time.time() - start_time:.2f}s")
            return search_output

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise HTTPException(status_code=422, detail=str(e))
        except NotFoundError as e:
            logger.error(f"Not found error: {str(e)}")
            raise HTTPException(status_code=404, detail=str(e))
        except ConfigurationError as e:
            logger.error(f"Configuration error: {str(e)}")
            if "Collection not found" in str(e):
                raise HTTPException(status_code=404, detail=str(e))
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing search: {str(e)}"
            )
