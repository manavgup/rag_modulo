import logging
from typing import Any

from rag_solution.evaluation.evaluator import RAGEvaluator
from rag_solution.generation.generator import AnthropicGenerator, BaseGenerator, OpenAIGenerator, WatsonxGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeneratorFactory:
    @staticmethod
    def create_generator(config: dict[str, Any]) -> BaseGenerator:
        generator_type = config.get("type", "watsonx")
        logger.info(f"Generator type: {generator_type}")
        if generator_type == "watsonx":
            return WatsonxGenerator(config)  # Pass the entire config, not just model_name
        elif generator_type == "openai":
            return OpenAIGenerator(config)  # Similarly, pass the full config to OpenAIGenerator
        elif generator_type == "anthropic":
            return AnthropicGenerator(config)  # Pass the entire config
        else:
            raise ValueError(f"Unsupported generator type: {generator_type}")


class EvaluatorFactory:
    @staticmethod
    def create_evaluator(config: dict[str, Any]) -> RAGEvaluator:  # noqa: ARG004
        # Currently, we only have one evaluator type, but we can extend this in the future
        return RAGEvaluator()
