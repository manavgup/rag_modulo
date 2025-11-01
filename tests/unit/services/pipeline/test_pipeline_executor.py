"""
Unit tests for PipelineExecutor.

Tests the pipeline executor functionality including:
- Stage orchestration
- Error handling
- Execution flow
- Stage management
"""

import pytest

from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline.base_stage import BaseStage, StageResult
from rag_solution.services.pipeline.pipeline_executor import PipelineExecutor
from rag_solution.services.pipeline.search_context import SearchContext


class MockSuccessStage(BaseStage):
    """Mock stage that always succeeds."""

    async def execute(self, context: SearchContext) -> StageResult:
        """Execute with success."""
        context.add_metadata(f"{self.stage_name}_executed", True)
        return StageResult(success=True, context=context)


class MockFailureStage(BaseStage):
    """Mock stage that always fails."""

    async def execute(self, context: SearchContext) -> StageResult:
        """Execute with failure."""
        return StageResult(success=False, context=context, error=f"{self.stage_name} failed")


class MockExceptionStage(BaseStage):
    """Mock stage that raises an exception."""

    async def execute(self, context: SearchContext) -> StageResult:
        """Execute with exception."""
        raise ValueError(f"{self.stage_name} exception")


@pytest.fixture
def mock_search_input() -> SearchInput:
    """Create mock search input."""
    from uuid import uuid4

    return SearchInput(user_id=uuid4(), collection_id=uuid4(), question="Test question?")


@pytest.fixture
def search_context(mock_search_input: SearchInput) -> SearchContext:
    """Create search context."""
    return SearchContext(
        search_input=mock_search_input, user_id=mock_search_input.user_id, collection_id=mock_search_input.collection_id
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestPipelineExecutor:
    """Test suite for PipelineExecutor."""

    async def test_executor_initialization(self) -> None:
        """Test executor initializes correctly."""
        stage1 = MockSuccessStage("stage1")
        stage2 = MockSuccessStage("stage2")
        executor = PipelineExecutor([stage1, stage2])

        assert len(executor.stages) == 2
        assert executor.get_stage_names() == ["stage1", "stage2"]

    async def test_successful_pipeline_execution(self, search_context: SearchContext) -> None:
        """Test successful execution of all stages."""
        stage1 = MockSuccessStage("stage1")
        stage2 = MockSuccessStage("stage2")
        stage3 = MockSuccessStage("stage3")

        executor = PipelineExecutor([stage1, stage2, stage3])
        result_context = await executor.execute(search_context)

        assert result_context.metadata["stage1_executed"] is True
        assert result_context.metadata["stage2_executed"] is True
        assert result_context.metadata["stage3_executed"] is True
        assert len(result_context.errors) == 0
        assert result_context.execution_time > 0

    async def test_pipeline_with_stage_failure(self, search_context: SearchContext) -> None:
        """Test pipeline continues after stage failure."""
        stage1 = MockSuccessStage("stage1")
        stage2 = MockFailureStage("stage2")
        stage3 = MockSuccessStage("stage3")

        executor = PipelineExecutor([stage1, stage2, stage3])
        result_context = await executor.execute(search_context)

        # Stage 1 and 3 should succeed
        assert result_context.metadata.get("stage1_executed") is True
        assert result_context.metadata.get("stage3_executed") is True

        # Stage 2 should have recorded error
        assert len(result_context.errors) == 1
        assert "stage2 failed" in result_context.errors[0]

    async def test_pipeline_with_exception(self, search_context: SearchContext) -> None:
        """Test pipeline handles exceptions."""
        stage1 = MockSuccessStage("stage1")
        stage2 = MockExceptionStage("stage2")
        stage3 = MockSuccessStage("stage3")

        executor = PipelineExecutor([stage1, stage2, stage3])
        result_context = await executor.execute(search_context)

        # Stage 1 and 3 should succeed
        assert result_context.metadata.get("stage1_executed") is True
        assert result_context.metadata.get("stage3_executed") is True

        # Exception should be recorded
        assert len(result_context.errors) > 0
        assert any("stage2" in error for error in result_context.errors)

    async def test_add_stage_dynamically(self) -> None:
        """Test adding stages dynamically."""
        stage1 = MockSuccessStage("stage1")
        executor = PipelineExecutor([stage1])

        assert len(executor.stages) == 1

        stage2 = MockSuccessStage("stage2")
        executor.add_stage(stage2)

        assert len(executor.stages) == 2
        assert executor.get_stage_names() == ["stage1", "stage2"]

    async def test_remove_stage_dynamically(self) -> None:
        """Test removing stages dynamically."""
        stage1 = MockSuccessStage("stage1")
        stage2 = MockSuccessStage("stage2")
        executor = PipelineExecutor([stage1, stage2])

        assert len(executor.stages) == 2

        executor.remove_stage("stage1")

        assert len(executor.stages) == 1
        assert executor.get_stage_names() == ["stage2"]

    async def test_empty_pipeline(self, search_context: SearchContext) -> None:
        """Test executor with no stages."""
        executor = PipelineExecutor([])
        result_context = await executor.execute(search_context)

        assert len(result_context.errors) == 0
        assert result_context.execution_time >= 0

    async def test_execution_time_tracking(self, search_context: SearchContext) -> None:
        """Test that execution time is tracked correctly."""
        stage1 = MockSuccessStage("stage1")
        executor = PipelineExecutor([stage1])

        result_context = await executor.execute(search_context)

        assert result_context.execution_time > 0
        assert isinstance(result_context.execution_time, float)

    async def test_stage_metadata_collection(self, search_context: SearchContext) -> None:
        """Test that stage metadata is collected."""

        class MetadataStage(BaseStage):
            async def execute(self, context: SearchContext) -> StageResult:
                return StageResult(
                    success=True, context=context, metadata={"custom_key": "custom_value", "count": 42}
                )

        stage = MetadataStage("metadata_stage")
        executor = PipelineExecutor([stage])

        result_context = await executor.execute(search_context)

        assert "metadata_stage_metadata" in result_context.metadata
        assert result_context.metadata["metadata_stage_metadata"]["custom_key"] == "custom_value"
        assert result_context.metadata["metadata_stage_metadata"]["count"] == 42
