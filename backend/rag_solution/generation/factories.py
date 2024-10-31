from typing import Dict, Any
from rag_solution.retrieval.retriever import BaseRetriever, VectorRetriever, KeywordRetriever, HybridRetriever
from rag_solution.generation.generator import BaseGenerator, WatsonxGenerator, OpenAIGenerator, AnthropicGenerator
from rag_solution.evaluation.evaluator import RAGEvaluator
from vectordbs.vector_store import VectorStore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RetrieverFactory:
    @staticmethod
    def create_retriever(config: Dict[str, Any], vector_store: VectorStore) -> BaseRetriever:
        retriever_type = config.get('type', 'hybrid')
        if retriever_type == 'vector':
            return VectorRetriever(vector_store)
        elif retriever_type == 'keyword':
            return KeywordRetriever(vector_store.get_all_documents())
        elif retriever_type == 'hybrid':
            return HybridRetriever(vector_store, vector_store.get_all_documents(), config.get('vector_weight', 0.7))
        else:
            raise ValueError(f"Unsupported retriever type: {retriever_type}")

class GeneratorFactory:
    @staticmethod
    def create_generator(config: Dict[str, Any]) -> BaseGenerator:
        generator_type = config.get('type', 'watsonx')
        logger.info(f"Generator type: {generator_type}")
        if generator_type == 'watsonx':
            return WatsonxGenerator(config)  # Pass the entire config, not just model_name
        elif generator_type == 'openai':
            return OpenAIGenerator(config)  # Similarly, pass the full config to OpenAIGenerator
        elif generator_type == 'anthropic':
            return AnthropicGenerator(config)  # Pass the entire config
        else:
            raise ValueError(f"Unsupported generator type: {generator_type}")

class EvaluatorFactory:
    @staticmethod
    def create_evaluator(config: Dict[str, Any]) -> RAGEvaluator:
        # Currently, we only have one evaluator type, but we can extend this in the future
        return RAGEvaluator()