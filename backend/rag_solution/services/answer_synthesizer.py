"""Answer synthesizer component for Chain of Thought reasoning."""

from core.config import Settings, get_settings
from core.logging_utils import get_logger
from rag_solution.generation.providers.base import LLMBase
from rag_solution.schemas.chain_of_thought_schema import ReasoningStep, SynthesisResult

logger = get_logger(__name__)


class AnswerSynthesizer:
    """Component for synthesizing answers from reasoning steps."""

    def __init__(self, llm_service: LLMBase | None = None, settings: Settings | None = None) -> None:
        """Initialize answer synthesizer.

        Args:
            llm_service: Optional LLM service for advanced synthesis.
            settings: Configuration settings.
        """
        self.llm_service = llm_service
        self.settings = settings or get_settings()

    def synthesize(self, original_question: str, reasoning_steps: list[ReasoningStep]) -> str:
        """Synthesize a final answer from reasoning steps with proper Markdown formatting.

        Args:
            original_question: The original question.
            reasoning_steps: The reasoning steps taken.

        Returns:
            The synthesized final answer formatted in Markdown.
        """
        if not reasoning_steps:
            return "Unable to generate an answer due to insufficient information."

        # Combine intermediate answers
        intermediate_answers = [step.intermediate_answer for step in reasoning_steps if step.intermediate_answer]

        if not intermediate_answers:
            return "Unable to synthesize an answer from the reasoning steps."

        # Simple synthesis with Markdown formatting
        if len(intermediate_answers) == 1:
            return intermediate_answers[0]

        # Combine multiple answers with proper Markdown structure
        synthesis_parts = []

        # Add main answer header
        synthesis_parts.append(f"## Answer to: {original_question}\n")

        # Add each reasoning step as a section
        for i, (step, answer) in enumerate(zip(reasoning_steps, intermediate_answers, strict=False), 1):
            synthesis_parts.append(f"### Step {i}: {step.question}\n")
            synthesis_parts.append(f"{answer}\n")

        # Add summary section if multiple steps
        if len(intermediate_answers) > 1:
            synthesis_parts.append("### Summary\n")
            synthesis_parts.append(f"Based on the analysis above, {intermediate_answers[0]}")

            for i, answer in enumerate(intermediate_answers[1:], 1):
                if i == len(intermediate_answers) - 1:
                    synthesis_parts.append(f" Additionally, {answer.lower()}")
                else:
                    synthesis_parts.append(f" Furthermore, {answer.lower()}")

        result = "\n".join(synthesis_parts)
        return result

    async def synthesize_answer(self, original_question: str, reasoning_steps: list[ReasoningStep]) -> SynthesisResult:
        """Synthesize answer and return result object like tests expect.

        Args:
            original_question: The original question.
            reasoning_steps: The reasoning steps taken.

        Returns:
            Object with final_answer and total_confidence attributes.
        """
        final_answer = self.synthesize(original_question, reasoning_steps)

        # Calculate total confidence
        confidences = [step.confidence_score for step in reasoning_steps if step.confidence_score is not None]
        total_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        # Return a proper SynthesisResult object
        return SynthesisResult(final_answer=final_answer, total_confidence=total_confidence)

    async def refine_answer(self, answer: str, context: list[str], user_id: str | None = None) -> str:
        """Refine an answer using additional context.

        Args:
            answer: The initial answer.
            context: Additional context.
            user_id: User ID for LLM service calls.

        Returns:
            The refined answer.
        """
        if not self.llm_service or not context:
            return answer

        try:
            # Create a refinement prompt that asks the LLM to improve the answer using context
            refinement_prompt = (
                f"Given the following initial answer:\n\n{answer}\n\n"
                f"And this additional context:\n\n{' '.join(context)}\n\n"
                "Please refine and improve the answer by incorporating relevant information "
                "from the context. Make it more comprehensive, accurate, and helpful while "
                "maintaining clarity and conciseness."
            )

            # Use the LLM service to refine the answer
            if hasattr(self.llm_service, "generate_text"):
                # Standard LLM provider interface - convert user_id to UUID if needed
                from uuid import UUID

                if user_id is not None:
                    try:
                        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

                        # Use templates for ALL providers for consistency
                        # WatsonX requires it, others benefit from structured prompting
                        from rag_solution.schemas.prompt_template_schema import PromptTemplateBase, PromptTemplateType

                        refinement_template = PromptTemplateBase(
                            id=user_uuid,
                            name="Answer Refinement Template",
                            user_id=user_uuid,
                            template_type=PromptTemplateType.CUSTOM,  # Could add REFINEMENT type later
                            template_format="{context}",
                            input_variables={"context": "The refinement prompt"},
                            is_default=False,
                            max_context_length=4000,  # Default context length
                        )

                        refined_response = await self.llm_service.generate_text(
                            user_id=user_uuid,
                            prompt=refinement_prompt,
                            template=refinement_template,
                            variables={"context": refinement_prompt},
                        )
                        return refined_response if isinstance(refined_response, str) else str(refined_response)
                    except (ValueError, TypeError):
                        # Invalid UUID format, skip refinement
                        return answer
                else:
                    # No user_id provided, skip refinement
                    return answer
            # Note: generate_response is not the standard interface, LLMs use generate_text
            # This fallback exists for backward compatibility but should not be used
            else:
                # No proper LLM interface available
                return answer

        except Exception:
            # Log the error but don't fail - return original answer as fallback
            return answer


__all__ = ["AnswerSynthesizer"]
