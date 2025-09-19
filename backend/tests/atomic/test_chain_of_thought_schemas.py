"""Atomic tests for Chain of Thought (CoT) schemas and data structures.

Tests the fundamental data structures and validation logic for CoT reasoning
without external dependencies. These tests verify schema definitions, validation rules,
and data transformations at the most granular level.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError


class TestChainOfThoughtConfigSchema:
    """Test Chain of Thought configuration schema validation."""

    def test_cot_config_schema_creation_with_valid_data(self):
        """Test creation of CoT config schema with valid data."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtConfig  # type: ignore  # type: ignore

        config_data = {
            "enabled": True,
            "max_reasoning_depth": 3,
            "reasoning_strategy": "decomposition",
            "context_preservation": True,
            "token_budget_multiplier": 2.5,
            "evaluation_threshold": 0.7,
        }

        config = ChainOfThoughtConfig(**config_data)

        assert config.enabled is True
        assert config.max_reasoning_depth == 3
        assert config.reasoning_strategy == "decomposition"
        assert config.context_preservation is True
        assert config.token_budget_multiplier == 2.5
        assert config.evaluation_threshold == 0.7

    def test_cot_config_schema_with_default_values(self):
        """Test CoT config schema uses appropriate default values."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtConfig

        config = ChainOfThoughtConfig()

        assert config.enabled is False
        assert config.max_reasoning_depth == 3
        assert config.reasoning_strategy == "decomposition"
        assert config.context_preservation is True
        assert config.token_budget_multiplier == 2.0
        assert config.evaluation_threshold == 0.6

    def test_cot_config_schema_validation_max_depth_positive(self):
        """Test max_reasoning_depth must be positive."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtConfig

        with pytest.raises(ValidationError) as exc_info:
            ChainOfThoughtConfig(max_reasoning_depth=0)

        assert "greater than 0" in str(exc_info.value)

    def test_cot_config_schema_validation_token_multiplier_positive(self):
        """Test token_budget_multiplier must be positive."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtConfig

        with pytest.raises(ValidationError) as exc_info:
            ChainOfThoughtConfig(token_budget_multiplier=0)

        assert "greater than 0" in str(exc_info.value)

    def test_cot_config_schema_validation_threshold_range(self):
        """Test evaluation_threshold must be between 0 and 1."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtConfig

        # Test lower bound
        with pytest.raises(ValidationError) as exc_info:
            ChainOfThoughtConfig(evaluation_threshold=-0.1)
        assert "between 0 and 1" in str(exc_info.value)

        # Test upper bound
        with pytest.raises(ValidationError) as exc_info:
            ChainOfThoughtConfig(evaluation_threshold=1.1)
        assert "between 0 and 1" in str(exc_info.value)

    def test_cot_config_schema_valid_reasoning_strategies(self):
        """Test valid reasoning strategy values."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtConfig

        valid_strategies = ["decomposition", "iterative", "hierarchical", "causal"]

        for strategy in valid_strategies:
            config = ChainOfThoughtConfig(reasoning_strategy=strategy)
            assert config.reasoning_strategy == strategy

    def test_cot_config_schema_invalid_reasoning_strategy(self):
        """Test invalid reasoning strategy raises validation error."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtConfig

        with pytest.raises(ValidationError) as exc_info:
            ChainOfThoughtConfig(reasoning_strategy="invalid_strategy")

        assert "must be one of" in str(exc_info.value)


class TestQuestionDecompositionSchema:
    """Test question decomposition schema validation."""

    def test_decomposed_question_schema_creation(self):
        """Test creation of decomposed question schema."""
        from rag_solution.schemas.chain_of_thought_schema import DecomposedQuestion

        question_data = {
            "sub_question": "What is machine learning?",
            "reasoning_step": 1,
            "dependency_indices": [0],
            "question_type": "definition",
            "complexity_score": 0.3,
        }

        question = DecomposedQuestion(**question_data)

        assert question.sub_question == "What is machine learning?"
        assert question.reasoning_step == 1
        assert question.dependency_indices == [0]
        assert question.question_type == "definition"
        assert question.complexity_score == 0.3

    def test_decomposed_question_schema_complexity_range(self):
        """Test complexity_score must be between 0 and 1."""
        from rag_solution.schemas.chain_of_thought_schema import DecomposedQuestion

        # Test lower bound
        with pytest.raises(ValidationError) as exc_info:
            DecomposedQuestion(sub_question="test", reasoning_step=1, complexity_score=-0.1)
        assert "between 0 and 1" in str(exc_info.value)

        # Test upper bound
        with pytest.raises(ValidationError) as exc_info:
            DecomposedQuestion(sub_question="test", reasoning_step=1, complexity_score=1.1)
        assert "between 0 and 1" in str(exc_info.value)

    def test_decomposed_question_schema_valid_question_types(self):
        """Test valid question type values."""
        from rag_solution.schemas.chain_of_thought_schema import DecomposedQuestion

        valid_types = ["definition", "comparison", "causal", "procedural", "analytical"]

        for q_type in valid_types:
            question = DecomposedQuestion(sub_question="test question", reasoning_step=1, question_type=q_type)
            assert question.question_type == q_type

    def test_decomposed_question_schema_step_positive(self):
        """Test reasoning_step must be positive."""
        from rag_solution.schemas.chain_of_thought_schema import DecomposedQuestion

        with pytest.raises(ValidationError) as exc_info:
            DecomposedQuestion(sub_question="test", reasoning_step=0)

        assert "greater than 0" in str(exc_info.value)


class TestReasoningStepSchema:
    """Test reasoning step schema validation."""

    def test_reasoning_step_schema_creation(self):
        """Test creation of reasoning step schema."""
        from rag_solution.schemas.chain_of_thought_schema import ReasoningStep

        step_data = {
            "step_number": 1,
            "question": "What is machine learning?",
            "context_used": ["Document 1 content", "Document 2 content"],
            "intermediate_answer": "Machine learning is a subset of AI...",
            "confidence_score": 0.85,
            "reasoning_trace": "First, I need to define machine learning...",
            "execution_time": 1.2,
        }

        step = ReasoningStep(**step_data)

        assert step.step_number == 1
        assert step.question == "What is machine learning?"
        assert len(step.context_used) == 2
        assert step.intermediate_answer == "Machine learning is a subset of AI..."
        assert step.confidence_score == 0.85
        assert step.reasoning_trace == "First, I need to define machine learning..."
        assert step.execution_time == 1.2

    def test_reasoning_step_schema_confidence_range(self):
        """Test confidence_score must be between 0 and 1."""
        from rag_solution.schemas.chain_of_thought_schema import ReasoningStep

        # Test lower bound
        with pytest.raises(ValidationError) as exc_info:
            ReasoningStep(step_number=1, question="test", confidence_score=-0.1)
        assert "between 0 and 1" in str(exc_info.value)

        # Test upper bound
        with pytest.raises(ValidationError) as exc_info:
            ReasoningStep(step_number=1, question="test", confidence_score=1.1)
        assert "between 0 and 1" in str(exc_info.value)

    def test_reasoning_step_schema_step_number_positive(self):
        """Test step_number must be positive."""
        from rag_solution.schemas.chain_of_thought_schema import ReasoningStep

        with pytest.raises(ValidationError) as exc_info:
            ReasoningStep(step_number=0, question="test")

        assert "greater than 0" in str(exc_info.value)

    def test_reasoning_step_schema_execution_time_positive(self):
        """Test execution_time must be positive when provided."""
        from rag_solution.schemas.chain_of_thought_schema import ReasoningStep

        with pytest.raises(ValidationError) as exc_info:
            ReasoningStep(step_number=1, question="test", execution_time=-1.0)

        assert "greater than 0" in str(exc_info.value)


class TestChainOfThoughtOutputSchema:
    """Test Chain of Thought output schema validation."""

    def test_cot_output_schema_creation(self):
        """Test creation of CoT output schema."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtOutput, ReasoningStep  # type: ignore

        step1 = ReasoningStep(
            step_number=1,
            question="What is machine learning?",
            context_used=["Document 1"],
            intermediate_answer="ML is a subset of AI",
            confidence_score=0.8,
        )

        step2 = ReasoningStep(
            step_number=2,
            question="How does ML relate to data science?",
            context_used=["Document 2"],
            intermediate_answer="ML is a core component of data science",
            confidence_score=0.9,
        )

        output_data = {
            "original_question": "What is machine learning and how does it relate to data science?",
            "final_answer": "Machine learning is a subset of AI that is a core component of data science...",
            "reasoning_steps": [step1, step2],
            "total_confidence": 0.85,
            "token_usage": 1250,
            "total_execution_time": 3.5,
            "reasoning_strategy": "decomposition",
        }

        output = ChainOfThoughtOutput(**output_data)

        assert output.original_question == "What is machine learning and how does it relate to data science?"
        assert output.final_answer == "Machine learning is a subset of AI that is a core component of data science..."
        assert len(output.reasoning_steps) == 2
        assert output.total_confidence == 0.85
        assert output.token_usage == 1250
        assert output.total_execution_time == 3.5
        assert output.reasoning_strategy == "decomposition"

    def test_cot_output_schema_confidence_range(self):
        """Test total_confidence must be between 0 and 1."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtOutput

        # Test lower bound
        with pytest.raises(ValidationError) as exc_info:
            ChainOfThoughtOutput(
                original_question="test", final_answer="test", reasoning_steps=[], total_confidence=-0.1
            )
        assert "between 0 and 1" in str(exc_info.value)

        # Test upper bound
        with pytest.raises(ValidationError) as exc_info:
            ChainOfThoughtOutput(
                original_question="test", final_answer="test", reasoning_steps=[], total_confidence=1.1
            )
        assert "between 0 and 1" in str(exc_info.value)

    def test_cot_output_schema_token_usage_positive(self):
        """Test token_usage must be positive when provided."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtOutput

        with pytest.raises(ValidationError) as exc_info:
            ChainOfThoughtOutput(original_question="test", final_answer="test", reasoning_steps=[], token_usage=-100)

        assert "greater than 0" in str(exc_info.value)

    def test_cot_output_schema_execution_time_positive(self):
        """Test total_execution_time must be positive when provided."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtOutput

        with pytest.raises(ValidationError) as exc_info:
            ChainOfThoughtOutput(
                original_question="test", final_answer="test", reasoning_steps=[], total_execution_time=-1.0
            )

        assert "greater than 0" in str(exc_info.value)


class TestChainOfThoughtInputSchema:
    """Test Chain of Thought input schema validation."""

    def test_cot_input_schema_creation(self):
        """Test creation of CoT input schema."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput

        input_data = {
            "question": "What is machine learning and how does it work?",
            "collection_id": uuid4(),
            "user_id": uuid4(),
            "cot_config": {"enabled": True, "max_reasoning_depth": 4, "reasoning_strategy": "iterative"},
            "context_metadata": {"document_types": ["research_paper", "tutorial"], "domain": "artificial_intelligence"},
        }

        cot_input = ChainOfThoughtInput(**input_data)

        assert cot_input.question == "What is machine learning and how does it work?"
        assert str(cot_input.collection_id) == str(input_data["collection_id"])
        assert str(cot_input.user_id) == str(input_data["user_id"])
        assert cot_input.cot_config["enabled"] is True
        assert cot_input.cot_config["max_reasoning_depth"] == 4
        assert cot_input.context_metadata["domain"] == "artificial_intelligence"

    def test_cot_input_schema_with_minimal_data(self):
        """Test CoT input schema with minimal required data."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput

        input_data = {"question": "What is AI?", "collection_id": uuid4(), "user_id": uuid4()}

        cot_input = ChainOfThoughtInput(**input_data)

        assert cot_input.question == "What is AI?"
        assert cot_input.cot_config is None
        assert cot_input.context_metadata is None

    def test_cot_input_schema_question_not_empty(self):
        """Test question field cannot be empty."""
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput

        with pytest.raises(ValidationError) as exc_info:
            ChainOfThoughtInput(question="", collection_id=uuid4(), user_id=uuid4())

        assert "String should have at least 1 character" in str(exc_info.value)


class TestQuestionClassificationSchema:
    """Test question classification schema validation."""

    def test_question_classification_schema_creation(self):
        """Test creation of question classification schema."""
        from rag_solution.schemas.chain_of_thought_schema import QuestionClassification

        classification_data = {
            "question_type": "multi_part",
            "complexity_level": "high",
            "requires_cot": True,
            "estimated_steps": 3,
            "confidence": 0.92,
            "reasoning": "Question contains multiple concepts requiring decomposition",
        }

        classification = QuestionClassification(**classification_data)

        assert classification.question_type == "multi_part"
        assert classification.complexity_level == "high"
        assert classification.requires_cot is True
        assert classification.estimated_steps == 3
        assert classification.confidence == 0.92
        assert "decomposition" in classification.reasoning

    def test_question_classification_valid_types(self):
        """Test valid question type values."""
        from rag_solution.schemas.chain_of_thought_schema import QuestionClassification

        valid_types = ["simple", "multi_part", "comparison", "causal", "complex_analytical"]

        for q_type in valid_types:
            classification = QuestionClassification(question_type=q_type, complexity_level="medium", requires_cot=False)
            assert classification.question_type == q_type

    def test_question_classification_valid_complexity_levels(self):
        """Test valid complexity level values."""
        from rag_solution.schemas.chain_of_thought_schema import QuestionClassification

        valid_levels = ["low", "medium", "high", "very_high"]

        for level in valid_levels:
            classification = QuestionClassification(question_type="simple", complexity_level=level, requires_cot=False)
            assert classification.complexity_level == level

    def test_question_classification_confidence_range(self):
        """Test confidence must be between 0 and 1."""
        from rag_solution.schemas.chain_of_thought_schema import QuestionClassification

        # Test lower bound
        with pytest.raises(ValidationError) as exc_info:
            QuestionClassification(question_type="simple", complexity_level="low", requires_cot=False, confidence=-0.1)
        assert "between 0 and 1" in str(exc_info.value)

        # Test upper bound
        with pytest.raises(ValidationError) as exc_info:
            QuestionClassification(question_type="simple", complexity_level="low", requires_cot=False, confidence=1.1)
        assert "between 0 and 1" in str(exc_info.value)

    def test_question_classification_estimated_steps_positive(self):
        """Test estimated_steps must be positive when provided."""
        from rag_solution.schemas.chain_of_thought_schema import QuestionClassification

        with pytest.raises(ValidationError) as exc_info:
            QuestionClassification(
                question_type="simple", complexity_level="low", requires_cot=False, estimated_steps=0
            )

        assert "greater than 0" in str(exc_info.value)
