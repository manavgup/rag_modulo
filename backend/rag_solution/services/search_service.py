"""Service layer for search functionality."""

from typing import Dict, Any, Optional, List
from uuid import UUID
import time
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
import re

from core.config import settings
from core.custom_exceptions import ConfigurationError
from rag_solution.pipeline.pipeline import Pipeline, PipelineResult
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.runtime_config_service import RuntimeConfigService, RuntimeServiceConfig
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.generation.providers.base import LLMProvider
from vectordbs.data_types import QueryResult, DocumentMetadata, DocumentChunk
from core.logging_utils import get_logger

logger = get_logger("services.search")

class SearchService:
    """Service for handling search operations through the RAG pipeline."""
    
    def __init__(self, db: Session) -> None:
        """Initialize search service with lazy loading of dependencies.
        
        Args:
            db: Database session
        """
        logger.debug("Initializing SearchService - no dependencies created yet")
        self.db: Session = db
        self._file_service: Optional[FileManagementService] = None
        self._runtime_config_service: Optional[RuntimeConfigService] = None
        self._collection_service: Optional[CollectionService] = None
        self._llm_factory: Optional[LLMProviderFactory] = None
        self.pipeline: Optional[Pipeline] = None

    @property
    def file_service(self) -> FileManagementService:
        """Lazy initialization of file management service."""
        if self._file_service is None:
            logger.debug("Lazy initializing file management service")
            self._file_service = FileManagementService(self.db)
        return self._file_service

    @property
    def runtime_config_service(self) -> RuntimeConfigService:
        """Lazy initialization of runtime config service."""
        if self._runtime_config_service is None:
            logger.debug("Lazy initializing runtime config service")
            self._runtime_config_service = RuntimeConfigService(self.db)
        return self._runtime_config_service

    @property
    def collection_service(self) -> CollectionService:
        """Lazy initialization of collection service."""
        if self._collection_service is None:
            logger.debug("Lazy initializing collection service")
            self._collection_service = CollectionService(self.db)
        return self._collection_service

    @property
    def llm_factory(self) -> LLMProviderFactory:
        """Lazy initialization of LLM factory."""
        if self._llm_factory is None:
            logger.debug("Lazy initializing LLM factory")
            self._llm_factory = LLMProviderFactory(self.db)
        return self._llm_factory

    def _initialize_pipeline(self, user_id: Optional[UUID] = None) -> Pipeline:
        """Initialize the RAG pipeline with runtime configurations.
        
        Args:
            user_id: Optional user ID for user-specific configurations
            
        Returns:
            Pipeline: Initialized RAG pipeline
            
        Raises:
            HTTPException: If initialization fails
        """
        logger.debug("Starting pipeline initialization")
        try:
            # Get runtime configuration
            config: RuntimeServiceConfig = self.runtime_config_service.get_runtime_config(user_id)
            if not config:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve runtime configuration."
                )

            # Get provider instance using factory
            provider: LLMProvider = self.llm_factory.get_provider(
                provider_name=config.provider_config.provider_name,
                model_id=config.provider_config.model_id
            )

            return Pipeline(
                db=self.db,
                provider=provider,
                model_parameters=config.llm_parameters,
                prompt_template=config.prompt_template,
                collection_name="default_collection"
            )

        except ConfigurationError as e:
            logger.error(f"Pipeline initialization failed: {e}")
            raise HTTPException(status_code=500, detail=f"Pipeline initialization failed: {e}")
        except ValueError as ve:
            logger.error(f"Invalid runtime configuration: {ve}")
            raise HTTPException(status_code=400, detail=str(ve))

    def _get_collection_vector_db_name(self, collection_id: UUID) -> str:
        """Get the vector database collection name for a given collection ID.
        
        Args:
            collection_id: UUID of the collection
            
        Returns:
            str: Vector database collection name
            
        Raises:
            HTTPException: If collection not found or access error
        """
        logger.debug(f"Getting collection name for ID {collection_id}")
        try:
            collection: CollectionOutput = self.collection_service.get_collection(collection_id)
            if not collection:
                raise HTTPException(
                    status_code=404,
                    detail=f"Collection {collection_id} not found"
                )
            return collection.vector_db_name
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error accessing collection: {str(e)}"
            )
    
    def _prepare_query(self, query: str) -> str:
        """Prepare query by removing any existing boolean operators.
        
        Args:
            query: Raw query string
            
        Returns:
            str: Cleaned query string
        """
        clean_query = re.sub(r'\s+(AND|OR)\s+', ' ', query)
        clean_query = re.sub(r'[\(\)]', '', clean_query)
        return clean_query.strip()
    
    def _clean_generated_answer(self, answer: str) -> str:
        """Clean up the generated answer.
        
        This method handles various answer formats including:
        - Answers with AND prefixes: "AND (info1)" -> "info1"
        - Answers with parentheses: "(info1 AND info2)" -> "(info1 info2)"
        - Multi-line answers: "AND (info1)\nAND (info2)" -> "info1 info2"
        
        Args:
            answer: Raw generated answer
            
        Returns:
            str: Cleaned answer text
        """
        if not answer:
            return ""
        
        # Handle AND prefixes and parentheses content
        def clean_part(text: str) -> str:
            # Remove AND prefix if present
            text = re.sub(r'^AND\s+', '', text)
            # If content is in parentheses, preserve the structure
            if text.startswith('(') and text.endswith(')'):
                inner = text[1:-1].strip()
                inner = re.sub(r'\s+AND\s+', ' ', inner)
                return f"({inner})"
            # If content is in parentheses with AND prefix, extract content
            match = re.match(r'\(([^)]+)\)', text.strip())
            if match:
                return match.group(1)
            return text

        # Split into lines and clean each part
        lines = answer.split('\n')
        cleaned_lines: List[str] = []
        seen: set[str] = set()
        
        for line in lines:
            clean_line = clean_part(line.strip())
            if clean_line and clean_line not in seen:
                seen.add(clean_line)
                cleaned_lines.append(clean_line)
        
        # Join lines and normalize spaces
        result = ' '.join(cleaned_lines)
        result = re.sub(r'\s+', ' ', result)
        
        return result.strip()

    def _generate_document_metadata(
        self,
        query_results: List[QueryResult],
        collection_id: UUID
    ) -> List[DocumentMetadata]:
        """Generate document metadata from query results and database records.
        
        Args:
            query_results: List of query results from vector search
            collection_id: UUID of the collection
            
        Returns:
            List[DocumentMetadata]: List of document metadata
            
        Raises:
            HTTPException: If metadata generation fails
        """
        logger.debug("Starting document metadata generation")
        try:
            doc_ids: set[str] = {
                result.document_id
                for result in query_results
                if result.document_id is not None
            }
            logger.debug(f"Found {len(doc_ids)} unique document IDs")

            files = self.file_service.get_files_by_collection(collection_id)
            logger.debug(f"Retrieved {len(files)} files from collection")

            file_metadata_by_id: Dict[str, DocumentMetadata] = {}
            for file in files:
                if file.document_id:  
                    file_metadata_by_id[file.document_id] = DocumentMetadata(
                        document_name=file.filename,
                        total_pages=file.metadata.total_pages if file.metadata else None,
                        total_chunks=file.metadata.total_chunks if file.metadata else None,
                        keywords=file.metadata.keywords if file.metadata else None
                    )

            doc_metadata = [
                file_metadata_by_id[doc_id]
                for doc_id in doc_ids
                if doc_id in file_metadata_by_id
            ]
            logger.debug(f"Generated metadata for {len(doc_metadata)} documents")
            return doc_metadata

        except Exception as e:
            logger.error(f"Error generating document metadata: {e}")
            raise
    
    async def search(
        self,
        search_input: SearchInput,
        user_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> SearchOutput:
        """Process a search query through the RAG pipeline.
        
        Args:
            search_input: Search input parameters
            user_id: Optional user ID for personalization
            context: Optional context for search
            
        Returns:
            SearchOutput: Search results including answer and documents
            
        Raises:
            HTTPException: If search processing fails
        """
        start_time = time.time()
        logger.debug("Starting search operation - services will be initialized as needed")
        
        try:
            collection_name: str = self._get_collection_vector_db_name(search_input.collection_id)
            clean_query: str = self._prepare_query(search_input.question)
            
            self.pipeline = self._initialize_pipeline(user_id)
            
            pipeline_result: PipelineResult = await self.pipeline.process(
                query=clean_query,
                collection_name=collection_name,
                context=context
            )

            document_metadata: List[DocumentMetadata] = self._generate_document_metadata(
                pipeline_result.query_results,
                search_input.collection_id
            )
            
            cleaned_answer: str = self._clean_generated_answer(pipeline_result.generated_answer)

            search_output = SearchOutput(
                answer=cleaned_answer,
                documents=document_metadata,
                query_results=pipeline_result.query_results,
                rewritten_query=pipeline_result.rewritten_query,
                evaluation=pipeline_result.evaluation
            )

            if not pipeline_result.query_results:
                logger.warning(f"No results found for query: {search_input.question}")
            
            logger.debug(f"Search operation completed in {time.time() - start_time:.2f}s")
            return search_output

        except HTTPException as he:
            logger.error(f"HTTP exception in search: {he.detail}")
            raise he
        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            raise HTTPException(status_code=400, detail=f"Invalid input: {str(ve)}")
        except Exception as e:
            logger.error(f"Unexpected error in search: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing search: {str(e)}")
