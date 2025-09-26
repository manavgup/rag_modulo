"""Unit tests for Chain of Thought Service following TDD Red Phase.

Tests the ChainOfThoughtService business logic without external dependencies.
These tests verify the core reasoning algorithms and service orchestration.
"""

from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from core.config import Settings
from core.custom_exceptions import LLMProviderError, ValidationError


class TestChainOfThoughtServiceTDD:
    """Test Chain of Thought Service using TDD Red Phase."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock(spec=Settings)
        settings.cot_max_depth = 5
        settings.cot_token_multiplier = 2.0
        settings.cot_evaluation_threshold = 0.6
        return settings

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service for testing."""
        mock = AsyncMock()
        # Ensure the mock has the generate_text method
        mock.generate_text = AsyncMock()
        return mock

    @pytest.fixture
    def mock_search_service(self):
        """Mock search service for testing."""
        return AsyncMock()

    @pytest.fixture
    def cot_service(self, mock_settings, mock_llm_service, mock_search_service):
        """Create ChainOfThoughtService instance for testing."""
        from rag_solution.services.chain_of_thought_service import ChainOfThoughtService  # type: ignore

        # Create a mock db session
        mock_db = MagicMock()

        return ChainOfThoughtService(
            settings=mock_settings, llm_service=mock_llm_service, search_service=mock_search_service, db=mock_db
        )

    async def test_cot_service_initialization(self, cot_service):
        """Test CoT service initializes correctly."""
        assert cot_service is not None
        assert hasattr(cot_service, "settings")
        assert hasattr(cot_service, "llm_service")
        assert hasattr(cot_service, "search_service")

    async def test_question_classification_simple_question(self, cot_service):
        """Test classification of simple question that doesn't require CoT."""
        question = "What is Python?"

        classification = await cot_service.classify_question(question)

        assert classification.question_type == "simple"
        assert classification.complexity_level == "low"
        assert classification.requires_cot is False
        assert classification.estimated_steps <= 1

    async def test_question_classification_complex_question(self, cot_service):
        """Test classification of complex question that requires CoT."""
        question = "How does machine learning differ from deep learning, and what are the practical applications of each in healthcare and finance?"

        classification = await cot_service.classify_question(question)

        assert classification.question_type == "multi_part"
        assert classification.complexity_level in ["high", "very_high"]
        assert classification.requires_cot is True
        assert classification.estimated_steps >= 3

    async def test_question_classification_comparison_question(self, cot_service):
        """Test classification of comparison-based question."""
        question = "Compare and contrast supervised and unsupervised learning algorithms"

        classification = await cot_service.classify_question(question)

        assert classification.question_type == "comparison"
        assert classification.requires_cot is True
        assert classification.confidence > 0.7

    async def test_question_decomposition_multi_part_question(self, cot_service):
        """Test decomposition of multi-part question into sub-questions."""
        question = "What is machine learning and how does it work in practice?"

        decomposition = await cot_service.decompose_question(question)

        assert len(decomposition.sub_questions) >= 2
        assert any("what is machine learning" in sq.sub_question.lower() for sq in decomposition.sub_questions)
        assert any("how does it work" in sq.sub_question.lower() for sq in decomposition.sub_questions)

        # Check ordering and dependencies
        for i, sub_q in enumerate(decomposition.sub_questions):
            assert sub_q.reasoning_step == i + 1
            if i > 0:
                assert len(sub_q.dependency_indices) > 0

    async def test_question_decomposition_causal_question(self, cot_service):
        """Test decomposition of causal reasoning question."""
        question = "Why does regularization prevent overfitting in neural networks?"

        decomposition = await cot_service.decompose_question(question)

        assert len(decomposition.sub_questions) >= 2
        # Should break down into definition and causal components
        definition_questions = [sq for sq in decomposition.sub_questions if sq.question_type == "definition"]
        causal_questions = [sq for sq in decomposition.sub_questions if sq.question_type == "causal"]

        assert len(definition_questions) > 0
        assert len(causal_questions) > 0

    async def test_iterative_reasoning_execution(self, cot_service, mock_search_service):
        """Test iterative reasoning execution with context preservation."""
        from rag_solution.schemas.chain_of_thought_schema import (  # type: ignore
            ChainOfThoughtInput,
        )

        # Setup mock search results
        mock_search_service.search_documents.return_value = {
            "documents": ["Machine learning definition", "ML applications"],
            "relevance_scores": [0.9, 0.8],
        }

        cot_input = ChainOfThoughtInput(
            question="What is machine learning and what are its applications?",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={"enabled": True, "max_reasoning_depth": 3, "reasoning_strategy": "iterative"},
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        assert result.original_question == cot_input.question
        assert len(result.reasoning_steps) >= 2
        assert result.final_answer is not None
        assert result.total_confidence > 0
        assert result.reasoning_strategy == "iterative"

    async def test_decomposition_reasoning_strategy(self, cot_service):
        """Test decomposition reasoning strategy."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput  # type: ignore

        cot_input = ChainOfThoughtInput(
            question="Compare machine learning and artificial intelligence",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={"enabled": True, "reasoning_strategy": "decomposition"},
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        assert result.reasoning_strategy == "decomposition"
        # Should have steps for defining each concept and then comparing
        assert len(result.reasoning_steps) >= 3

    async def test_context_preservation_across_steps(self, cot_service):
        """Test context preservation across reasoning steps."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput  # type: ignore

        cot_input = ChainOfThoughtInput(
            question="How does backpropagation work and why is it important?",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={"enabled": True, "context_preservation": True},
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        # Verify that later steps reference earlier step outputs
        if len(result.reasoning_steps) > 1:
            later_steps = result.reasoning_steps[1:]
            for step in later_steps:
                # Context should include information from previous steps
                assert len(step.context_used) > 0

    async def test_token_budget_management(self, cot_service, mock_settings):
        """Test token budget management with multiplier."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput  # type: ignore

        mock_settings.cot_token_multiplier = 2.5

        cot_input = ChainOfThoughtInput(
            question="Complex question requiring multiple reasoning steps",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={"enabled": True, "token_budget_multiplier": 3.0},
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        # Should track token usage
        assert result.token_usage is not None
        assert result.token_usage > 0

    async def test_confidence_aggregation(self, cot_service):
        """Test confidence score aggregation across reasoning steps."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput  # type: ignore

        cot_input = ChainOfThoughtInput(
            question="Multi-step question for confidence testing",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={"enabled": True},
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        assert 0 <= result.total_confidence <= 1
        # Total confidence should be reasonable aggregation of step confidences
        if result.reasoning_steps:
            step_confidences = [
                step.confidence_score for step in result.reasoning_steps if step.confidence_score is not None
            ]
            if step_confidences:
                avg_confidence = sum(step_confidences) / len(step_confidences)
                # Total confidence should be within reasonable range of average
                assert abs(result.total_confidence - avg_confidence) <= 0.3

    async def test_cot_disabled_fallback(self, cot_service, mock_search_service):
        """Test fallback to regular search when CoT is disabled."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput  # type: ignore

        mock_search_service.search.return_value = {
            "answer": "Regular search result",
            "documents": [],
            "execution_time": 1.0,
        }

        cot_input = ChainOfThoughtInput(
            question="Simple question", collection_id=uuid4(), user_id=uuid4(), cot_config={"enabled": False}
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        # Should fallback to regular search
        assert len(result.reasoning_steps) == 0
        assert result.final_answer == "Regular search result"

    async def test_max_depth_enforcement(self, cot_service, mock_settings):
        """Test enforcement of maximum reasoning depth."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput  # type: ignore

        mock_settings.cot_max_depth = 2

        cot_input = ChainOfThoughtInput(
            question="Very complex question that could generate many steps",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={
                "enabled": True,
                "max_reasoning_depth": 5,  # Higher than settings limit
            },
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        # Should respect settings limit
        assert len(result.reasoning_steps) <= 2

    async def test_evaluation_threshold_filtering(self, cot_service, mock_settings):
        """Test filtering of low-confidence reasoning steps."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput  # type: ignore

        mock_settings.cot_evaluation_threshold = 0.8

        cot_input = ChainOfThoughtInput(
            question="Question that may produce low-confidence steps",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={"enabled": True},
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        # All reasoning steps should meet confidence threshold
        for step in result.reasoning_steps:
            if step.confidence_score is not None:
                assert step.confidence_score >= 0.6  # Some tolerance

    async def test_error_handling_llm_failure(self, cot_service, mock_llm_service):
        """Test error handling when LLM service fails."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput  # type: ignore

        mock_llm_service.generate_text.side_effect = LLMProviderError("LLM service unavailable")

        user_id = uuid4()
        cot_input = ChainOfThoughtInput(
            question="Test question", collection_id=uuid4(), user_id=user_id, cot_config={"enabled": True}
        )

        with pytest.raises(LLMProviderError):
            await cot_service.execute_chain_of_thought(cot_input, user_id=str(user_id))

    async def test_error_handling_invalid_configuration(self, cot_service):
        """Test error handling for invalid CoT configuration."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput  # type: ignore

        cot_input = ChainOfThoughtInput(
            question="Test question",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={
                "enabled": True,
                "max_reasoning_depth": -1,  # Invalid
            },
        )

        with pytest.raises(ValidationError):
            await cot_service.execute_chain_of_thought(cot_input)

    async def test_reasoning_step_execution_time_tracking(self, cot_service):
        """Test execution time tracking for individual reasoning steps."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput  # type: ignore

        cot_input = ChainOfThoughtInput(
            question="Question requiring multiple steps",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={"enabled": True},
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        # Should track execution time for each step
        for step in result.reasoning_steps:
            assert step.execution_time is not None
            assert step.execution_time > 0

        # Total execution time should be sum of step times
        step_times = [step.execution_time for step in result.reasoning_steps if step.execution_time is not None]
        if step_times:
            assert result.total_execution_time >= sum(step_times)


class TestQuestionDecomposerTDD:
    """Test Question Decomposer component using TDD Red Phase."""

    @pytest.fixture
    def question_decomposer(self):
        """Create QuestionDecomposer instance for testing."""
        from rag_solution.services.question_decomposer import QuestionDecomposer  # type: ignore

        mock_llm_service = AsyncMock()
        return QuestionDecomposer(llm_service=mock_llm_service)

    async def test_decomposer_initialization(self, question_decomposer):
        """Test question decomposer initializes correctly."""
        assert question_decomposer is not None
        assert hasattr(question_decomposer, "llm_service")

    async def test_simple_question_no_decomposition(self, question_decomposer):
        """Test simple question returns single sub-question."""
        question = "What is Python?"

        result = await question_decomposer.decompose(question)

        assert len(result.sub_questions) == 1
        assert result.sub_questions[0].sub_question == question
        assert result.sub_questions[0].question_type == "definition"

    async def test_multi_part_question_decomposition(self, question_decomposer):
        """Test multi-part question gets properly decomposed."""
        question = "What is machine learning and how is it different from artificial intelligence?"

        result = await question_decomposer.decompose(question)

        assert len(result.sub_questions) >= 2
        # Should have definition and comparison components
        question_types = [sq.question_type for sq in result.sub_questions]
        assert "definition" in question_types
        assert "comparison" in question_types

    async def test_causal_question_decomposition(self, question_decomposer):
        """Test causal question decomposition."""
        question = "Why does regularization prevent overfitting in neural networks?"

        result = await question_decomposer.decompose(question)

        assert len(result.sub_questions) >= 2
        # Should break down causal chain
        causal_steps = [sq for sq in result.sub_questions if sq.question_type == "causal"]
        assert len(causal_steps) > 0

    async def test_dependency_tracking(self, question_decomposer):
        """Test dependency tracking between sub-questions."""
        question = "How does backpropagation work and why is it effective for training neural networks?"

        result = await question_decomposer.decompose(question)

        # Later questions should depend on earlier ones
        for i, sub_q in enumerate(result.sub_questions[1:], 1):
            assert len(sub_q.dependency_indices) > 0
            # Dependencies should reference earlier steps
            for dep_idx in sub_q.dependency_indices:
                assert dep_idx < i

    async def test_complexity_scoring(self, question_decomposer):
        """Test complexity scoring for sub-questions."""
        question = "Compare supervised and unsupervised learning algorithms and their use cases"

        result = await question_decomposer.decompose(question)

        for sub_q in result.sub_questions:
            assert 0 <= sub_q.complexity_score <= 1
            # Comparison questions should have higher complexity
            if sub_q.question_type == "comparison":
                assert sub_q.complexity_score > 0.5

    async def test_question_type_classification(self, question_decomposer):
        """Test accurate question type classification."""
        test_cases = [
            ("What is machine learning?", "definition"),
            ("How does gradient descent work?", "procedural"),
            ("Why is regularization important?", "causal"),
            ("Compare CNN and RNN architectures", "comparison"),
            ("Analyze the impact of dropout on model performance", "analytical"),
        ]

        for question, expected_type in test_cases:
            result = await question_decomposer.decompose(question)
            question_types = [sq.question_type for sq in result.sub_questions]
            assert expected_type in question_types


class TestAnswerSynthesizerTDD:
    """Test Answer Synthesizer component using TDD Red Phase."""

    @pytest.fixture
    def answer_synthesizer(self):
        """Create AnswerSynthesizer instance for testing."""
        from rag_solution.services.answer_synthesizer import AnswerSynthesizer  # type: ignore

        mock_llm_service = AsyncMock()
        return AnswerSynthesizer(llm_service=mock_llm_service)

    async def test_synthesizer_initialization(self, answer_synthesizer):
        """Test answer synthesizer initializes correctly."""
        assert answer_synthesizer is not None
        assert hasattr(answer_synthesizer, "llm_service")

    async def test_single_step_synthesis(self, answer_synthesizer):
        """Test synthesis from single reasoning step."""
        from rag_solution.schemas.chain_of_thought_schema import ReasoningStep  # type: ignore

        original_question = "What is machine learning?"
        reasoning_steps = [
            ReasoningStep(
                step_number=1,
                question="What is machine learning?",
                intermediate_answer="Machine learning is a subset of AI that enables computers to learn without explicit programming",
                confidence_score=0.9,
            )
        ]

        result = await answer_synthesizer.synthesize_answer(original_question, reasoning_steps)

        assert result.final_answer is not None
        assert len(result.final_answer) > 0
        assert result.total_confidence > 0

    async def test_multi_step_synthesis(self, answer_synthesizer):
        """Test synthesis from multiple reasoning steps."""
        from rag_solution.schemas.chain_of_thought_schema import ReasoningStep  # type: ignore

        original_question = "What is machine learning and how does it work?"
        reasoning_steps = [
            ReasoningStep(
                step_number=1,
                question="What is machine learning?",
                intermediate_answer="Machine learning is a subset of AI",
                confidence_score=0.9,
            ),
            ReasoningStep(
                step_number=2,
                question="How does machine learning work?",
                intermediate_answer="It works by training algorithms on data",
                confidence_score=0.8,
            ),
        ]

        result = await answer_synthesizer.synthesize_answer(original_question, reasoning_steps)

        assert result.final_answer is not None
        # Should incorporate information from both steps
        assert "machine learning" in result.final_answer.lower()
        assert "training" in result.final_answer.lower() or "algorithms" in result.final_answer.lower()

    async def test_confidence_aggregation_synthesis(self, answer_synthesizer):
        """Test confidence score aggregation during synthesis."""
        from rag_solution.schemas.chain_of_thought_schema import ReasoningStep  # type: ignore

        reasoning_steps = [
            ReasoningStep(step_number=1, question="Q1", intermediate_answer="A1", confidence_score=0.9),
            ReasoningStep(step_number=2, question="Q2", intermediate_answer="A2", confidence_score=0.7),
            ReasoningStep(step_number=3, question="Q3", intermediate_answer="A3", confidence_score=0.8),
        ]

        result = await answer_synthesizer.synthesize_answer("Test question", reasoning_steps)

        # Total confidence should be reasonable aggregation
        expected_range = (0.7, 0.9)  # Between min and max step confidence
        assert expected_range[0] <= result.total_confidence <= expected_range[1]

    async def test_synthesis_with_context_preservation(self, answer_synthesizer):
        """Test synthesis preserves context across reasoning steps."""
        from rag_solution.schemas.chain_of_thought_schema import ReasoningStep  # type: ignore

        reasoning_steps = [
            ReasoningStep(
                step_number=1,
                question="Define neural networks",
                intermediate_answer="Neural networks are computational models inspired by biological neurons",
                context_used=["Document about neural network basics"],
                confidence_score=0.9,
            ),
            ReasoningStep(
                step_number=2,
                question="How do neural networks learn?",
                intermediate_answer="They learn through backpropagation and gradient descent",
                context_used=["Document about training algorithms", "Previous step answer"],
                confidence_score=0.8,
            ),
        ]

        result = await answer_synthesizer.synthesize_answer(
            "What are neural networks and how do they learn?", reasoning_steps
        )

        # Should create coherent answer combining both steps
        assert "neural networks" in result.final_answer.lower()
        assert "backpropagation" in result.final_answer.lower() or "gradient descent" in result.final_answer.lower()

    async def test_synthesis_handles_missing_confidence(self, answer_synthesizer):
        """Test synthesis handles missing confidence scores gracefully."""
        from rag_solution.schemas.chain_of_thought_schema import ReasoningStep  # type: ignore

        reasoning_steps = [
            ReasoningStep(
                step_number=1,
                question="Q1",
                intermediate_answer="A1",
                confidence_score=None,  # Missing confidence
            ),
            ReasoningStep(step_number=2, question="Q2", intermediate_answer="A2", confidence_score=0.8),
        ]

        result = await answer_synthesizer.synthesize_answer("Test question", reasoning_steps)

        # Should still produce valid result
        assert result.final_answer is not None
        assert 0 <= result.total_confidence <= 1

    async def test_synthesis_empty_steps_fallback(self, answer_synthesizer):
        """Test synthesis handles empty reasoning steps."""
        result = await answer_synthesizer.synthesize_answer("Test question", [])

        # Should provide fallback response
        assert result.final_answer is not None
        assert result.total_confidence >= 0
