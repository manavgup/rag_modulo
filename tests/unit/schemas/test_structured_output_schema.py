"""Unit tests for structured output schemas.

Tests the Pydantic models for structured LLM outputs including:
- Citation model validation
- ReasoningStep model validation
- StructuredAnswer model validation
- StructuredOutputConfig validation
"""

import pytest
from pydantic import UUID4, ValidationError

from rag_solution.schemas.structured_output_schema import (
    Citation,
    FormatType,
    ReasoningStep,
    StructuredAnswer,
    StructuredOutputConfig,
)


class TestCitation:
    """Test cases for Citation model."""

    def test_valid_citation(self):
        """Test creating a valid citation."""
        citation = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="This is a test excerpt.",
            relevance_score=0.95,
        )
        assert citation.document_id == UUID4("550e8400-e29b-41d4-a716-446655440000")
        assert citation.title == "Test Document"
        assert citation.excerpt == "This is a test excerpt."
        assert citation.relevance_score == 0.95
        assert citation.page_number is None
        assert citation.chunk_id is None

    def test_citation_with_optional_fields(self):
        """Test citation with all optional fields."""
        citation = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="This is a test excerpt.",
            page_number=42,
            relevance_score=0.95,
            chunk_id="chunk_123",
        )
        assert citation.page_number == 42
        assert citation.chunk_id == "chunk_123"

    def test_citation_empty_excerpt_validation(self):
        """Test that empty excerpt fails validation."""
        with pytest.raises(ValidationError, match="Excerpt cannot be empty"):
            Citation(
                document_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test Document",
                excerpt="",
                relevance_score=0.95,
            )

    def test_citation_relevance_score_bounds(self):
        """Test relevance score must be between 0.0 and 1.0."""
        # Test lower bound
        with pytest.raises(ValidationError):
            Citation(
                document_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test Document",
                excerpt="Test excerpt",
                relevance_score=-0.1,
            )

        # Test upper bound
        with pytest.raises(ValidationError):
            Citation(
                document_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test Document",
                excerpt="Test excerpt",
                relevance_score=1.1,
            )

    def test_citation_page_number_validation(self):
        """Test page number must be positive."""
        with pytest.raises(ValidationError):
            Citation(
                document_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test Document",
                excerpt="Test excerpt",
                page_number=0,
                relevance_score=0.95,
            )


class TestReasoningStep:
    """Test cases for ReasoningStep model."""

    def test_valid_reasoning_step(self):
        """Test creating a valid reasoning step."""
        step = ReasoningStep(
            step_number=1, thought="First, I analyze the question...", conclusion="The answer is based on..."
        )
        assert step.step_number == 1
        assert "analyze" in step.thought
        assert "based on" in step.conclusion
        assert len(step.citations) == 0

    def test_reasoning_step_with_citations(self):
        """Test reasoning step with citations."""
        citation = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="Test excerpt",
            relevance_score=0.95,
        )
        step = ReasoningStep(step_number=1, thought="Analysis...", conclusion="Conclusion...", citations=[citation])
        assert len(step.citations) == 1
        assert step.citations[0].title == "Test Document"

    def test_reasoning_step_empty_thought_validation(self):
        """Test that empty thought fails validation."""
        with pytest.raises(ValidationError, match="Field cannot be empty"):
            ReasoningStep(step_number=1, thought="", conclusion="Conclusion")

    def test_reasoning_step_empty_conclusion_validation(self):
        """Test that empty conclusion fails validation."""
        with pytest.raises(ValidationError, match="Field cannot be empty"):
            ReasoningStep(step_number=1, thought="Thought", conclusion="")

    def test_reasoning_step_number_positive(self):
        """Test step number must be positive."""
        with pytest.raises(ValidationError):
            ReasoningStep(step_number=0, thought="Thought", conclusion="Conclusion")


class TestStructuredAnswer:
    """Test cases for StructuredAnswer model."""

    def test_valid_structured_answer(self):
        """Test creating a valid structured answer."""
        citation = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="Test excerpt",
            relevance_score=0.95,
        )
        answer = StructuredAnswer(
            answer="This is the answer to your question.",
            confidence=0.92,
            citations=[citation],
            format_type=FormatType.STANDARD,
        )
        assert answer.answer == "This is the answer to your question."
        assert answer.confidence == 0.92
        assert len(answer.citations) == 1
        assert answer.format_type == FormatType.STANDARD
        assert answer.reasoning_steps is None

    def test_structured_answer_with_reasoning(self):
        """Test structured answer with reasoning steps."""
        citation = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="Test excerpt",
            relevance_score=0.95,
        )
        step = ReasoningStep(step_number=1, thought="Analysis...", conclusion="Conclusion...")
        answer = StructuredAnswer(
            answer="Final answer",
            confidence=0.85,
            citations=[citation],
            reasoning_steps=[step],
            format_type=FormatType.COT_REASONING,
        )
        assert answer.reasoning_steps is not None
        assert len(answer.reasoning_steps) == 1
        assert answer.reasoning_steps[0].step_number == 1

    def test_structured_answer_empty_answer_validation(self):
        """Test that empty answer fails validation."""
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            StructuredAnswer(answer="", confidence=0.9, citations=[], format_type=FormatType.STANDARD)

    def test_structured_answer_confidence_bounds(self):
        """Test confidence must be between 0.0 and 1.0."""
        citation = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="Test excerpt",
            relevance_score=0.95,
        )

        # Test lower bound
        with pytest.raises(ValidationError):
            StructuredAnswer(answer="Answer", confidence=-0.1, citations=[citation], format_type=FormatType.STANDARD)

        # Test upper bound
        with pytest.raises(ValidationError):
            StructuredAnswer(answer="Answer", confidence=1.1, citations=[citation], format_type=FormatType.STANDARD)

    def test_structured_answer_duplicate_citations(self):
        """Test that duplicate citations (same doc, chunk, page) are removed."""
        citation1 = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="Excerpt 1",
            relevance_score=0.95,
            chunk_id="chunk_1",
            page_number=5,
        )
        citation2 = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Document",
            excerpt="Excerpt 2",
            relevance_score=0.90,
            chunk_id="chunk_1",  # Same document, chunk, and page
            page_number=5,
        )
        answer = StructuredAnswer(
            answer="Answer",
            confidence=0.9,
            citations=[citation1, citation2],
            format_type=FormatType.STANDARD,
        )
        # Duplicates (same doc_id, chunk_id, page_number) should be removed
        assert len(answer.citations) == 1
        # Should keep the one with higher relevance score
        assert answer.citations[0].relevance_score == 0.95

    def test_structured_answer_multi_page_citations_preserved(self):
        """Test that citations from different pages of same document are preserved."""
        citation_page5 = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="IBM Annual Report 2023",
            excerpt="Revenue increased by 12%...",
            relevance_score=0.95,
            chunk_id=None,
            page_number=5,
        )
        citation_page12 = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="IBM Annual Report 2023",
            excerpt="Net income rose to $8.2B...",
            relevance_score=0.88,
            chunk_id=None,
            page_number=12,
        )
        citation_page18 = Citation(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            title="IBM Annual Report 2023",
            excerpt="Future outlook remains positive...",
            relevance_score=0.82,
            chunk_id=None,
            page_number=18,
        )
        answer = StructuredAnswer(
            answer="IBM's financial performance improved significantly in 2023.",
            confidence=0.92,
            citations=[citation_page5, citation_page12, citation_page18],
            format_type=FormatType.STANDARD,
        )
        # All 3 citations from different pages should be preserved
        assert len(answer.citations) == 3
        # Should be sorted by relevance score (highest first)
        assert answer.citations[0].page_number == 5  # 0.95
        assert answer.citations[1].page_number == 12  # 0.88
        assert answer.citations[2].page_number == 18  # 0.82

    def test_structured_answer_reasoning_steps_sequential(self):
        """Test that reasoning steps must be sequential."""
        step1 = ReasoningStep(step_number=1, thought="First", conclusion="First conclusion")
        step3 = ReasoningStep(step_number=3, thought="Third", conclusion="Third conclusion")  # Skip step 2

        with pytest.raises(ValidationError, match="Reasoning steps must be sequential"):
            StructuredAnswer(
                answer="Answer",
                confidence=0.9,
                citations=[],
                reasoning_steps=[step1, step3],
                format_type=FormatType.COT_REASONING,
            )


class TestStructuredOutputConfig:
    """Test cases for StructuredOutputConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = StructuredOutputConfig()
        assert config.enabled is False
        assert config.format_type == FormatType.STANDARD
        assert config.include_reasoning is False
        assert config.max_citations == 5
        assert config.min_confidence == 0.0
        assert config.validation_strict is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = StructuredOutputConfig(
            enabled=True,
            format_type=FormatType.COT_REASONING,
            include_reasoning=True,
            max_citations=10,
            min_confidence=0.6,
            validation_strict=False,
        )
        assert config.enabled is True
        assert config.format_type == FormatType.COT_REASONING
        assert config.include_reasoning is True
        assert config.max_citations == 10
        assert config.min_confidence == 0.6
        assert config.validation_strict is False

    def test_max_citations_bounds(self):
        """Test max_citations must be between 1 and 20."""
        # Test lower bound
        with pytest.raises(ValidationError):
            StructuredOutputConfig(max_citations=0)

        # Test upper bound
        with pytest.raises(ValidationError):
            StructuredOutputConfig(max_citations=21)

    def test_min_confidence_bounds(self):
        """Test min_confidence must be between 0.0 and 1.0."""
        # Test lower bound
        with pytest.raises(ValidationError):
            StructuredOutputConfig(min_confidence=-0.1)

        # Test upper bound
        with pytest.raises(ValidationError):
            StructuredOutputConfig(min_confidence=1.1)
