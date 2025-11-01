"""
Generation stage.

This stage generates the final answer using LLM or CoT reasoning.
Wraps the answer generation functionality from PipelineService.
"""

import re

from core.logging_utils import get_logger
from rag_solution.services.pipeline.base_stage import BaseStage, StageResult
from rag_solution.services.pipeline.search_context import SearchContext

logger = get_logger("services.pipeline.stages.generation")


class GenerationStage(BaseStage):  # pylint: disable=too-few-public-methods
    """
    Generates final answer using LLM or CoT reasoning.

    This stage:
    1. Checks if CoT result is available (use that as answer)
    2. Otherwise, generates answer from reranked documents
    3. Applies answer cleaning and formatting
    4. Updates context with generated answer

    Note: Single public method (execute) is by design for pipeline stage pattern.
    """

    def __init__(self, pipeline_service: "PipelineService") -> None:  # type: ignore
        """
        Initialize the generation stage.

        Args:
            pipeline_service: PipelineService instance for generation operations
        """
        super().__init__("Generation")
        self.pipeline_service = pipeline_service

    async def execute(self, context: SearchContext) -> StageResult:
        """
        Execute answer generation.

        Args:
            context: Current search context

        Returns:
            StageResult with generated answer in context

        Raises:
            ValueError: If required context attributes are missing
            AttributeError: If context attributes are not accessible
        """
        self._log_stage_start(context)

        try:
            # Ensure we have query results
            if context.query_results is None:
                raise ValueError("Query results not set in context")

            # Ensure we have pipeline_id
            if not context.pipeline_id:
                raise ValueError("Pipeline ID not set in context")

            # Determine answer source
            if context.cot_output:
                # Use CoT answer
                generated_answer = context.cot_output.final_answer
                answer_source = "cot"
                logger.info("Using CoT-generated answer")
            else:
                # Generate answer from documents
                generated_answer = await self._generate_answer_from_documents(context)
                answer_source = "llm"
                logger.info("Generated answer using LLM")

            # Clean answer
            cleaned_answer = self._clean_answer(generated_answer)

            logger.info("Answer generated: %d chars, source=%s", len(cleaned_answer), answer_source)

            # Update context
            context.generated_answer = cleaned_answer
            context.add_metadata("generation", {"source": answer_source, "answer_length": len(cleaned_answer)})

            result = StageResult(success=True, context=context)
            self._log_stage_complete(result)
            return result

        except (ValueError, AttributeError, TypeError, KeyError) as e:
            return await self._handle_error(context, e)

    async def _generate_answer_from_documents(self, context: SearchContext) -> str:
        """
        Generate answer using LLM from documents.

        Args:
            context: Search context

        Returns:
            Generated answer text
        """
        # Validate configuration and get required components
        _, llm_parameters, provider = self.pipeline_service._validate_configuration(
            context.pipeline_id,
            context.user_id,  # pylint: disable=protected-access
        )

        # Get templates
        rag_template, _ = self.pipeline_service._get_templates(context.user_id)  # pylint: disable=protected-access

        # Format context from query results
        context_text = self.pipeline_service._format_context(  # pylint: disable=protected-access
            rag_template.id, context.query_results
        )

        # Use rewritten query if available, otherwise original question
        query = context.rewritten_query or context.search_input.question

        # Generate answer
        answer = self.pipeline_service._generate_answer(  # pylint: disable=protected-access
            context.user_id, query, context_text, provider, llm_parameters, rag_template
        )

        return answer

    def _clean_answer(self, answer: str) -> str:
        """
        Clean generated answer by removing artifacts.

        Args:
            answer: Raw answer text

        Returns:
            Cleaned answer text
        """
        # Remove common LLM artifacts
        cleaned = answer.strip()

        # Remove "Answer:" prefix if present
        cleaned = re.sub(r"^(Answer|Response|Result):\s*", "", cleaned, flags=re.IGNORECASE)

        # Remove thinking tags if present (from CoT leakage)
        cleaned = re.sub(r"<thinking>.*?</thinking>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)

        # Remove extra whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        return cleaned
