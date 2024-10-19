import logging
import json
import asyncio
from typing import List, Dict, Any, Generator, Optional, Iterator
from dataclasses import dataclass
from rag_solution.query_rewriting.query_rewriter import QueryRewriter
from rag_solution.retrieval.factories import RetrieverFactory
from rag_solution.generation.factories import GeneratorFactory, EvaluatorFactory
from vectordbs.factory import get_datastore
from rag_solution.data_ingestion.ingestion import DocumentStore
from vectordbs.data_types import Document, QueryResult, DocumentChunkWithScore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PipelineResult:
    original_query: str
    rewritten_query: str
    retrieved_documents: List[str]
    generated_answer: str
    evaluation: Optional[Dict[str, Any]] = None

class Pipeline:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the RAG Pipeline.

        Args:
            config (Dict[str, Any]): Configuration dictionary for the pipeline.
        """
        self.config = config
        self.query_rewriter = QueryRewriter(config.get('query_rewriting', {}))
        
        vector_store_config = config.get('vector_store', {'type': 'milvus'})
        self.vector_store = get_datastore(vector_store_config)
        
        self.collection_name = config.get('collection_name', 'default_collection')
        self.document_store = DocumentStore(self.vector_store, self.collection_name)
        
        self.retriever = RetrieverFactory.create_retriever(config.get('retrieval', {}), self.document_store)
        self.generator = GeneratorFactory.create_generator(config.get('generation', {}))
        self.evaluator = EvaluatorFactory.create_evaluator(config.get('evaluation', {}))

    async def initialize(self):
        """
        Asynchronously initialize the pipeline, including document loading.
        """
        await self._load_documents()

    async def _load_documents(self):
        """
        Load documents from the specified data source and ingest them into the document store.
        """
        data_source = self.config.get('data_source', [])
        
        try:
            await self.document_store.load_documents(data_source)
            logger.info(f"Loaded documents into collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
            raise

    def process(self, query: str, collection_name: str, context: Optional[Dict[str, Any]] = None) -> PipelineResult:
        """
        Process a query through the RAG pipeline.

        Args:
            query (str): The query to process.
            collection_name (str): The name of the collection to search in.
            context (Optional[Dict[str, Any]]): Additional context for query rewriting.

        Returns:
            PipelineResult: The processed result containing query, rewritten query, retrieved documents, response, and evaluation metrics.
        """
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
                        # logger.info(f"    Chunk ID: {chunk.chunk_id}")
                        # logger.info(f"    Text: {chunk.text[:100]}...")  # Print first 100 characters
                        # logger.info(f"    Score: {chunk.score}")
                        # logger.info(f"    Metadata: {chunk.metadata}")

            logger.info(f"\nTotal texts extracted: {len(all_texts)}")

            context = "\n".join(all_texts)
            logger.info(f"Calling generator.generate with {rewritten_query}")
            generated_answer = self.generator.generate(rewritten_query, context)
            logger.info(f"Generated answer: {generated_answer}")

            logger.info("Now going to evaluate the results")

            # evaluation_result = self.evaluator.evaluate(query, generated_answer, retrieved_docs)
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

    def _extract_chunk_text(self, chunk: Any) -> Optional[str]:
        """
        Extract text from a chunk, handling different possible structures.
        """
        if isinstance(chunk, str):
            return chunk
        elif isinstance(chunk, dict):
            return chunk.get('text') or chunk.get('content')
        elif hasattr(chunk, 'text'):
            return chunk.text
        elif hasattr(chunk, 'content'):
            return chunk.content
        else:
            logger.warning(f"Unable to extract text from chunk: {chunk}")
            return None

    def _extract_chunk_metadata(self, chunk: Any) -> Dict[str, Any]:
        """
        Extract metadata from a chunk, handling different possible structures.
        """
        if isinstance(chunk, dict):
            return {k: v for k, v in chunk.items() if k not in ['text', 'content']}
        elif hasattr(chunk, '__dict__'):
            return {k: v for k, v in chunk.__dict__.items() if k not in ['text', 'content']}
        else:
            return {}

    def process_stream(self, query: str, collection_name: str, context: Optional[Dict[str, Any]] = None) -> Iterator[Dict[str, Any]]:
        """
        Process a query through the RAG pipeline with streaming response.

        Args:
            query (str): The query to process.
            collection_name (str): The name of the collection to search in.
            context (Optional[Dict[str, Any]]): Additional context for query rewriting.

        Yields:
            Dict[str, Any]: Chunks of the processed result.
        """
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

            generation_params = self.config.get('generation', {}).get('default_params', {})
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
        """
        Update the pipeline configuration.

        Args:
            new_config (Dict[str, Any]): New configuration to update.
        """
        self.config.update(new_config)
        # Reinitialize components with new config
        self.query_rewriter = QueryRewriter(self.config.get('query_rewriting', {}))
        vector_store_config = self.config.get('vector_store', {'type': 'milvus'})
        self.vector_store = get_datastore(vector_store_config)
        self.collection_name = self.config.get('collection_name', 'default_collection')
        self.document_store = DocumentStore(self.vector_store, self.collection_name)
        self.retriever = RetrieverFactory.create_retriever(self.config.get('retrieval', {}), self.document_store)
        self.generator = GeneratorFactory.create_generator(self.config.get('generation', {}))
        self.evaluator = EvaluatorFactory.create_evaluator(self.config.get('evaluation', {}))
        logger.info("Pipeline configuration updated")

# Example usage
if __name__ == "__main__":
    config = {
        'query_rewriting': {
            'use_simple_rewriter': True,
            'use_hyponym_rewriter': False
        },
        'retrieval': {
            'type': 'hybrid',
            'vector_weight': 0.7
        },
        'generation': {
            'type': 'watsonx',
            'model_name': 'flan-t5-xl',
            'default_params': {
                'max_new_tokens': 100,
                'temperature': 0.7
            }
        },
        'vector_store': {
            'type': 'milvus',
            'connection_args': {
                'host': 'localhost',
                'port': '19530'
            }
        },
        'data_source': ['/path/to/your/documents'],
        'collection_name': 'my_collection',
        'top_k': 5,
    }

    async def run_pipeline():
        pipeline = Pipeline(config)
        await pipeline.initialize()
        query = "What is the theory of relativity?"

        print("Non-streaming response:")
        result = pipeline.process(query, pipeline.collection_name)
        print(f"Original Query: {result.original_query}")
        print(f"Rewritten Query: {result.rewritten_query}")
        print("Retrieved Documents:")
        for doc in result.retrieved_documents:
            print(f"  - Content: {doc[:100]}...")
        print(f"Generated Response: {result.generated_answer}")
        print(f"Evaluation: {result.evaluation}")

        print("\nStreaming response:")
        for chunk in pipeline.process_stream(query, pipeline.collection_name):
            if 'error' in chunk:
                print(f"Error: {chunk['error']}")
            elif 'response_chunk' in chunk:
                print(chunk['response_chunk'], end='', flush=True)
            elif 'retrieved_documents' in chunk:
                print(f"\nOriginal Query: {chunk['original_query']}")
                print(f"Rewritten Query: {chunk['rewritten_query']}")
                print("Retrieved Documents:")
                for doc in chunk['retrieved_documents']:
                    if isinstance(doc, QueryResult):
                        print(f"  - Score: {doc.score}, Content: {doc.text[:100]}...")
                    elif isinstance(doc, dict):
                        print(f"  - Score: {doc.get('score', 'N/A')}, Content: {doc.get('text', '')[:100]}...")
            elif 'evaluation' in chunk:
                print("\nEvaluation Metrics:")
                for metric, value in chunk['evaluation'].items():
                    print(f"  {metric}: {value}")
        print()

    asyncio.run(run_pipeline())