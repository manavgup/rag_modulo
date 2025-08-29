import asyncio
import json
from typing import Any

import json_repair
import pydantic
from dotenv import find_dotenv, load_dotenv
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from pydantic import BaseModel

from core.logging_utils import get_logger
from rag_solution.evaluation.metrics import AnswerRelevance, AnswerSimilarity, ContextRelevance, Faithfulness
from rag_solution.evaluation.prompts import (
    ANSWER_RELEVANCE_PROMPT_LLAMA3,
    ANSWER_SIMILARITY_EVALUATION_PROMPT_LLAMA3,
    CONTEXT_RELEVANCY_PROMPT_LLAMA3,
    FAITHFULNESS_PROMPT_LLAMA3,
)

logger = get_logger(__name__)
from vectordbs.utils.watsonx import generate_batch, generate_text, get_model

BASE_LLM_PARAMETERS = {
    GenParams.DECODING_METHOD: "greedy",
    GenParams.RANDOM_SEED: 60,
    GenParams.MAX_NEW_TOKENS: 200,
    GenParams.MIN_NEW_TOKENS: 1,
    GenParams.TEMPERATURE: 0.2,
    GenParams.STOP_SEQUENCES: ["-------", "\n-------\n"],
}


def get_schema(pydantic_object: pydantic.BaseModel, empty: bool = False, json_output: bool = False) -> str | dict:
    if issubclass(pydantic_object, pydantic.BaseModel):
        pydantic_model = pydantic_object.model_json_schema()
    elif issubclass(pydantic_object, pydantic.v1.BaseModel):
        pydantic_model = pydantic_object.schema()
    else:
        raise ValueError("should be a valid pydantic_model schema")

    schema = dict(pydantic_model.items())
    reduced_schema = schema
    if "title" in reduced_schema:
        del reduced_schema["title"]
    if "type" in reduced_schema:
        del reduced_schema["type"]

    if empty:
        expected_schema = {key: None for key, value in reduced_schema.get("properties").items()}
    else:
        expected_schema = {key: f"<{value['description']}>" for key, value in reduced_schema.get("properties").items()}

    return expected_schema if json_output else json.dumps(expected_schema)


def init_llm(
    parameters: dict[str, str | int | float] = BASE_LLM_PARAMETERS,
    MODEL_ID="meta-llama/llama-3-3-70b-instruct",
) -> ModelInference:
    """
    Initializes a language model with the given parameters.

    :param parameters: A dictionary of parameters for the language model.
    :param MODEL_ID: A string representing the model ID. Defaults to a specific model.
    :return: An instance of a language model - BaseLanguageModel
    """
    try:
        _ = load_dotenv(find_dotenv())
        return get_model(generate_params=parameters, model_id=MODEL_ID)
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        raise RuntimeError(f"Failed to initialize LLM: {e}")


def get_evaluator():
    """Get or create the evaluator instance."""
    return init_llm(parameters=BASE_LLM_PARAMETERS)


# Base class for evaluators with a default LLM
class BaseEvaluator:
    def __init__(
        self,
        llm: ModelInference | None = None,
        prompt: str = None,
        pydantic_model: BaseModel = None,
    ):
        self.llm = llm or get_evaluator()
        self.prompt = prompt
        self.pydantic_model = pydantic_model

    def evaluate(self, inputs: dict):
        schema = get_schema(self.pydantic_model)
        inputs = inputs | {"schema": schema}
        prompt = self.prompt.format(**inputs)
        generated_text = generate_text(prompt=prompt, wx_model=self.llm)
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
            schema = get_schema(self.pydantic_model)
            inputs = {**inputs, "schema": schema}
            prompt = self.prompt.format(**inputs)

            response = await llm.agenerate(prompt=prompt)
            if not response or "results" not in response or not response["results"]:
                raise ValueError("Response is missing 'results' or is empty.")

            generated_text = response["results"][0].get("generated_text", "").strip()
            if not generated_text:
                raise ValueError("Generated text is empty or missing.")

            return json_repair.repair_json(json_str=generated_text, return_objects=True)

        except Exception as e:
            raise RuntimeError(f"Failed to evaluate inputs: {e}")

    def batch_evaluate(self, inputs: list):
        all_outputs = []
        prompts = [
            self.prompt.format(**{**prompt_inputs, "schema": get_schema(self.pydantic_model)})
            for prompt_inputs in inputs
        ]
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        llm = init_llm(parameters=BASE_LLM_PARAMETERS)
        try:
            result = generate_batch(prompts=prompts, wx_model=llm, loop=loop, concurrency_level=10)
        finally:
            loop.close()
            llm.close_persistent_connection()

        for generated_text in result:
            try:
                final_json = json_repair.repair_json(json_str=generated_text, return_objects=True)
                if isinstance(final_json, list) or isinstance(final_json, str):
                    logger.warning(f"Output Parser during batch processing  [{final_json}]")
                    final_json = get_schema(self.pydantic_model, json_output=True, empty=True)
            except Exception as ex:
                logger.error(f"Output Parser Exception during batch processing for [{generated_text}] : {ex}")
                final_json = get_schema(self.pydantic_model, json_output=True, empty=True)

            all_outputs.append(final_json)

        return all_outputs


# Specific evaluator for Faithfulness
class FaithfulnessEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__(prompt=FAITHFULNESS_PROMPT_LLAMA3, pydantic_model=Faithfulness)
        self.scores = {"High": 1, "Medium": 0.5, "Low": 0}

    def evaluate(self, context: str, answer: str) -> dict:
        result = super().evaluate(inputs={"context": context, "answer": answer})
        result["score"] = self.scores.get(result.get("faithfulness_rate"))
        return result

    async def a_evaluate(self, context: str, answer: str, llm: ModelInference):
        result = await super().a_evaluate(inputs={"context": context, "answer": answer}, llm=llm)
        result["score"] = self.scores.get(result.get("faithfulness_rate"))
        return result

    def batch_evaluate(self, inputs: list):
        result = super().batch_evaluate(inputs)
        for item in result:
            if isinstance(item, list):
                print("list")
            if isinstance(item, str):
                print("str")
            item["score"] = self.scores.get(item.get("faithfulness_rate", 0))
        return result


# Specific evaluator for answer relevance
class AnswerRelevanceEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__(prompt=ANSWER_RELEVANCE_PROMPT_LLAMA3, pydantic_model=AnswerRelevance)
        self.scores = {"High": 1, "Medium": 0.5, "Low": 0}

    def evaluate(self, question: str, answer: str):
        result = super().evaluate(inputs={"question": question, "answer": answer})
        result["answer_relevance_score"] = self.scores.get(result.get("answer_relevance_rate"))
        return result

    async def a_evaluate(self, question: str, answer: str, llm: ModelInference):
        result = await super().a_evaluate(inputs={"question": question, "answer": answer}, llm=llm)
        result["answer_relevance_score"] = self.scores.get(result.get("answer_relevance_rate"))
        return result

    def batch_evaluate(self, inputs: list):
        result = super().batch_evaluate(inputs)
        for item in result:
            item["answer_relevance_score"] = self.scores.get(item.get("answer_relevance_rate", 0))
        return result


# Specific evaluator for answer similarity, reference answer is needed
class AnswerSimilarityEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__(prompt=ANSWER_SIMILARITY_EVALUATION_PROMPT_LLAMA3, pydantic_model=AnswerSimilarity)

    def evaluate(self, question: str, answer: str, reference_answer: str, show_logs: bool = False):
        return super().evaluate(
            inputs={
                "question": question,
                "answer": answer,
                "reference_answer": reference_answer,
            }
        )

    def batch_evaluate(self, inputs: list):
        return super().batch_evaluate(inputs)


# Specific evaluator for context relevancy, context and question is needed
class ContextRelevanceEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__(prompt=CONTEXT_RELEVANCY_PROMPT_LLAMA3, pydantic_model=ContextRelevance)
        self.scores = {"High": 1, "Medium": 0.5, "Low": 0}

    def evaluate(self, context: str, question: str):
        result = super().evaluate(inputs={"context": context, "question": question})
        result["context_relevance_score"] = self.scores.get(result.get("context_relevance_rate"))
        return result

    async def a_evaluate(self, context: str, question: str, llm: ModelInference):
        result = await super().a_evaluate(inputs={"context": context, "question": question}, llm=llm)
        result["context_relevance_score"] = self.scores.get(result.get("context_relevance_rate"))
        return result

    def batch_evaluate(self, inputs: list):
        result = super().batch_evaluate(inputs)
        for item in result:
            item["context_relevance_score"] = self.scores.get(item.get("context_relevance_rate", 0))
        return result
