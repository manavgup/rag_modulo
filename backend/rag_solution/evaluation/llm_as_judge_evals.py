import asyncio
import json
from typing import Any

import json_repair
import pydantic
from core.logging_utils import get_logger
from dotenv import find_dotenv, load_dotenv
from ibm_watsonx_ai.foundation_models import ModelInference  # type: ignore[import-untyped]
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams  # type: ignore[import-untyped]
from pydantic import BaseModel
from vectordbs.utils.watsonx import generate_batch, generate_text, get_model

from rag_solution.evaluation.metrics import AnswerRelevance, AnswerSimilarity, ContextRelevance, Faithfulness
from rag_solution.evaluation.prompts import (
    ANSWER_RELEVANCE_PROMPT_LLAMA3,
    ANSWER_SIMILARITY_EVALUATION_PROMPT_LLAMA3,
    CONTEXT_RELEVANCY_PROMPT_LLAMA3,
    FAITHFULNESS_PROMPT_LLAMA3,
)

logger = get_logger(__name__)

BASE_LLM_PARAMETERS = {
    GenParams.DECODING_METHOD: "greedy",
    GenParams.RANDOM_SEED: 60,
    GenParams.MAX_NEW_TOKENS: 200,
    GenParams.MIN_NEW_TOKENS: 1,
    GenParams.TEMPERATURE: 0.2,
    GenParams.STOP_SEQUENCES: ["-------", "\n-------\n"],
}


def get_schema(
    pydantic_object: pydantic.BaseModel | type[pydantic.BaseModel], empty: bool = False, json_output: bool = False
) -> str | dict:
    """Returns schema of the BaseModel"""
    if isinstance(pydantic_object, type):
        # Handle class type by getting schema directly
        # Check for v2 BaseModel first (has model_json_schema method)
        if hasattr(pydantic_object, "model_json_schema"):
            pydantic_model = pydantic_object.model_json_schema()
        # Check for v1 BaseModel (has schema method)
        elif hasattr(pydantic_object, "schema"):
            pydantic_model = pydantic_object.schema()
        else:
            raise ValueError("should be a valid pydantic_model class")
    else:
        # Handle instance types - check for available methods
        if hasattr(pydantic_object, "model_json_schema"):
            pydantic_model = pydantic_object.model_json_schema()
        elif hasattr(pydantic_object, "schema"):
            pydantic_model = pydantic_object.schema()
        else:
            raise ValueError("should be a valid pydantic_model instance")

    schema = dict(pydantic_model.items())
    reduced_schema = schema
    if "title" in reduced_schema:
        del reduced_schema["title"]
    if "type" in reduced_schema:
        del reduced_schema["type"]

    if empty:
        expected_schema = {key: None for key, value in reduced_schema.get("properties", {}).items()}
    else:
        expected_schema = {
            key: f"<{value.get('description', '') if isinstance(value, dict) and value.get('description') else ''}>"  # type: ignore[misc]
            for key, value in reduced_schema.get("properties", {}).items()
        }

    return expected_schema if json_output else json.dumps(expected_schema)


def init_llm(
    parameters: dict = BASE_LLM_PARAMETERS,
    model_id: str = "meta-llama/llama-3-3-70b-instruct",
) -> ModelInference:
    """
    Initializes a language model with the given parameters.

    :param parameters: A dictionary of parameters for the language model.
    :param MODEL_ID: A string representing the model ID. Defaults to a specific model.
    :return: An instance of a language model - BaseLanguageModel
    """
    try:
        _ = load_dotenv(find_dotenv())
        return get_model(generate_params=parameters, model_id=model_id)
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        raise RuntimeError(f"Failed to initialize LLM: {e}") from e


def get_evaluator() -> ModelInference:
    """Get or create the evaluator instance."""
    return init_llm(parameters=BASE_LLM_PARAMETERS)


# Base class for evaluators with a default LLM
class BaseEvaluator:
    def __init__(
        self,
        llm: ModelInference | None = None,
        prompt: str | None = None,
        pydantic_model: BaseModel | type[BaseModel] | None = None,
    ) -> None:
        self.llm = llm or get_evaluator()
        self.prompt = prompt
        self.pydantic_model = pydantic_model

    def evaluate(self, inputs: dict) -> Any:
        if self.pydantic_model is None:
            raise ValueError("pydantic_model must be provided")
        schema = get_schema(self.pydantic_model)
        inputs = inputs | {"schema": schema}
        if self.prompt is None:
            raise ValueError("prompt must be provided")
        prompt = self.prompt.format(**inputs)
        generated_text = generate_text(prompt=prompt, wx_model=self.llm)
        # Ensure we have a string for json_repair
        if isinstance(generated_text, list):
            generated_text = generated_text[0] if generated_text else ""
        return json_repair.repair_json(json_str=generated_text, return_objects=True)

    async def a_evaluate(self, inputs: dict[str, Any], llm: ModelInference) -> Any:
        """
        Evaluates the provided inputs using the specified LLM.

        Args:
            inputs (Dict[str, Any]): The inputs to be formatted into the prompt.
            llm (ModelInference): watsonx LLM instance with an `agenerate` async method.

        Returns:
            Any: The repaired JSON object from the generated text.
        """
        try:
            if self.pydantic_model is None:
                raise ValueError("pydantic_model must be provided")
            schema = get_schema(self.pydantic_model)
            inputs = {**inputs, "schema": schema}
            if self.prompt is None:
                raise ValueError("prompt must be provided")
            prompt = self.prompt.format(**inputs)

            response = await llm.agenerate(prompt=prompt)
            if not response or "results" not in response or not response["results"]:
                raise ValueError("Response is missing 'results' or is empty.")

            generated_text = response["results"][0].get("generated_text", "").strip()
            if not generated_text:
                raise ValueError("Generated text is empty or missing.")

            return json_repair.repair_json(json_str=generated_text, return_objects=True)

        except Exception as e:
            raise RuntimeError(f"Failed to evaluate inputs: {e}") from e

    def batch_evaluate(self, inputs: list) -> list[Any]:
        if self.pydantic_model is None:
            raise ValueError("pydantic_model must be provided")
        if self.prompt is None:
            raise ValueError("prompt must be provided")

        all_outputs = []
        prompts = [
            self.prompt.format(**{**prompt_inputs, "schema": get_schema(self.pydantic_model)})
            for prompt_inputs in inputs
        ]
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        llm = init_llm(parameters=BASE_LLM_PARAMETERS)
        try:
            result = generate_batch(prompts=prompts, wx_model=llm, concurrency_level=10)
        finally:
            loop.close()
            llm.close_persistent_connection()

        for generated_text in result:
            try:
                final_json = json_repair.repair_json(json_str=generated_text, return_objects=True)
                if isinstance(final_json, list | str):
                    logger.warning(f"Output Parser during batch processing  [{final_json}]")
                    final_json = get_schema(self.pydantic_model, json_output=True, empty=True)
            except Exception as ex:
                logger.error(f"Output Parser Exception during batch processing for [{generated_text}] : {ex}")
                final_json = get_schema(self.pydantic_model, json_output=True, empty=True)

            all_outputs.append(final_json)

        return all_outputs


# Specific evaluator for Faithfulness
class FaithfulnessEvaluator(BaseEvaluator):
    def __init__(self) -> None:
        super().__init__(prompt=FAITHFULNESS_PROMPT_LLAMA3, pydantic_model=Faithfulness)
        self.scores = {"High": 1, "Medium": 0.5, "Low": 0}

    def evaluate_faithfulness(self, context: str, answer: str) -> Any:
        """Evaluate faithfulness with convenient parameter names."""
        result = self.evaluate(inputs={"context": context, "answer": answer})
        if isinstance(result, dict):
            result["score"] = self.scores.get(result.get("faithfulness_rate", ""), 0)
        return result

    async def a_evaluate_faithfulness(self, context: str, answer: str, llm: ModelInference) -> Any:
        """Evaluate faithfulness asynchronously with convenient parameter names."""
        result = await self.a_evaluate(inputs={"context": context, "answer": answer}, llm=llm)
        if isinstance(result, dict):
            result["score"] = self.scores.get(result.get("faithfulness_rate", ""), 0)
        return result

    def batch_evaluate_faithfulness(self, inputs: list[dict[str, str]]) -> list[Any]:
        """Batch evaluate faithfulness with convenient input format."""
        # Convert list of dicts to the format expected by base class
        base_inputs = [{"context": item["context"], "answer": item["answer"]} for item in inputs]
        result = self.batch_evaluate(base_inputs)
        for item in result:
            if isinstance(item, dict):
                item["score"] = self.scores.get(item.get("faithfulness_rate", ""), 0)
        return result


# Specific evaluator for answer relevance
class AnswerRelevanceEvaluator(BaseEvaluator):
    def __init__(self) -> None:
        super().__init__(prompt=ANSWER_RELEVANCE_PROMPT_LLAMA3, pydantic_model=AnswerRelevance)
        self.scores = {"High": 1, "Medium": 0.5, "Low": 0}

    def evaluate_answer_relevance(self, question: str, answer: str) -> Any:
        """Evaluate answer relevance with convenient parameter names."""
        result = self.evaluate(inputs={"question": question, "answer": answer})
        if isinstance(result, dict):
            result["answer_relevance_score"] = self.scores.get(result.get("answer_relevance_rate", ""), 0)
        return result

    async def a_evaluate_answer_relevance(self, question: str, answer: str, llm: ModelInference) -> Any:
        """Evaluate answer relevance asynchronously with convenient parameter names."""
        result = await self.a_evaluate(inputs={"question": question, "answer": answer}, llm=llm)
        if isinstance(result, dict):
            result["answer_relevance_score"] = self.scores.get(result.get("answer_relevance_rate", ""), 0)
        return result

    def batch_evaluate_answer_relevance(self, inputs: list[dict[str, str]]) -> list[Any]:
        """Batch evaluate answer relevance with convenient input format."""
        # Convert list of dicts to the format expected by base class
        base_inputs = [{"question": item["question"], "answer": item["answer"]} for item in inputs]
        result = self.batch_evaluate(base_inputs)
        for item in result:
            if isinstance(item, dict):
                item["answer_relevance_score"] = self.scores.get(item.get("answer_relevance_rate", ""), 0)
        return result


# Specific evaluator for answer similarity, reference answer is needed
class AnswerSimilarityEvaluator(BaseEvaluator):
    def __init__(self) -> None:
        super().__init__(prompt=ANSWER_SIMILARITY_EVALUATION_PROMPT_LLAMA3, pydantic_model=AnswerSimilarity)

    def evaluate_answer_similarity(self, question: str, answer: str, reference_answer: str) -> Any:
        """Evaluate answer similarity with convenient parameter names."""
        return self.evaluate(
            inputs={
                "question": question,
                "answer": answer,
                "reference_answer": reference_answer,
            }
        )

    def batch_evaluate_answer_similarity(self, inputs: list[dict[str, str]]) -> list[Any]:
        """Batch evaluate answer similarity with convenient input format."""
        # Convert list of dicts to the format expected by base class
        base_inputs = [
            {"question": item["question"], "answer": item["answer"], "reference_answer": item["reference_answer"]}
            for item in inputs
        ]
        return self.batch_evaluate(base_inputs)


# Specific evaluator for context relevancy, context and question is needed
class ContextRelevanceEvaluator(BaseEvaluator):
    def __init__(self) -> None:
        super().__init__(prompt=CONTEXT_RELEVANCY_PROMPT_LLAMA3, pydantic_model=ContextRelevance)
        self.scores = {"High": 1, "Medium": 0.5, "Low": 0}

    def evaluate_context_relevance(self, context: str, question: str) -> Any:
        """Evaluate context relevance with convenient parameter names."""
        result = self.evaluate(inputs={"context": context, "question": question})
        if isinstance(result, dict):
            result["context_relevance_score"] = self.scores.get(result.get("context_relevance_rate", ""), 0)
        return result

    async def a_evaluate_context_relevance(self, context: str, question: str, llm: ModelInference) -> Any:
        """Evaluate context relevance asynchronously with convenient parameter names."""
        result = await self.a_evaluate(inputs={"context": context, "question": question}, llm=llm)
        if isinstance(result, dict):
            result["context_relevance_score"] = self.scores.get(result.get("context_relevance_rate", ""), 0)
        return result

    def batch_evaluate_context_relevance(self, inputs: list[dict[str, str]]) -> list[Any]:
        """Batch evaluate context relevance with convenient input format."""
        # Convert list of dicts to the format expected by base class
        base_inputs = [{"context": item["context"], "question": item["question"]} for item in inputs]
        result = self.batch_evaluate(base_inputs)
        for item in result:
            if isinstance(item, dict):
                item["context_relevance_score"] = self.scores.get(item.get("context_relevance_rate", ""), 0)
        return result
