"""Pipeline implementation for RAG processing."""

import logging
from typing import List, Dict, Any, Generator, Optional, Iterator, AsyncIterator
from uuid import UUID
from sqlalchemy.orm import Session
from dataclasses import dataclass

from rag_solution.query_rewriting.query_rewriter import QueryRewriter
from rag_solution.retrieval.factories import RetrieverFactory
from rag_solution.generation.factories import GeneratorFactory, EvaluatorFactory
from vectordbs.factory import get_datastore
from rag_solution.data_ingestion.ingestion import DocumentStore
from vectordbs.data_types import Document, QueryResult, DocumentChunkWithScore
from core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PipelineResult:
    """Result from pipeline processing."""
    original_query: str
    rewritten_query: str
    retrieved_documents: List[str]
    generated_answer: str
    evaluation: Optional[Dict[str, Any]] = None

class Pipeline():
    def __init__(self, config: Dict[str, Any], db: Session):
        """Initialize the RAG Pipeline."""
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

    async def initialize(self):
        """Initialize the pipeline and load documents."""
        await self._load_documents()

    async def _load_documents(self):
        """Load and process documents."""
        data_source = self.config.get('data_source', [])
        try:
            await self.document_store.load_documents(data_source)
            logger.info(f"Loaded documents into collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
            raise

    def get_collection_chunks(self, collection_name: str) -> List[DocumentChunkWithScore]:
        """
        Get document chunks from a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            List[DocumentChunkWithScore]: List of document chunks with scores
        """
        try:
            # Use retriever to get representative documents
            retrieved_docs = self.retriever.retrieve(
                collection_name=collection_name,
                query="",  # Empty query to get representative documents
                number_of_results=settings.top_k  # Use configured top_k from settings
            )
            
            # Extract chunks from retrieved documents
            chunks = []
            for doc in retrieved_docs:
                if hasattr(doc, 'data') and doc.data:
                    chunks.extend(doc.data)
            return chunks
        except Exception as e:
            logger.error(f"Error getting collection chunks: {e}")
            return []

    async def process(self, query: str, collection_name: str, context: Optional[Dict[str, Any]] = None) -> PipelineResult:
        """Process a query through the RAG pipeline."""
        try:
            if not query.strip():
                raise ValueError("Query cannot be empty")

            rewritten_query = self.query_rewriter.rewrite(query, context)
            logger.info(f"Rewritten query: {rewritten_query}")

            retrieved_docs: List[QueryResult] = self.retriever.retrieve(collection_name, rewritten_query)
            logger.info(f"Retrieved {len(retrieved_docs)} documents")

            # Extract text from retrieved documents
            all_texts = []
            for doc_index, doc in enumerate(retrieved_docs):
                logger.info(f"Processing QueryResult {doc_index + 1}")
                logger.info(f"  Similarities: {doc.similarities}")
                logger.info(f"  IDs: {doc.ids}")
                
                if doc.data:
                    for chunk_index, chunk in enumerate(doc.data):
                        all_texts.append(chunk.text)
                        logger.info(f"  Chunk {chunk_index + 1}:")

            logger.info(f"\nTotal texts extracted: {len(all_texts)}")

            # Generate answer
            context = "\n".join(all_texts)
            logger.info(f"Calling generator.generate with {rewritten_query}")
            generated_answer = self.generator.generate(rewritten_query, context)
            logger.info(f"Generated answer: {generated_answer}")

            logger.info("Now going to evaluate the results")
            evaluation_result = None
            
            return PipelineResult(
                original_query=query,
                rewritten_query=rewritten_query,
                retrieved_documents=all_texts,
                generated_answer=generated_answer,
                evaluation=evaluation_result
            )
        except Exception as e:
            logger.error(f"Error in pipeline: {str(e)}")
            return PipelineResult(
                original_query=query,
                rewritten_query=rewritten_query if 'rewritten_query' in locals() else "",
                retrieved_documents=[],
                generated_answer="",
                evaluation={"error": str(e)}
            )

    async def process_stream(self, query: str, collection_name: str, context: Optional[Dict[str, Any]] = None) -> AsyncIterator[Dict[str, Any]]:
        """Process a query with streaming response."""
        try:
            if not query.strip():
                raise ValueError("Query cannot be empty")

            rewritten_query = self.query_rewriter.rewrite(query, context)
            logger.info(f"Rewritten query: {rewritten_query}")
            
            retrieved_documents = self.retriever.retrieve(collection_name, rewritten_query)
            logger.info(f"Retrieved {len(retrieved_documents)} documents")
            
            yield {
                'original_query': query,
                'rewritten_query': rewritten_query,
                'retrieved_documents': retrieved_documents,
            }

            generation_params = {
                'max_new_tokens': settings.max_new_tokens,
                'min_new_tokens': settings.min_new_tokens,
                'temperature': settings.temperature,
                'top_k': settings.top_k,
                'random_seed': settings.random_seed
            }
            
            response_chunks = []
            for chunk in self.generator.generate_stream(rewritten_query, retrieved_documents, **generation_params):
                response_chunks.append(chunk)
                yield {'response_chunk': chunk}

            full_response = ''.join(response_chunks)
            evaluation_result = self.evaluator.evaluate(query, full_response, retrieved_documents)
            yield {'evaluation': evaluation_result}

            logger.info("Finished streaming response")
        except Exception as e:
            logger.error(f"Error in pipeline stream: {str(e)}")
            yield {
                'error': str(e),
                'original_query': query
            }

    def update_config(self, new_config: Dict[str, Any]):
        """Update pipeline configuration."""
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
