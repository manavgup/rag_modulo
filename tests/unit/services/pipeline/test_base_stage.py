"""
Unit tests for BaseStage abstract class.

Tests the base functionality of pipeline stages including:
- Stage initialization
- Error handling
- Logging
- Abstract method enforcement
"""

import pytest

from rag_solution.services.pipeline.base_stage import BaseStage, StageResult
from rag_solution.services.pipeline.search_context import SearchContext
from rag_solution.schemas.search_schema import SearchInput


class MockStage(BaseStage):
    """Mock implementation of BaseStage for testing."""

    def __init__(self, stage_name: str, should_succeed: bool = True) -> None:
        """Initialize mock stage with success control."""
        super().__init__(stage_name)
        self.should_succeed = should_succeed
        self.execute_called = False

    async def execute(self, context: SearchContext) -> StageResult:
        """Mock execute implementation."""
        self.execute_called = True
        self._log_stage_start(context)

        if not self.should_succeed:
            result = StageResult(success=False, context=context, error="Mock failure")
        else:
            context.add_metadata("mock_data", "test_value")
            result = StageResult(success=True, context=context)

        self._log_stage_complete(result)
        return result


@pytest.fixture
def mock_search_input() -> SearchInput:
    """Create mock search input for testing."""
    from uuid import uuid4

    return SearchInput(user_id=uuid4(), collection_id=uuid4(), question="Test question?")


@pytest.fixture
def search_context(mock_search_input: SearchInput) -> SearchContext:
    """Create search context for testing."""
    return SearchContext(
        search_input=mock_search_input, user_id=mock_search_input.user_id, collection_id=mock_search_input.collection_id
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestBaseStage:
    """Test suite for BaseStage class."""

    async def test_stage_initialization(self) -> None:
        """Test that stage initializes correctly."""
        stage = MockStage("test_stage")
        assert stage.stage_name == "test_stage"
        assert hasattr(stage, "logger")

    async def test_successful_stage_execution(self, search_context: SearchContext) -> None:
        """Test successful stage execution."""
        stage = MockStage("test_stage", should_succeed=True)
        result = await stage.execute(search_context)

        assert result.success is True
        assert result.error is None
        assert stage.execute_called is True
        assert "mock_data" in result.context.metadata

    async def test_failed_stage_execution(self, search_context: SearchContext) -> None:
        """Test failed stage execution."""
        stage = MockStage("test_stage", should_succeed=False)
        result = await stage.execute(search_context)

        assert result.success is False
        assert result.error == "Mock failure"
        assert stage.execute_called is True

    async def test_error_handling(self, search_context: SearchContext) -> None:
        """Test stage error handling."""
        stage = MockStage("test_stage")
        test_error = ValueError("Test error")

        result = await stage._handle_error(search_context, test_error)

        assert result.success is False
        assert "Test error" in result.error
        assert result.context == search_context

    async def test_abstract_class_enforcement(self) -> None:
        """Test that BaseStage cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseStage("invalid")  # type: ignore

    async def test_stage_result_creation(self, search_context: SearchContext) -> None:
        """Test StageResult dataclass creation."""
        result = StageResult(success=True, context=search_context, metadata={"key": "value"})

        assert result.success is True
        assert result.context == search_context
        assert result.error is None
        assert result.metadata == {"key": "value"}

    async def test_stage_result_with_error(self, search_context: SearchContext) -> None:
        """Test StageResult with error information."""
        result = StageResult(success=False, context=search_context, error="Test error")

        assert result.success is False
        assert result.error == "Test error"
