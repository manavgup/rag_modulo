from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from core.config import settings
from rag_solution.pipeline.pipeline import Pipeline
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.services.collection_service import CollectionService

class SearchService:
    def __init__(self, db: Session):
        self.pipeline = self._create_pipeline()
        self.collection_service = CollectionService(db)

    def _create_pipeline(self) -> Pipeline:
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
        return Pipeline(config)

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

    def search(self, search_input: SearchInput, context: Optional[Dict[str, Any]] = None) -> SearchOutput:
        """
        Process a search query through the RAG pipeline.

        Args:
            search_input (SearchInput): Input data containing question and collection.
            context (Optional[Dict[str, Any]]): Additional context for query processing.

        Returns:
            SearchOutput: Contains the answer and related information.

        Raises:
            HTTPException: If collection lookup fails or search processing fails
        """
        try:
            # Get the actual vector db collection name from the collection ID
            vector_db_collection = self._get_collection_vector_db_name(search_input.collection_id)
            
            # Process the search through the pipeline
            result = self.pipeline.process(
                query=search_input.question,
                collection_name=vector_db_collection,
                context=context
            )
            
            # Convert pipeline result to match SearchOutput schema
            source_documents = []
            for doc in result.retrieved_documents:
                if isinstance(doc, str):
                    # If it's just text, create a basic document
                    source_documents.append({
                        'text': doc,
                        'metadata': None,
                        'score': None,
                        'document_id': None
                    })
                else:
                    # If it's a structured document, preserve its structure
                    source_documents.append(doc)
            
            return SearchOutput(
                answer=result.generated_answer,
                source_documents=source_documents,
                rewritten_query=result.rewritten_query,
                evaluation=result.evaluation
            )
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing search: {str(e)}"
            )

    def search_stream(self, search_input: SearchInput, context: Optional[Dict[str, Any]] = None):
        """
        Process a search query through the RAG pipeline with streaming response.

        Args:
            search_input (SearchInput): Input data containing question and collection.
            context (Optional[Dict[str, Any]]): Additional context for query processing.

        Returns:
            Iterator: Streams the generated answer and related information.

        Raises:
            HTTPException: If collection lookup fails or search processing fails
        """
        try:
            # Get the actual vector db collection name from the collection ID
            vector_db_collection = self._get_collection_vector_db_name(search_input.collection_id)
            
            # Return streaming response
            return self.pipeline.process_stream(
                query=search_input.question,
                collection_name=vector_db_collection,
                context=context
            )
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing streaming search: {str(e)}"
            )