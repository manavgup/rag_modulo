"""Unit tests for AnswerSynthesizer."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from backend.rag_solution.schemas.chain_of_thought_schema import ReasoningStep, SynthesisResult
from backend.rag_solution.services.answer_synthesizer import AnswerSynthesizer


class TestAnswerSynthesizer:
    """Test cases for AnswerSynthesizer."""

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create a mock LLM service."""
        return Mock()

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create mock settings."""
        settings = Mock()
        settings.llm_provider = "openai"
        return settings

    @pytest.fixture
    def synthesizer(self, mock_llm_service: Mock, mock_settings: Mock) -> AnswerSynthesizer:
        """Create an AnswerSynthesizer instance with mocked dependencies."""
        return AnswerSynthesizer(llm_service=mock_llm_service, settings=mock_settings)

    @pytest.fixture
    def synthesizer_no_llm(self) -> AnswerSynthesizer:
        """Create an AnswerSynthesizer without LLM service."""
        return AnswerSynthesizer()

    @pytest.fixture
    def sample_reasoning_steps(self) -> list[ReasoningStep]:
        """Create sample reasoning steps."""
        return [
            ReasoningStep(
                step_number=1,
                question="First step question",
                intermediate_answer="First answer",
                confidence_score=0.8
            ),
            ReasoningStep(
                step_number=2,
                question="Second step question",
                intermediate_answer="Second answer",
                confidence_score=0.9
            )
        ]

    def test_init_with_llm_service(self, mock_llm_service: Mock, mock_settings: Mock) -> None:
        """Test AnswerSynthesizer initialization with LLM service."""
        synthesizer = AnswerSynthesizer(llm_service=mock_llm_service, settings=mock_settings)
        assert synthesizer.llm_service == mock_llm_service
        assert synthesizer.settings == mock_settings

    def test_init_without_llm_service(self) -> None:
        """Test AnswerSynthesizer initialization without LLM service."""
        synthesizer = AnswerSynthesizer()
        assert synthesizer.llm_service is None
        assert synthesizer.settings is not None

    def test_synthesize_no_steps(self, synthesizer: AnswerSynthesizer) -> None:
        """Test synthesis with no reasoning steps."""
        result = synthesizer.synthesize("test question", [])
        assert result == "Unable to generate an answer due to insufficient information."

    def test_synthesize_no_intermediate_answers(self, synthesizer: AnswerSynthesizer) -> None:
        """Test synthesis with steps but no intermediate answers."""
        steps = [
            ReasoningStep(step_number=1, question="test question", intermediate_answer="", confidence_score=0.5)
        ]
        result = synthesizer.synthesize("test question", steps)
        assert result == "Unable to synthesize an answer from the reasoning steps."

    def test_synthesize_single_answer(self, synthesizer: AnswerSynthesizer) -> None:
        """Test synthesis with single intermediate answer."""
        steps = [
            ReasoningStep(
                step_number=1,
                question="test question",
                intermediate_answer="Single answer",
                confidence_score=0.8
            )
        ]
        result = synthesizer.synthesize("test question", steps)
        assert result == "Single answer"

    def test_synthesize_multiple_answers(self, synthesizer: AnswerSynthesizer, sample_reasoning_steps: list[ReasoningStep]) -> None:
        """Test synthesis with multiple intermediate answers."""
        result = synthesizer.synthesize("test question", sample_reasoning_steps)
        expected = "Based on the analysis of test question: First answer Additionally, second answer"
        assert result == expected

    def test_synthesize_three_answers(self, synthesizer: AnswerSynthesizer) -> None:
        """Test synthesis with three intermediate answers."""
        steps = [
            ReasoningStep(step_number=1, question="test1", intermediate_answer="First", confidence_score=0.8),
            ReasoningStep(step_number=2, question="test2", intermediate_answer="Second", confidence_score=0.9),
            ReasoningStep(step_number=3, question="test3", intermediate_answer="Third", confidence_score=0.7)
        ]
        result = synthesizer.synthesize("test question", steps)
        expected = "Based on the analysis of test question: First Furthermore, second Additionally, third"
        assert result == expected

    @pytest.mark.asyncio
    async def test_synthesize_answer_success(self, synthesizer: AnswerSynthesizer, sample_reasoning_steps: list[ReasoningStep]) -> None:
        """Test synthesize_answer method with successful synthesis."""
        result = await synthesizer.synthesize_answer("test question", sample_reasoning_steps)

        assert isinstance(result, SynthesisResult)
        assert result.final_answer == "Based on the analysis of test question: First answer Additionally, second answer"
        assert abs(result.total_confidence - 0.85) < 0.001  # (0.8 + 0.9) / 2

    @pytest.mark.asyncio
    async def test_synthesize_answer_no_confidence_scores(self, synthesizer: AnswerSynthesizer) -> None:
        """Test synthesize_answer with no confidence scores."""
        steps = [
            ReasoningStep(step_number=1, question="test question", intermediate_answer="Answer", confidence_score=None)
        ]
        result = await synthesizer.synthesize_answer("test question", steps)

        assert isinstance(result, SynthesisResult)
        assert result.final_answer == "Answer"
        assert result.total_confidence == 0.5  # Default when no confidence scores

    @pytest.mark.asyncio
    async def test_synthesize_answer_empty_steps(self, synthesizer: AnswerSynthesizer) -> None:
        """Test synthesize_answer with empty steps."""
        result = await synthesizer.synthesize_answer("test question", [])

        assert isinstance(result, SynthesisResult)
        assert result.final_answer == "Unable to generate an answer due to insufficient information."
        assert result.total_confidence == 0.5  # Default when no confidence scores

    @pytest.mark.asyncio
    async def test_refine_answer_no_llm_service(self, synthesizer_no_llm: AnswerSynthesizer) -> None:
        """Test refine_answer without LLM service."""
        result = await synthesizer_no_llm.refine_answer("test answer", ["context"])
        assert result == "test answer"

    @pytest.mark.asyncio
    async def test_refine_answer_no_context(self, synthesizer: AnswerSynthesizer) -> None:
        """Test refine_answer without context."""
        result = await synthesizer.refine_answer("test answer", [])
        assert result == "test answer"

    @pytest.mark.asyncio
    async def test_refine_answer_success(self, synthesizer: AnswerSynthesizer) -> None:
        """Test successful answer refinement."""
        # Mock the LLM service
        synthesizer.llm_service.generate_text = AsyncMock(return_value="Refined answer")

        result = await synthesizer.refine_answer("test answer", ["context1", "context2"], str(uuid4()))

        assert result == "Refined answer"
        synthesizer.llm_service.generate_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_refine_answer_invalid_user_id(self, synthesizer: AnswerSynthesizer) -> None:
        """Test refine_answer with invalid user ID."""
        result = await synthesizer.refine_answer("test answer", ["context"], "invalid-uuid")
        assert result == "test answer"

    @pytest.mark.asyncio
    async def test_refine_answer_no_user_id(self, synthesizer: AnswerSynthesizer) -> None:
        """Test refine_answer without user ID."""
        result = await synthesizer.refine_answer("test answer", ["context"], None)
        assert result == "test answer"

    @pytest.mark.asyncio
    async def test_refine_answer_exception(self, synthesizer: AnswerSynthesizer) -> None:
        """Test refine_answer with exception."""
        # Mock the LLM service to raise exception
        synthesizer.llm_service.generate_text = AsyncMock(side_effect=Exception("LLM error"))

        result = await synthesizer.refine_answer("test answer", ["context"], str(uuid4()))

        # Should return original answer on exception
        assert result == "test answer"

    @pytest.mark.asyncio
    async def test_refine_answer_no_generate_text_method(self, synthesizer: AnswerSynthesizer) -> None:
        """Test refine_answer when LLM service doesn't have generate_text method."""
        # Remove generate_text method
        del synthesizer.llm_service.generate_text

        result = await synthesizer.refine_answer("test answer", ["context"], str(uuid4()))

        # Should return original answer
        assert result == "test answer"

    @pytest.mark.asyncio
    async def test_refine_answer_non_string_response(self, synthesizer: AnswerSynthesizer) -> None:
        """Test refine_answer with non-string LLM response."""
        # Mock the LLM service to return non-string
        synthesizer.llm_service.generate_text = AsyncMock(return_value=123)

        result = await synthesizer.refine_answer("test answer", ["context"], str(uuid4()))

        assert result == "123"  # Should convert to string

    def test_synthesize_with_empty_intermediate_answers(self, synthesizer: AnswerSynthesizer) -> None:
        """Test synthesis with steps containing empty intermediate answers."""
        steps = [
            ReasoningStep(step_number=1, question="test1", intermediate_answer="", confidence_score=0.8),
            ReasoningStep(step_number=2, question="test2", intermediate_answer="Valid answer", confidence_score=0.9),
            ReasoningStep(step_number=3, question="test3", intermediate_answer="", confidence_score=0.7)
        ]
        result = synthesizer.synthesize("test question", steps)
        assert result == "Valid answer"  # Should only use non-empty answers

    def test_synthesize_with_none_intermediate_answers(self, synthesizer: AnswerSynthesizer) -> None:
        """Test synthesis with steps containing None intermediate answers."""
        steps = [
            ReasoningStep(step_number=1, question="test1", intermediate_answer=None, confidence_score=0.8),
            ReasoningStep(step_number=2, question="test2", intermediate_answer="Valid answer", confidence_score=0.9)
        ]
        result = synthesizer.synthesize("test question", steps)
        assert result == "Valid answer"  # Should only use non-None answers
