"""
Unit tests for ReasoningStage.

Tests the Chain of Thought reasoning functionality including:
- CoT execution
- Conditional execution (enable/disable/automatic)
- Context document extraction
- Error handling
"""

from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtOutput, ReasoningStep
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline.search_context import SearchContext
from rag_solution.services.pipeline.stages.reasoning_stage import ReasoningStage


@pytest.fixture
def mock_cot_service() -> Mock:
    """Create mock ChainOfThoughtService."""
    service = Mock()
    service.execute_chain_of_thought = AsyncMock()
    return service


@pytest.fixture
def search_context_simple() -> SearchContext:
    """Create search context with simple question."""
    user_id = uuid4()
    collection_id = uuid4()
    search_input = SearchInput(user_id=user_id, collection_id=collection_id, question="What is Python?")
    context = SearchContext(search_input=search_input, user_id=user_id, collection_id=collection_id)

    # Add mock query results
    result1 = Mock()
    result1.chunk = Mock()
    result1.chunk.text = "Python is a programming language."
    result2 = Mock()
    result2.chunk = Mock()
    result2.chunk.text = "Python is used for web development."

    context.query_results = [result1, result2]
    return context


@pytest.fixture
def search_context_complex() -> SearchContext:
    """Create search context with complex question."""
    user_id = uuid4()
    collection_id = uuid4()
    search_input = SearchInput(
        user_id=user_id,
        collection_id=collection_id,
        question="How does machine learning work and what are its key components?",
    )
    context = SearchContext(search_input=search_input, user_id=user_id, collection_id=collection_id)

    # Add mock query results
    result1 = Mock()
    result1.chunk = Mock()
    result1.chunk.text = "Machine learning uses algorithms to learn patterns from data."

    context.query_results = [result1]
    return context


@pytest.fixture
def mock_cot_output() -> ChainOfThoughtOutput:
    """Create mock ChainOfThoughtOutput."""
    return ChainOfThoughtOutput(
        original_question="Test question?",
        final_answer="Test answer",
        reasoning_steps=[
            ReasoningStep(
                step_number=1,
                question="Sub question 1",
                intermediate_answer="Intermediate answer 1",
                confidence_score=0.9,
            )
        ],
        total_confidence=0.9,
        token_usage=100,
        total_execution_time=1.5,
        reasoning_strategy="decomposition",
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestReasoningStage:
    """Test suite for ReasoningStage."""

    async def test_stage_initialization(self, mock_cot_service: Mock) -> None:
        """Test that stage initializes correctly."""
        stage = ReasoningStage(mock_cot_service)
        assert stage.stage_name == "Reasoning"
        assert stage.cot_service == mock_cot_service

    async def test_cot_skipped_simple_question(
        self, mock_cot_service: Mock, search_context_simple: SearchContext
    ) -> None:
        """Test that CoT is skipped for simple questions."""
        stage = ReasoningStage(mock_cot_service)
        result = await stage.execute(search_context_simple)

        assert result.success is True
        assert not hasattr(result.context, "cot_output") or result.context.cot_output is None
        assert "reasoning" not in result.context.metadata
        mock_cot_service.execute_chain_of_thought.assert_not_called()

    async def test_cot_executed_complex_question(
        self, mock_cot_service: Mock, search_context_complex: SearchContext, mock_cot_output: ChainOfThoughtOutput
    ) -> None:
        """Test that CoT is executed for complex questions."""
        mock_cot_service.execute_chain_of_thought.return_value = mock_cot_output

        stage = ReasoningStage(mock_cot_service)
        result = await stage.execute(search_context_complex)

        assert result.success is True
        assert result.context.cot_output == mock_cot_output
        assert "reasoning" in result.context.metadata
        assert result.context.metadata["reasoning"]["strategy"] == "decomposition"
        assert result.context.metadata["reasoning"]["steps_count"] == 1
        assert result.context.metadata["reasoning"]["confidence"] == 0.9

        mock_cot_service.execute_chain_of_thought.assert_called_once()

    async def test_cot_explicitly_disabled(
        self, mock_cot_service: Mock, search_context_complex: SearchContext
    ) -> None:
        """Test that CoT is skipped when explicitly disabled."""
        search_context_complex.search_input.config_metadata = {"cot_disabled": True}

        stage = ReasoningStage(mock_cot_service)
        result = await stage.execute(search_context_complex)

        assert result.success is True
        assert not hasattr(result.context, "cot_output") or result.context.cot_output is None
        assert "reasoning" not in result.context.metadata
        mock_cot_service.execute_chain_of_thought.assert_not_called()

    async def test_cot_explicitly_enabled(
        self, mock_cot_service: Mock, search_context_simple: SearchContext, mock_cot_output: ChainOfThoughtOutput
    ) -> None:
        """Test that CoT is executed when explicitly enabled."""
        search_context_simple.search_input.config_metadata = {"cot_enabled": True}
        mock_cot_service.execute_chain_of_thought.return_value = mock_cot_output

        stage = ReasoningStage(mock_cot_service)
        result = await stage.execute(search_context_simple)

        assert result.success is True
        assert result.context.cot_output == mock_cot_output
        mock_cot_service.execute_chain_of_thought.assert_called_once()

    async def test_context_document_extraction(
        self, mock_cot_service: Mock, search_context_simple: SearchContext, mock_cot_output: ChainOfThoughtOutput
    ) -> None:
        """Test that context documents are extracted correctly."""
        search_context_simple.search_input.config_metadata = {"cot_enabled": True}
        mock_cot_service.execute_chain_of_thought.return_value = mock_cot_output

        stage = ReasoningStage(mock_cot_service)
        await stage.execute(search_context_simple)

        # Check that context documents were passed to CoT service
        call_args = mock_cot_service.execute_chain_of_thought.call_args
        context_docs = call_args[0][1]  # Second positional argument

        assert len(context_docs) == 2
        assert "Python is a programming language." in context_docs
        assert "Python is used for web development." in context_docs

    async def test_missing_query_results(
        self, mock_cot_service: Mock, search_context_simple: SearchContext
    ) -> None:
        """Test error handling when query results are missing."""
        search_context_simple.query_results = None
        search_context_simple.search_input.config_metadata = {"cot_enabled": True}

        stage = ReasoningStage(mock_cot_service)
        result = await stage.execute(search_context_simple)

        assert result.success is False
        assert result.error is not None
        assert "Query results not set" in result.error

    async def test_cot_error_handling(
        self, mock_cot_service: Mock, search_context_complex: SearchContext
    ) -> None:
        """Test error handling during CoT execution."""
        mock_cot_service.execute_chain_of_thought.side_effect = ValueError("CoT execution failed")

        stage = ReasoningStage(mock_cot_service)
        result = await stage.execute(search_context_complex)

        assert result.success is False
        assert result.error is not None
        assert "CoT execution failed" in result.error

    async def test_cot_input_conversion(
        self, mock_cot_service: Mock, search_context_complex: SearchContext, mock_cot_output: ChainOfThoughtOutput
    ) -> None:
        """Test that SearchInput is correctly converted to ChainOfThoughtInput."""
        mock_cot_service.execute_chain_of_thought.return_value = mock_cot_output

        stage = ReasoningStage(mock_cot_service)
        await stage.execute(search_context_complex)

        # Check that ChainOfThoughtInput was created correctly
        call_args = mock_cot_service.execute_chain_of_thought.call_args
        cot_input = call_args[0][0]  # First positional argument

        assert cot_input.question == search_context_complex.search_input.question
        assert cot_input.collection_id == search_context_complex.collection_id
        assert cot_input.user_id == search_context_complex.user_id

    async def test_empty_query_results(
        self, mock_cot_service: Mock, search_context_complex: SearchContext, mock_cot_output: ChainOfThoughtOutput
    ) -> None:
        """Test CoT execution with empty query results."""
        search_context_complex.query_results = []
        mock_cot_service.execute_chain_of_thought.return_value = mock_cot_output

        stage = ReasoningStage(mock_cot_service)
        result = await stage.execute(search_context_complex)

        assert result.success is True
        assert result.context.cot_output == mock_cot_output

        # Context documents should be empty
        call_args = mock_cot_service.execute_chain_of_thought.call_args
        context_docs = call_args[0][1]
        assert len(context_docs) == 0
