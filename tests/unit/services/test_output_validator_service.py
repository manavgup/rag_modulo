"""Unit tests for OutputValidatorService.

Tests the validation service for structured LLM outputs including:
- Citation validation
- Answer completeness validation
- Confidence score validation
- Retry logic
- Quality assessment
"""

from unittest.mock import Mock

import pytest

from rag_solution.schemas.structured_output_schema import (
    Citation,
    FormatType,
    ReasoningStep,
    StructuredAnswer,
    StructuredOutputConfig,
)
from rag_solution.services.output_validator_service import (
    OutputValidationError,
    OutputValidatorService,
)


class TestOutputValidatorService:
    """Test cases for OutputValidatorService."""

    @pytest.fixture
    def validator(self):
        """Create validator service instance."""
        return OutputValidatorService(max_retries=3, min_confidence=0.6, require_citations=True, min_answer_length=20)

    @pytest.fixture
    def valid_answer(self):
        """Create a valid structured answer."""
        citation = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="This is a relevant excerpt from the document.",
            relevance_score=0.95,
        )
        return StructuredAnswer(
            answer="This is a comprehensive answer to the question with sufficient detail.",
            confidence=0.92,
            citations=[citation],
            format_type=FormatType.STANDARD,
        )

    @pytest.fixture
    def context_documents(self):
        """Create context documents for validation."""
        return [
            {"id": "550e8400-e29b-41d4-a716-446655440000", "title": "Test Document", "content": "Document content..."}
        ]

    def test_validate_valid_answer(self, validator, valid_answer, context_documents):
        """Test validation passes for valid answer."""
        is_valid, issues = validator.validate_structured_answer(valid_answer, context_documents)
        assert is_valid is True
        assert len(issues) == 0

    def test_validate_short_answer(self, validator, context_documents):
        """Test validation fails for short answer."""
        citation = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="Test excerpt",
            relevance_score=0.95,
        )
        answer = StructuredAnswer(
            answer="Too short", confidence=0.9, citations=[citation], format_type=FormatType.STANDARD
        )

        is_valid, issues = validator.validate_structured_answer(answer, context_documents)
        assert is_valid is False
        assert any("too short" in issue.lower() for issue in issues)

    def test_validate_low_confidence(self, validator, context_documents):
        """Test validation fails for low confidence."""
        citation = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="Test excerpt",
            relevance_score=0.95,
        )
        answer = StructuredAnswer(
            answer="This is a sufficient answer with enough detail.",
            confidence=0.4,
            citations=[citation],
            format_type=FormatType.STANDARD,
        )

        is_valid, issues = validator.validate_structured_answer(answer, context_documents)
        assert is_valid is False
        assert any("confidence" in issue.lower() for issue in issues)

    def test_validate_missing_citations(self, validator, context_documents):
        """Test validation fails when citations are required but missing."""
        answer = StructuredAnswer(
            answer="This is a sufficient answer with enough detail.",
            confidence=0.9,
            citations=[],
            format_type=FormatType.STANDARD,
        )

        is_valid, issues = validator.validate_structured_answer(answer, context_documents)
        assert is_valid is False
        assert any("citations" in issue.lower() for issue in issues)

    def test_validate_invalid_document_id(self, validator, context_documents):
        """Test validation fails for citation with invalid document ID."""
        citation = Citation(
            document_id="11111111-1111-4111-8111-111111111111",  # Valid UUID4 but not in context
            title="Unknown Document",
            excerpt="Test excerpt",
            relevance_score=0.95,
        )
        answer = StructuredAnswer(
            answer="This is a sufficient answer with enough detail.",
            confidence=0.9,
            citations=[citation],
            format_type=FormatType.STANDARD,
        )

        is_valid, issues = validator.validate_structured_answer(answer, context_documents)
        assert is_valid is False
        assert any("not in context" in issue.lower() for issue in issues)

    def test_validate_short_excerpt(self, validator, context_documents):
        """Test validation fails for citation with short excerpt."""
        citation = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="Short",  # Too short
            relevance_score=0.95,
        )
        answer = StructuredAnswer(
            answer="This is a sufficient answer with enough detail.",
            confidence=0.9,
            citations=[citation],
            format_type=FormatType.STANDARD,
        )

        is_valid, issues = validator.validate_structured_answer(answer, context_documents)
        assert is_valid is False
        assert any("excerpt" in issue.lower() for issue in issues)

    def test_validate_invalid_relevance_score(self, validator, context_documents):
        """Test validation catches invalid relevance scores."""
        # This should be caught by Pydantic validation before reaching validator
        with pytest.raises(Exception):  # ValidationError from Pydantic
            Citation(
                document_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test Document",
                excerpt="Test excerpt that is long enough",
                relevance_score=1.5,  # Invalid
            )

    def test_validate_reasoning_steps(self, validator, context_documents):
        """Test validation checks reasoning steps completeness."""
        from pydantic import ValidationError

        # Test that ReasoningStep with empty thought fails at construction
        with pytest.raises(ValidationError, match="Field cannot be empty"):
            ReasoningStep(step_number=1, thought="", conclusion="Conclusion")

    def test_validate_with_config(self, validator, valid_answer, context_documents):
        """Test validation with custom config."""
        config = StructuredOutputConfig(min_confidence=0.5)
        is_valid, issues = validator.validate_structured_answer(valid_answer, context_documents, config)
        assert is_valid is True
        assert len(issues) == 0

    def test_validate_with_retry_success(self, validator, valid_answer, context_documents):
        """Test retry logic succeeds on first attempt."""
        generate_fn = Mock(return_value=valid_answer)

        result = validator.validate_with_retry(generate_fn, context_documents)

        assert result == valid_answer
        assert generate_fn.call_count == 1

    def test_validate_with_retry_success_on_second_attempt(self, validator, valid_answer, context_documents):
        """Test retry logic succeeds on second attempt."""
        invalid_answer = StructuredAnswer(
            answer="Too short", confidence=0.9, citations=[], format_type=FormatType.STANDARD
        )

        generate_fn = Mock(side_effect=[invalid_answer, valid_answer])

        result = validator.validate_with_retry(generate_fn, context_documents)

        assert result == valid_answer
        assert generate_fn.call_count == 2

    def test_validate_with_retry_exhausted(self, validator, context_documents):
        """Test retry logic fails after max retries."""
        invalid_answer = StructuredAnswer(
            answer="Too short", confidence=0.9, citations=[], format_type=FormatType.STANDARD
        )

        generate_fn = Mock(return_value=invalid_answer)

        with pytest.raises(OutputValidationError) as exc_info:
            validator.validate_with_retry(generate_fn, context_documents)

        assert "after 3 attempts" in str(exc_info.value)
        assert generate_fn.call_count == 3
        assert len(exc_info.value.issues) > 0

    def test_assess_quality_standard(self, validator, valid_answer):
        """Test quality assessment for standard answer."""
        metrics = validator.assess_quality(valid_answer)

        assert "confidence" in metrics
        assert "num_citations" in metrics
        assert "answer_length" in metrics
        assert "has_reasoning" in metrics
        assert "avg_relevance" in metrics
        assert "quality_score" in metrics

        assert metrics["confidence"] == 0.92
        assert metrics["num_citations"] == 1
        assert metrics["has_reasoning"] is False
        assert 0.0 <= metrics["quality_score"] <= 1.0

    def test_assess_quality_with_reasoning(self, validator, context_documents):
        """Test quality assessment for answer with reasoning."""
        citation = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="Test excerpt",
            relevance_score=0.95,
        )
        step = ReasoningStep(step_number=1, thought="Analysis...", conclusion="Conclusion...")

        answer = StructuredAnswer(
            answer="Answer with reasoning and sufficient detail for quality assessment.",
            confidence=0.95,
            citations=[citation],
            reasoning_steps=[step],
            format_type=FormatType.COT_REASONING,
        )

        metrics = validator.assess_quality(answer)

        assert metrics["has_reasoning"] is True
        # Quality score should be higher due to reasoning (expected ~0.65)
        assert metrics["quality_score"] > 0.6

    def test_assess_quality_multiple_citations(self, validator, context_documents):
        """Test quality assessment with multiple citations."""
        citations = [
            Citation(
                document_id="550e8400-e29b-41d4-a716-446655440000",
                title=f"Document {i}",
                excerpt=f"Excerpt {i}",
                relevance_score=0.9 - (i * 0.1),
                chunk_id=f"chunk_{i}",  # Add unique chunk_ids to prevent duplicate removal
            )
            for i in range(3)
        ]

        answer = StructuredAnswer(
            answer="Answer with multiple citations and sufficient detail for assessment.",
            confidence=0.9,
            citations=citations,
            format_type=FormatType.STANDARD,
        )

        metrics = validator.assess_quality(answer)

        assert metrics["num_citations"] == 3
        assert metrics["avg_relevance"] > 0.0
        # More citations should improve quality score
        assert metrics["quality_score"] > 0.6
