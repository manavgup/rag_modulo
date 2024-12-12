from typing import Dict, Any, Optional, List
from uuid import UUID
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
import logging
import re

from core.config import settings
from rag_solution.pipeline.pipeline import Pipeline, PipelineResult
from rag_solution.schemas.search_schema import SearchInput, SearchOutput, DocumentMetadata, SourceDocument
from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.services.collection_service import CollectionService
from vectordbs.data_types import QueryResult, DocumentChunkWithScore, Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, db: Session):
        self.pipeline = self._create_pipeline(db)
        self.collection_service = CollectionService(db)

    def _create_pipeline(self, db:Session) -> Pipeline:
        """
        Create and configure the RAG pipeline using settings.
        
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
            'top_k': settings.top_k,
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
        """
        Get the vector database collection name for a given collection ID.
        
        Args:
            collection_id (UUID): The UUID of the collection
            
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
    
    def _transform_retrieved_documents(self, retrieved_documents: List[QueryResult]) -> List[SourceDocument]:
        """Transform retrieved documents from pipeline format to API response format."""
        source_documents = []

        if not retrieved_documents:
            logger.warning("No retrieved documents to process")
            return source_documents

        try:
            # Process each QueryResult
            for query_result in retrieved_documents:
                if query_result.data:
                    for chunk in query_result.data:
                        metadata = DocumentMetadata(
                            source=chunk.metadata.source.value if chunk.metadata else 'unknown',
                            source_id=chunk.metadata.source_id if chunk.metadata else None,
                            url=chunk.metadata.url if chunk.metadata else None,
                            created_at=chunk.metadata.created_at if chunk.metadata else None,
                            author=chunk.metadata.author if chunk.metadata else None,
                            page_number=chunk.metadata.page_number if chunk.metadata else None
                        )
                        
                        source_documents.append(SourceDocument(
                            text=chunk.text,
                            metadata=metadata,
                            score=chunk.score,
                            document_id=chunk.document_id
                        ))

            return source_documents

        except Exception as e:
            logger.error(f"Error processing retrieved documents: {str(e)}")
            return source_documents
    
    def _create_metadata(self, chunk: Any) -> Optional[DocumentMetadata]:
        """Create metadata object from chunk data."""
        try:
            if not chunk.metadata:
                return None
                
            return DocumentMetadata(
                source=chunk.metadata.source.value if hasattr(chunk.metadata, 'source') else 'unknown',
                source_id=getattr(chunk.metadata, 'source_id', None),
                url=getattr(chunk.metadata, 'url', None),
                created_at=getattr(chunk.metadata, 'created_at', None),
                author=getattr(chunk.metadata, 'author', None),
                title=getattr(chunk.metadata, 'title', None),
                page_number=getattr(chunk.metadata, 'page_number', None),
                total_pages=getattr(chunk.metadata, 'total_pages', None)
            )
        except Exception as e:
            logger.error(f"Error creating metadata: {str(e)}")
            return None
    
    def _prepare_query(self, query: str) -> str:
        """Prepare query by removing any existing boolean operators."""
        # Remove boolean operators and parentheses
        clean_query = re.sub(r'\s+(AND|OR)\s+', ' ', query)
        clean_query = re.sub(r'[\(\)]', '', clean_query)
        return clean_query.strip()
    
    def _clean_generated_answer(self, answer: str) -> str:
        """Clean up the generated answer."""
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
    
    async def search(self, search_input: SearchInput, context: Optional[Dict[str, Any]] = None) -> SearchOutput:
        """
        Process a search query through the RAG pipeline.

        Args:
            search_input (SearchInput): The input containing the query and collection details.
                question (str): The query text
                collection_id (UUID): The collection identifier
            context (Optional[Dict[str, Any]]): Additional context for search customization.

        Returns:
            SearchOutput: The result of the search operation containing:
                - answer (str): Generated response
                - source_documents (List[Dict[str, Any]]): Retrieved source documents
                - rewritten_query (Optional[str]): Query after rewriting
                - evaluation (Optional[Dict[str, Any]]): Evaluation metrics

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
            # Clean generated answer
            cleaned_answer = self._clean_generated_answer(pipeline_result.generated_answer)

            # Transform pipeline results to source documents
            source_documents:List[SourceDocument]  = self._transform_retrieved_documents(pipeline_result.retrieved_documents)

            if not source_documents:
                logger.warning(f"No source documents found for query: {search_input.question}")

            # Create the final SearchOutput
            search_output = SearchOutput(
                answer=cleaned_answer,
                source_documents=source_documents,
                rewritten_query=clean_query,
                evaluation=pipeline_result.evaluation
            )

            # Validate we have some results
            if not source_documents:
                logger.warning(f"No source documents found for query: {search_input.question}")
                
            return search_output

        except HTTPException as he:
            # Re-raise existing HTTP exceptions
            raise he
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid input: {str(ve)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing search: {str(e)}")
