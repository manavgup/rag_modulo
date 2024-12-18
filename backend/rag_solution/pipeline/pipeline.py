"""Pipeline implementation for RAG processing."""

import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from uuid import UUID
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from rag_solution.query_rewriting.query_rewriter import QueryRewriter
from rag_solution.retrieval.factories import RetrieverFactory
from rag_solution.generation.factories import GeneratorFactory, EvaluatorFactory
from vectordbs.factory import get_datastore
from rag_solution.data_ingestion.ingestion import DocumentStore
from vectordbs.data_types import QueryResult, DocumentChunk, DocumentMetadata, VectorQuery
from core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PipelineResult(BaseModel):
    """Result from pipeline processing.
    
    Attributes:
        rewritten_query: Query after rewriting
        document_metadata: Unique document metadata for display
        query_results: List of vector similarity matches
        generated_answer: Generated answer text
        evaluation: Optional evaluation results
    """
    rewritten_query: str
    query_results: List[QueryResult]
    generated_answer: str
    evaluation: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

    def get_sorted_results(self) -> List[QueryResult]:
        """Get results sorted by similarity score."""
        return sorted(self.query_results, key=lambda x: x.score, reverse=True)

    def get_top_k_results(self, k: int) -> List[QueryResult]:
        """Get top k results by similarity score."""
        return self.get_sorted_results()[:k]

    def get_all_texts(self) -> List[str]:
        """Get all chunk texts from results."""
        return [result.chunk.text for result in self.query_results]

    def get_unique_document_ids(self) -> set[str]:
        """Get set of unique document IDs from results."""
        return {
            result.document_id  # Using the convenience property
            for result in self.query_results 
            if result.document_id is not None
        }

    def get_results_for_document(self, document_id: str) -> List[QueryResult]:
        """Get all results from a specific document."""
        return [
            result for result in self.query_results 
            if result.document_id == document_id
        ]

class Pipeline():
    """Main RAG pipeline implementation.
    
    This class orchestrates the entire RAG process:
    1. Query rewriting
    2. Document retrieval
    3. Answer generation
    4. Optional evaluation
    """
    
    def __init__(self, config: Dict[str, Any], db: Session):
        """Initialize the RAG Pipeline.
        
        Args:
            config: Configuration dictionary containing settings for all components
            db: SQLAlchemy database session
        """
        self.config = config
        self.db = db
        self.query_rewriter = QueryRewriter(config.get('query_rewriting', {}))
        
        vector_store_config = config.get('vector_store', {'type': 'milvus'})
        self.vector_store = get_datastore(vector_store_config['type'])
        
        self.collection_name = config.get('collection_name', 'default_collection')
        self.document_store = DocumentStore(self.vector_store, self.collection_name)
        
        self.retriever = RetrieverFactory.create_retriever(config.get('retrieval', {}), self.document_store)
        self.generator = GeneratorFactory.create_generator(config.get('generation', {}))
        self.evaluator = EvaluatorFactory.create_evaluator(config.get('evaluation', {}))

    async def initialize(self) -> None:
        """Initialize the pipeline and load documents."""
        await self._load_documents()

    async def _load_documents(self) -> None:
        """Load and process documents from configured data sources."""
        data_source = self.config.get('data_source', [])
        try:
            await self.document_store.load_documents(data_source)
            logger.info(f"Loaded documents into collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
            raise

    def get_collection_chunks(self, collection_name: str) -> List[DocumentChunk]:
        """Get document chunks from a collection.
        
        Args:
            collection_name: Name of the collection to retrieve chunks from
            
        Returns:
            List[DocumentChunk]: List of document chunks
        """
        try:
            # Create an empty query to get representative documents
            query = VectorQuery(
                text="",  # Empty query to get representative documents
                number_of_results=settings.number_of_results
            )
            
            retrieved_docs = self.retriever.retrieve(
                collection_name=collection_name,
                query=query
            )
            
            # Extract chunks from retrieved documents
            chunks = []
            for result in retrieved_docs:
                chunks.extend(result.chunk)
            return chunks
            
        except Exception as e:
            logger.error(f"Error getting collection chunks: {e}")
            return []

    async def process(self, query: str, collection_name: str, context: Optional[Dict[str, Any]] = None) -> PipelineResult:
        """Process a query through the RAG pipeline.
        
        Args:
            query: The user's query string
            collection_name: Name of the collection to search in
            context: Optional context information for query processing
            
        Returns:
            PipelineResult: Contains the generated answer and supporting information
        """
        try:
            if not query.strip():
                raise ValueError("Query cannot be empty")

            # 1: Query Rewriting
            rewritten_query = self.query_rewriter.rewrite(query, context)
            logger.info(f"Rewritten query: {rewritten_query}")
            logger.info(f"Going with original query: {query}")

            #2: Vector Retrieval
            query_results: List[QueryResult] = self.retriever.retrieve(collection_name, query)
            logger.info(f"Retrieved {len(query_results)} documents")

            # Get all chunks to generate the answer from the LLM
            all_texts = "\n".join(result.chunk.text for result in query_results)

            #3. Generate answer from all chunks 
            logger.info(f"Calling generator.generate with {all_texts}")
            generated_answer = self.generator.generate(query, all_texts)
            logger.info(f"Generated answer: {generated_answer}")

            #4. Evaluation
            logger.info("Now going to evaluate the results")
            evaluation_result = None
            
            return PipelineResult(
                rewritten_query=rewritten_query,
                query_results=query_results,
                generated_answer=generated_answer,
                evaluation=evaluation_result
            )
        except Exception as e:
            logger.error(f"Error in pipeline: {str(e)}")
            return PipelineResult(
                rewritten_query=rewritten_query if 'rewritten_query' in locals() else "",
                query_results = [],
                generated_answer="",
                evaluation={"error": str(e)}
            )
        
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update pipeline configuration.
        
        Args:
            new_config: New configuration dictionary to update with
        """
        self.config.update(new_config)
        # Reinitialize components with new config
        self.query_rewriter = QueryRewriter(self.config.get('query_rewriting', {}))
        vector_store_config = self.config.get('vector_store', {'type': 'milvus'})
        self.vector_store = get_datastore(vector_store_config['type'])
        self.collection_name = self.config.get('collection_name', 'default_collection')
        self.document_store = DocumentStore(self.vector_store, self.collection_name)
        self.retriever = RetrieverFactory.create_retriever(self.config.get('retrieval', {}), self.document_store)
        self.generator = GeneratorFactory.create_generator(self.config.get('generation', {}))
        self.evaluator = EvaluatorFactory.create_evaluator(self.config.get('evaluation', {}))
        logger.info("Pipeline configuration updated")
