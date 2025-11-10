"""Output validation service for structured LLM responses.

This service validates structured outputs from LLM providers, ensuring:
- Citation validity against retrieved documents
- Answer completeness and quality
- Confidence score calibration
- Retry logic for invalid outputs

Follows industry best practices from OpenAI, Anthropic, and LangChain for
robust structured output validation with automatic retry mechanisms.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from core.custom_exceptions import LLMProviderError
from core.logging_utils import get_logger
from rag_solution.schemas.structured_output_schema import Citation, StructuredAnswer, StructuredOutputConfig

logger = get_logger("services.output_validator")


class OutputValidationError(Exception):
    """Exception raised when output validation fails."""

    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            issues: List of specific validation issues
        """
        super().__init__(message)
        self.issues = issues or []


class OutputValidatorService:
    """Service for validating structured LLM outputs with retry logic.

    This service validates structured answers against quality criteria and
    retrieved documents, implementing automatic retry logic for invalid outputs.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        min_confidence: Minimum acceptable confidence score (default: 0.0)
        require_citations: Whether citations are required (default: True)
        min_answer_length: Minimum answer length in characters (default: 10)
    """

    def __init__(
        self,
        max_retries: int = 3,
        min_confidence: float = 0.0,
        require_citations: bool = True,
        min_answer_length: int = 10,
    ) -> None:
        """Initialize validator service.

        Args:
            max_retries: Maximum number of retry attempts
            min_confidence: Minimum acceptable confidence score
            require_citations: Whether citations are required
            min_answer_length: Minimum answer length in characters
        """
        self.max_retries = max_retries
        self.min_confidence = min_confidence
        self.require_citations = require_citations
        self.min_answer_length = min_answer_length
        self.logger = get_logger(f"{__name__}.OutputValidatorService")

    def validate_structured_answer(
        self,
        answer: StructuredAnswer,
        context_documents: list[dict[str, Any]],
        config: StructuredOutputConfig | None = None,
    ) -> tuple[bool, list[str]]:
        """Validate structured answer against quality criteria.

        Args:
            answer: Structured answer to validate
            context_documents: Retrieved documents for citation validation
            config: Optional configuration for validation criteria

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues: list[str] = []

        # Use config settings if provided
        min_confidence = config.min_confidence if config else self.min_confidence
        require_citations = self.require_citations  # Could be overridden by config

        # Validate answer completeness
        if not answer.answer or len(answer.answer.strip()) < self.min_answer_length:
            issues.append(f"Answer too short (minimum {self.min_answer_length} characters)")

        # Validate confidence score
        if answer.confidence < min_confidence:
            issues.append(f"Confidence score {answer.confidence} below minimum {min_confidence}")

        # Validate citations
        if require_citations and len(answer.citations) == 0:
            issues.append("No citations provided")

        # Validate citation format and document references
        document_ids = {str(doc.get("id")) for doc in context_documents if doc.get("id")}
        for i, citation in enumerate(answer.citations):
            citation_issues = self._validate_citation(citation, document_ids, i)
            issues.extend(citation_issues)

        # Validate reasoning steps if present
        if answer.reasoning_steps:
            for i, step in enumerate(answer.reasoning_steps):
                if not step.thought or not step.conclusion:
                    issues.append(f"Reasoning step {i + 1} missing thought or conclusion")

        is_valid = len(issues) == 0
        if not is_valid:
            self.logger.warning(f"Validation failed with {len(issues)} issues: {issues}")

        return is_valid, issues

    def _validate_citation(self, citation: Citation, valid_document_ids: set[str], index: int) -> list[str]:
        """Validate a single citation.

        Args:
            citation: Citation to validate
            valid_document_ids: Set of valid document IDs from context
            index: Citation index for error messages

        Returns:
            List of validation issues
        """
        issues: list[str] = []

        # Check document ID exists in context
        if str(citation.document_id) not in valid_document_ids:
            issues.append(f"Citation {index + 1}: Document ID {citation.document_id} not in context")

        # Validate excerpt length
        if not citation.excerpt or len(citation.excerpt.strip()) < 10:
            issues.append(f"Citation {index + 1}: Excerpt too short or empty")

        # Validate relevance score
        if citation.relevance_score < 0.0 or citation.relevance_score > 1.0:
            issues.append(f"Citation {index + 1}: Invalid relevance score {citation.relevance_score}")

        return issues

    def validate_with_retry(
        self,
        generate_fn: Any,
        context_documents: list[dict[str, Any]],
        config: StructuredOutputConfig | None = None,
    ) -> StructuredAnswer:
        """Validate output with automatic retry logic.

        Args:
            generate_fn: Function that generates structured output (callable)
            context_documents: Retrieved documents for validation
            config: Optional configuration

        Returns:
            Validated structured answer

        Raises:
            OutputValidationError: If validation fails after max retries
            LLMProviderError: If generation fails
        """
        all_issues: list[str] = []

        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Validation attempt {attempt + 1}/{self.max_retries}")

                # Generate structured output
                answer = generate_fn()

                # Validate the output
                is_valid, issues = self.validate_structured_answer(answer, context_documents, config)

                if is_valid:
                    self.logger.info(f"Validation successful on attempt {attempt + 1}")
                    return answer

                # Validation failed - collect issues
                all_issues.extend([f"Attempt {attempt + 1}: {issue}" for issue in issues])
                self.logger.warning(f"Attempt {attempt + 1} validation failed: {issues}")

            except ValidationError as e:
                all_issues.append(f"Attempt {attempt + 1}: Validation error - {e!s}")
                self.logger.error(f"Validation error on attempt {attempt + 1}: {e}")

            except LLMProviderError as e:
                # Don't retry on provider errors - propagate immediately
                self.logger.error(f"Provider error on attempt {attempt + 1}: {e}")
                raise

            except Exception as e:
                all_issues.append(f"Attempt {attempt + 1}: Unexpected error - {e!s}")
                self.logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")

        # All retries exhausted
        error_msg = f"Validation failed after {self.max_retries} attempts"
        self.logger.error(f"{error_msg}. Issues: {all_issues}")
        raise OutputValidationError(error_msg, all_issues)

    def assess_quality(self, answer: StructuredAnswer) -> dict[str, Any]:
        """Assess the quality of a structured answer.

        Args:
            answer: Structured answer to assess

        Returns:
            Dictionary with quality metrics
        """
        metrics = {
            "confidence": answer.confidence,
            "num_citations": len(answer.citations),
            "answer_length": len(answer.answer),
            "has_reasoning": answer.reasoning_steps is not None and len(answer.reasoning_steps) > 0,
            "avg_relevance": (
                sum(c.relevance_score for c in answer.citations) / len(answer.citations) if answer.citations else 0.0
            ),
            "format_type": answer.format_type.value,
        }

        # Calculate overall quality score (0.0-1.0)
        quality_score = 0.0

        # Confidence contributes 40%
        quality_score += answer.confidence * 0.4

        # Citation quality contributes 30%
        if answer.citations:
            citation_quality = min(len(answer.citations) / 3.0, 1.0)  # Ideal: 3+ citations
            quality_score += citation_quality * 0.3

        # Answer completeness contributes 20%
        answer_quality = min(len(answer.answer) / 200.0, 1.0)  # Ideal: 200+ chars
        quality_score += answer_quality * 0.2

        # Reasoning presence contributes 10%
        if metrics["has_reasoning"]:
            quality_score += 0.1

        metrics["quality_score"] = round(quality_score, 2)

        return metrics
