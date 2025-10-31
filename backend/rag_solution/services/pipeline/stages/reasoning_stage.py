"""
Reasoning stage.

This stage applies Chain of Thought reasoning for complex questions.
Wraps the ChainOfThoughtService functionality.
"""

from core.logging_utils import get_logger
from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput
from rag_solution.services.pipeline.base_stage import BaseStage, StageResult
from rag_solution.services.pipeline.search_context import SearchContext

logger = get_logger("services.pipeline.stages.reasoning")


class ReasoningStage(BaseStage):  # pylint: disable=too-few-public-methods
    """
    Applies Chain of Thought reasoning for complex questions.

    This stage:
    1. Checks if CoT is enabled (automatic detection or explicit)
    2. Converts query_results to context documents
    3. Executes CoT reasoning via ChainOfThoughtService
    4. Adds reasoning steps and final answer to context

    Note: Single public method (execute) is by design for pipeline stage pattern.
    """

    def __init__(self, chain_of_thought_service: "ChainOfThoughtService") -> None:  # type: ignore
        """
        Initialize the reasoning stage.

        Args:
            chain_of_thought_service: ChainOfThoughtService instance for CoT reasoning
        """
        super().__init__("Reasoning")
        self.cot_service = chain_of_thought_service

    async def execute(self, context: SearchContext) -> StageResult:
        """
        Execute CoT reasoning.

        Args:
            context: Current search context

        Returns:
            StageResult with CoT results in context

        Raises:
            ValueError: If required context attributes are missing
            AttributeError: If context attributes are not accessible
        """
        self._log_stage_start(context)

        try:
            # Check if CoT should be used
            if not self._should_use_cot(context):
                logger.info("CoT not needed for this query")
                result = StageResult(success=True, context=context)
                self._log_stage_complete(result)
                return result

            # Ensure we have query results
            if context.query_results is None:
                raise ValueError("Query results not set in context")

            # Convert query_results to context documents
            context_docs = self._extract_context_documents(context)

            # Convert SearchInput to ChainOfThoughtInput
            cot_input = self._convert_to_cot_input(context)

            # Execute CoT
            cot_result = await self.cot_service.execute_chain_of_thought(
                cot_input, context_docs, user_id=str(context.user_id)
            )

            logger.info(
                "CoT reasoning completed: %d steps, strategy=%s, confidence=%.2f",
                len(cot_result.reasoning_steps),
                cot_result.reasoning_strategy,
                cot_result.total_confidence,
            )

            # Update context with CoT results
            context.cot_output = cot_result
            context.add_metadata(
                "reasoning",
                {
                    "strategy": cot_result.reasoning_strategy,
                    "steps_count": len(cot_result.reasoning_steps),
                    "confidence": cot_result.total_confidence,
                    "execution_time": cot_result.total_execution_time,
                },
            )

            result = StageResult(success=True, context=context)
            self._log_stage_complete(result)
            return result

        except (ValueError, AttributeError, TypeError, KeyError) as e:
            return await self._handle_error(context, e)

    def _should_use_cot(self, context: SearchContext) -> bool:
        """
        Determine if Chain of Thought should be used.

        Args:
            context: Search context

        Returns:
            True if CoT should be used, False otherwise
        """
        config_metadata = context.search_input.config_metadata or {}

        # Explicit disable
        if config_metadata.get("cot_disabled", False):
            return False

        # Explicit enable
        if config_metadata.get("cot_enabled", False):
            return True

        # Automatic detection via ChainOfThoughtService
        # For now, let's use a simple heuristic: complex questions (multi-part, long)
        question = context.search_input.question
        question_length = len(question.split())
        has_multiple_parts = any(word in question.lower() for word in ["and", "also", "additionally", "furthermore"])

        # Use CoT for complex questions (>15 words or multiple parts)
        return question_length > 15 or has_multiple_parts

    def _extract_context_documents(self, context: SearchContext) -> list[str]:
        """
        Extract context documents from query results.

        Args:
            context: Search context

        Returns:
            List of document texts
        """
        context_docs = []
        if context.query_results:
            for result in context.query_results:
                if hasattr(result, "chunk") and result.chunk and hasattr(result.chunk, "text"):
                    text = result.chunk.text
                    if text:
                        context_docs.append(text)
                elif hasattr(result, "text"):
                    text = result.text
                    if text:
                        context_docs.append(text)
        return context_docs

    def _convert_to_cot_input(self, context: SearchContext) -> ChainOfThoughtInput:
        """
        Convert SearchInput to ChainOfThoughtInput.

        Args:
            context: Search context

        Returns:
            ChainOfThoughtInput instance
        """
        config_metadata = context.search_input.config_metadata or {}

        return ChainOfThoughtInput(
            question=context.search_input.question,
            collection_id=context.collection_id,
            user_id=context.user_id,
            cot_config=config_metadata.get("cot_config"),
            context_metadata=config_metadata,
        )
