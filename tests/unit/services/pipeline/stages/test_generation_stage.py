"""
Unit tests for GenerationStage.

Tests the answer generation functionality including:
- Answer generation using LLM
- Answer generation using CoT result
- Answer cleaning
- Error handling
"""

from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtOutput, ReasoningStep
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline.search_context import SearchContext
from rag_solution.services.pipeline.stages.generation_stage import GenerationStage


@pytest.fixture
def mock_pipeline_service() -> Mock:
    """Create mock pipeline service."""
    service = Mock()
    service._validate_configuration = Mock()
    service._get_templates = Mock()
    service._format_context = Mock()
    service._generate_answer = Mock()
    return service


@pytest.fixture
def search_context_without_cot() -> SearchContext:
    """Create search context without CoT result."""
    user_id = uuid4()
    collection_id = uuid4()
    pipeline_id = uuid4()
    search_input = SearchInput(user_id=user_id, collection_id=collection_id, question="Test question?")
    context = SearchContext(search_input=search_input, user_id=user_id, collection_id=collection_id)
    context.pipeline_id = pipeline_id
    context.rewritten_query = "enhanced test question"

    # Add mock query results
    result1 = Mock()
    result1.chunk = Mock()
    result1.chunk.text = "Test document 1"

    context.query_results = [result1]
    return context


@pytest.fixture
def search_context_with_cot() -> SearchContext:
    """Create search context with CoT result."""
    user_id = uuid4()
    collection_id = uuid4()
    pipeline_id = uuid4()
    search_input = SearchInput(user_id=user_id, collection_id=collection_id, question="Complex question?")
    context = SearchContext(search_input=search_input, user_id=user_id, collection_id=collection_id)
    context.pipeline_id = pipeline_id

    # Add CoT output
    context.cot_output = ChainOfThoughtOutput(
        original_question="Complex question?",
        final_answer="This is the CoT-generated answer.",
        reasoning_steps=[
            ReasoningStep(
                step_number=1,
                question="Sub question",
                intermediate_answer="Intermediate answer",
                confidence_score=0.9,
            )
        ],
        total_confidence=0.9,
        token_usage=100,
        total_execution_time=1.5,
        reasoning_strategy="decomposition",
    )

    # Add mock query results
    result1 = Mock()
    result1.chunk = Mock()
    result1.chunk.text = "Test document 1"

    context.query_results = [result1]
    return context


@pytest.mark.unit
@pytest.mark.asyncio
class TestGenerationStage:
    """Test suite for GenerationStage."""

    async def test_stage_initialization(self, mock_pipeline_service: Mock) -> None:
        """Test that stage initializes correctly."""
        stage = GenerationStage(mock_pipeline_service)
        assert stage.stage_name == "Generation"
        assert stage.pipeline_service == mock_pipeline_service

    async def test_generation_with_llm(
        self, mock_pipeline_service: Mock, search_context_without_cot: SearchContext
    ) -> None:
        """Test answer generation using LLM."""
        # Setup mocks
        mock_pipeline_service._validate_configuration.return_value = (None, Mock(), Mock())
        mock_pipeline_service._get_templates.return_value = (Mock(id=uuid4()), None)
        mock_pipeline_service._format_context.return_value = "Formatted context"
        mock_pipeline_service._generate_answer.return_value = "Generated answer from LLM"

        stage = GenerationStage(mock_pipeline_service)
        result = await stage.execute(search_context_without_cot)

        assert result.success is True
        assert result.context.generated_answer == "Generated answer from LLM"
        assert "generation" in result.context.metadata
        assert result.context.metadata["generation"]["source"] == "llm"
        assert result.context.metadata["generation"]["answer_length"] == len("Generated answer from LLM")

        mock_pipeline_service._generate_answer.assert_called_once()

    async def test_generation_with_cot(
        self, mock_pipeline_service: Mock, search_context_with_cot: SearchContext
    ) -> None:
        """Test answer generation using CoT result."""
        stage = GenerationStage(mock_pipeline_service)
        result = await stage.execute(search_context_with_cot)

        assert result.success is True
        assert result.context.generated_answer == "This is the CoT-generated answer."
        assert "generation" in result.context.metadata
        assert result.context.metadata["generation"]["source"] == "cot"

        # LLM should not be called when CoT result is available
        mock_pipeline_service._generate_answer.assert_not_called()

    async def test_answer_cleaning_prefix_removal(
        self, mock_pipeline_service: Mock, search_context_without_cot: SearchContext
    ) -> None:
        """Test that answer prefixes are removed during cleaning."""
        mock_pipeline_service._validate_configuration.return_value = (None, Mock(), Mock())
        mock_pipeline_service._get_templates.return_value = (Mock(id=uuid4()), None)
        mock_pipeline_service._format_context.return_value = "Formatted context"
        mock_pipeline_service._generate_answer.return_value = "Answer: This is the actual answer"

        stage = GenerationStage(mock_pipeline_service)
        result = await stage.execute(search_context_without_cot)

        assert result.success is True
        assert result.context.generated_answer == "This is the actual answer"

    async def test_answer_cleaning_thinking_tags(
        self, mock_pipeline_service: Mock, search_context_without_cot: SearchContext
    ) -> None:
        """Test that thinking tags are removed during cleaning."""
        mock_pipeline_service._validate_configuration.return_value = (None, Mock(), Mock())
        mock_pipeline_service._get_templates.return_value = (Mock(id=uuid4()), None)
        mock_pipeline_service._format_context.return_value = "Formatted context"
        mock_pipeline_service._generate_answer.return_value = (
            "<thinking>Internal reasoning</thinking>This is the actual answer"
        )

        stage = GenerationStage(mock_pipeline_service)
        result = await stage.execute(search_context_without_cot)

        assert result.success is True
        assert "<thinking>" not in result.context.generated_answer
        assert "This is the actual answer" in result.context.generated_answer

    async def test_answer_cleaning_whitespace(
        self, mock_pipeline_service: Mock, search_context_without_cot: SearchContext
    ) -> None:
        """Test that extra whitespace is cleaned."""
        mock_pipeline_service._validate_configuration.return_value = (None, Mock(), Mock())
        mock_pipeline_service._get_templates.return_value = (Mock(id=uuid4()), None)
        mock_pipeline_service._format_context.return_value = "Formatted context"
        mock_pipeline_service._generate_answer.return_value = "  Answer\n\n\n\nwith    spaces  "

        stage = GenerationStage(mock_pipeline_service)
        result = await stage.execute(search_context_without_cot)

        assert result.success is True
        assert result.context.generated_answer == "Answer\n\nwith    spaces"

    async def test_missing_query_results(
        self, mock_pipeline_service: Mock, search_context_without_cot: SearchContext
    ) -> None:
        """Test error handling when query results are missing."""
        search_context_without_cot.query_results = None

        stage = GenerationStage(mock_pipeline_service)
        result = await stage.execute(search_context_without_cot)

        assert result.success is False
        assert result.error is not None
        assert "Query results not set" in result.error

    async def test_missing_pipeline_id(
        self, mock_pipeline_service: Mock, search_context_without_cot: SearchContext
    ) -> None:
        """Test error handling when pipeline ID is missing."""
        search_context_without_cot.pipeline_id = None

        stage = GenerationStage(mock_pipeline_service)
        result = await stage.execute(search_context_without_cot)

        assert result.success is False
        assert result.error is not None
        assert "Pipeline ID not set" in result.error

    async def test_generation_error_handling(
        self, mock_pipeline_service: Mock, search_context_without_cot: SearchContext
    ) -> None:
        """Test error handling during answer generation."""
        mock_pipeline_service._validate_configuration.side_effect = ValueError("Configuration error")

        stage = GenerationStage(mock_pipeline_service)
        result = await stage.execute(search_context_without_cot)

        assert result.success is False
        assert result.error is not None
        assert "Configuration error" in result.error

    async def test_empty_query_results(
        self, mock_pipeline_service: Mock, search_context_without_cot: SearchContext
    ) -> None:
        """Test generation with empty query results."""
        search_context_without_cot.query_results = []
        mock_pipeline_service._validate_configuration.return_value = (None, Mock(), Mock())
        mock_pipeline_service._get_templates.return_value = (Mock(id=uuid4()), None)
        mock_pipeline_service._format_context.return_value = ""
        mock_pipeline_service._generate_answer.return_value = "No relevant documents found"

        stage = GenerationStage(mock_pipeline_service)
        result = await stage.execute(search_context_without_cot)

        assert result.success is True
        assert result.context.generated_answer == "No relevant documents found"
