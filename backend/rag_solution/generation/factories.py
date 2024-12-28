from typing import Dict, Any
from rag_solution.generation.generator import BaseGenerator, WatsonxGenerator, OpenAIGenerator, AnthropicGenerator
from rag_solution.evaluation.evaluator import RAGEvaluator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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