"""Service layer for search functionality."""

from typing import Dict, Any, Optional, List
from uuid import UUID
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
import logging
import re

from core.config import settings
from rag_solution.pipeline.pipeline import Pipeline, PipelineResult
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from vectordbs.data_types import QueryResult, DocumentMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchService:
    """Service for handling search operations through the RAG pipeline."""
    
    def __init__(self, db: Session):
        """Initialize search service.
        
        Args:
            db: Database session
        """
        self.pipeline = self._create_pipeline(db)
        self.collection_service: CollectionService = CollectionService(db)
        self.file_service: FileManagementService = FileManagementService(db)

    def _create_pipeline(self, db: Session) -> Pipeline:
        """Create and configure the RAG pipeline using settings.
        
        Args:
            db: Database session
            
        Returns:
            Pipeline: Configured pipeline instance
        """
        config = {
            'query_rewriting': {
                'use_simple_rewriter': True,
                'use_hyponym_rewriter': False
            },
            'retrieval': {
                'type': 'vector',
                'vector_weight': 0.7
            },
            'generation': {
                'type': 'watsonx',
                'model_name': settings.rag_llm,
                'default_params': {
                    'max_new_tokens': settings.max_new_tokens,
                    'min_new_tokens': settings.min_new_tokens,
                    'temperature': settings.temperature,
                    'random_seed': settings.random_seed,
                    'top_k': settings.top_k
                }
            },
            'vector_store': {
                'type': settings.vector_db,
                'connection_args': {
                    'host': settings.milvus_host,
                    'port': settings.milvus_port,
                    'user': settings.milvus_user,
                    'password': settings.milvus_password,
                    'index_params': settings.milvus_index_params,
                    'search_params': settings.milvus_search_params
                }
            },
            'number_of_results': settings.number_of_results,
            'chunking': {
                'strategy': settings.chunking_strategy,
                'min_chunk_size': settings.min_chunk_size,
                'max_chunk_size': settings.max_chunk_size,
                'chunk_overlap': settings.chunk_overlap,
                'semantic_threshold': settings.semantic_threshold
            },
            'embedding': {
                'model': settings.embedding_model,
                'dimension': settings.embedding_dim,
                'field': settings.embedding_field,
                'batch_size': settings.upsert_batch_size
            }
        }
        return Pipeline(config, db)

    def _get_collection_vector_db_name(self, collection_id: UUID) -> str:
        """Get the vector database collection name for a given collection ID.
        
        Args:
            collection_id: The UUID of the collection
            
        Returns:
            str: The vector database collection name
            
        Raises:
            HTTPException: If collection is not found or user doesn't have access
        """
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
        # Remove boolean operators and parentheses
        clean_query = re.sub(r'\s+(AND|OR)\s+', ' ', query)
        clean_query = re.sub(r'[\(\)]', '', clean_query)
        return clean_query.strip()
    
    def _clean_generated_answer(self, answer: str) -> str:
        """Clean up the generated answer.
        
        Args:
            answer: Raw generated answer
            
        Returns:
            str: Cleaned answer text
        """
        if not answer:
            return ""
        
        # Remove boolean operation prefixes
        answer = re.sub(r'^AND\s+\([^)]+\)(\s+AND\s+\([^)]+\))*\s*', '', answer)
        
        # Remove duplicate lines
        lines = answer.split('\n')
        unique_lines = []
        seen = set()
        for line in lines:
            clean_line = line.strip()
            if clean_line and clean_line not in seen:
                seen.add(clean_line)
                unique_lines.append(clean_line)
        
        # Join unique lines back together
        cleaned = '\n'.join(unique_lines)
        
        # Clean up any remaining artifacts
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()

    def _generate_document_metadata(self, query_results: List[QueryResult],
        collection_id: UUID
        ) -> List[DocumentMetadata]:
        """
        Generate document metadata from query results and database records.

        Args:
            query_results (List[QueryResult]): The list of QueryResult objects from the search.
            collection_id (UUID): The UUID of the collection to fetch the file metadata from.

        Returns:
            List[DocumentMetadata]: The list of DocumentMetadata objects for the relevant documents.

        Raises:
            Exception: If an error occurs while generating the document metadata.
        """
        try:
            # Get all unique document IDs from query results
            doc_ids = {
                result.document_id
                for result in query_results
                if result.document_id is not None
            }
            logger.info(f"Found {doc_ids} unique document IDs from query results")

            # Fetch file metadata from database for the relevant documents
            files = self.file_service.get_files_by_collection(collection_id)
            logger.info(f"received files: {files}")

            file_metadata_by_id = {}
            for file in files:
                filename = file.filename
                logger.info(f"Processing file: {file}")
                if file.document_id:  
                    file_metadata_by_id[file.document_id] = DocumentMetadata(
                                        document_name=filename,
                                        total_pages=file.metadata.total_pages if file.metadata else None,
                                        total_chunks=file.metadata.total_chunks if file.metadata else None,
                                        keywords=file.metadata.keywords if file.metadata else None
                    )
            logger.info(f"Created {len(file_metadata_by_id)} document metadata objects")

            # Return the relevant DocumentMetadata objects
            doc_metadata = [
                file_metadata_by_id[doc_id]
                for doc_id in doc_ids
                if doc_id in file_metadata_by_id
            ]
            logger.info(f"Returning {len(doc_metadata)} DocumentMetadata objects")
            return doc_metadata

        except Exception as e:
            logger.error(f"Error generating document metadata: {e}")
            raise
    
    async def search(self, search_input: SearchInput, context: Optional[Dict[str, Any]] = None) -> SearchOutput:
        """Process a search query through the RAG pipeline.

        Args:
            search_input: The input containing the query and collection details
            context: Additional context for search customization

        Returns:
            SearchOutput: The result of the search operation

        Raises:
            HTTPException: 
                - 404: If collection not found
                - 400: If invalid input or collection access error
                - 500: If processing error occurs
        """
        try:
            # Get collection name with typed return
            collection_name: str = self._get_collection_vector_db_name(search_input.collection_id)

            # Clean the query before sending to pipeline
            clean_query = self._prepare_query(search_input.question)
            
            # Process through pipeline with strong typing
            pipeline_result: PipelineResult = await self.pipeline.process(
                query=clean_query,
                collection_name=collection_name,
                context=context
            )

            # Generate metadata
            document_metadata: List[DocumentMetadata] = self._generate_document_metadata(
                pipeline_result.query_results,
                search_input.collection_id
            )
            
            # Clean generated answer
            cleaned_answer = self._clean_generated_answer(pipeline_result.generated_answer)

            # Create SearchOutput directly from PipelineResult
            search_output = SearchOutput(
                answer=cleaned_answer,
                documents=document_metadata,
                query_results=pipeline_result.query_results,
                rewritten_query=pipeline_result.rewritten_query,
                evaluation=pipeline_result.evaluation
            )

            if not pipeline_result.query_results:
                logger.warning(f"No results found for query: {search_input.question}")
                
            return search_output

        except HTTPException as he:
            # Re-raise existing HTTP exceptions
            raise he
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid input: {str(ve)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing search: {str(e)}")
