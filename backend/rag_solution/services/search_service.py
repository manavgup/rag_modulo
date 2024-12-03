from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
import asyncio
from core.config import settings
from rag_solution.pipeline.pipeline import Pipeline, PipelineResult
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.services.collection_service import CollectionService

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
            
            # Process through pipeline with strong typing
            pipeline_result: PipelineResult = await self.pipeline.process(
                query=search_input.question,
                collection_name=collection_name,
                context=context
            )

            # Transform pipeline result to search output
            return SearchOutput(
                answer=pipeline_result.generated_answer,
                source_documents=[
                    {
                        'text': doc,
                        'metadata': None  # Add metadata if available in your implementation
                    }
                    for doc in pipeline_result.retrieved_documents
                ],
                rewritten_query=pipeline_result.rewritten_query,
                evaluation=pipeline_result.evaluation
            )

        except HTTPException as he:
            # Re-raise existing HTTP exceptions
            raise he
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid input: {str(ve)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing search: {str(e)}")
