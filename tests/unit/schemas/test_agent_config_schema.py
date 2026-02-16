"""Unit tests for agent configuration schemas.

This module tests the Pydantic schemas for agent configuration
including validation and serialization.

Reference: GitHub Issue #697
"""

import pytest
from pydantic import UUID4, ValidationError

from rag_solution.schemas.agent_config_schema import (
    AgentArtifact,
    AgentConfigInput,
    AgentConfigOutput,
    AgentConfigStatus,
    AgentConfigUpdate,
    AgentContext,
    AgentExecutionStatus,
    AgentExecutionSummary,
    AgentResult,
    AgentStage,
    BatchPriorityUpdate,
    CollectionAgentInput,
    CollectionAgentOutput,
    CollectionAgentUpdate,
    PipelineMetadata,
)


class TestAgentStageEnum:
    """Test AgentStage enum."""

    def test_pre_search_value(self) -> None:
        """Test PRE_SEARCH stage value."""
        assert AgentStage.PRE_SEARCH.value == "pre_search"

    def test_post_search_value(self) -> None:
        """Test POST_SEARCH stage value."""
        assert AgentStage.POST_SEARCH.value == "post_search"

    def test_response_value(self) -> None:
        """Test RESPONSE stage value."""
        assert AgentStage.RESPONSE.value == "response"


class TestAgentConfigStatusEnum:
    """Test AgentConfigStatus enum."""

    def test_active_value(self) -> None:
        """Test ACTIVE status value."""
        assert AgentConfigStatus.ACTIVE.value == "active"

    def test_disabled_value(self) -> None:
        """Test DISABLED status value."""
        assert AgentConfigStatus.DISABLED.value == "disabled"

    def test_deprecated_value(self) -> None:
        """Test DEPRECATED status value."""
        assert AgentConfigStatus.DEPRECATED.value == "deprecated"


class TestAgentExecutionStatusEnum:
    """Test AgentExecutionStatus enum."""

    def test_all_statuses(self) -> None:
        """Test all execution status values."""
        assert AgentExecutionStatus.SUCCESS.value == "success"
        assert AgentExecutionStatus.FAILED.value == "failed"
        assert AgentExecutionStatus.TIMEOUT.value == "timeout"
        assert AgentExecutionStatus.SKIPPED.value == "skipped"
        assert AgentExecutionStatus.CIRCUIT_OPEN.value == "circuit_open"


class TestAgentConfigInput:
    """Test AgentConfigInput schema."""

    def test_valid_input(self) -> None:
        """Test creating valid agent config input."""
        config = AgentConfigInput(
            name="Query Expander",
            description="Expands queries for better retrieval",
            agent_type="query_expander",
            stage=AgentStage.PRE_SEARCH,
            handler_module="rag_solution.agents.query_expander",
            handler_class="QueryExpanderAgent",
        )
        assert config.name == "Query Expander"
        assert config.stage == AgentStage.PRE_SEARCH
        assert config.timeout_seconds == 30  # default
        assert config.max_retries == 2  # default

    def test_with_custom_settings(self) -> None:
        """Test config with custom timeout and retries."""
        config = AgentConfigInput(
            name="Slow Agent",
            agent_type="slow_agent",
            stage=AgentStage.RESPONSE,
            handler_module="test.module",
            handler_class="SlowAgent",
            timeout_seconds=120,
            max_retries=5,
            priority=50,
        )
        assert config.timeout_seconds == 120
        assert config.max_retries == 5
        assert config.priority == 50

    def test_with_default_config(self) -> None:
        """Test config with default_config parameter."""
        config = AgentConfigInput(
            name="Configurable Agent",
            agent_type="configurable",
            stage=AgentStage.POST_SEARCH,
            handler_module="test.module",
            handler_class="ConfigurableAgent",
            default_config={"threshold": 0.5, "max_results": 10},
        )
        assert config.default_config["threshold"] == 0.5
        assert config.default_config["max_results"] == 10

    def test_name_validation(self) -> None:
        """Test name field validation."""
        with pytest.raises(ValidationError):
            AgentConfigInput(
                name="",  # Empty name should fail
                agent_type="test",
                stage=AgentStage.PRE_SEARCH,
                handler_module="test.module",
                handler_class="TestAgent",
            )

    def test_timeout_validation(self) -> None:
        """Test timeout_seconds validation bounds."""
        # Too low
        with pytest.raises(ValidationError):
            AgentConfigInput(
                name="Test",
                agent_type="test",
                stage=AgentStage.PRE_SEARCH,
                handler_module="test.module",
                handler_class="TestAgent",
                timeout_seconds=0,
            )
        # Too high
        with pytest.raises(ValidationError):
            AgentConfigInput(
                name="Test",
                agent_type="test",
                stage=AgentStage.PRE_SEARCH,
                handler_module="test.module",
                handler_class="TestAgent",
                timeout_seconds=500,
            )

    def test_max_retries_validation(self) -> None:
        """Test max_retries validation bounds."""
        with pytest.raises(ValidationError):
            AgentConfigInput(
                name="Test",
                agent_type="test",
                stage=AgentStage.PRE_SEARCH,
                handler_module="test.module",
                handler_class="TestAgent",
                max_retries=10,  # Max is 5
            )


class TestAgentConfigUpdate:
    """Test AgentConfigUpdate schema."""

    def test_partial_update(self) -> None:
        """Test partial update with only some fields."""
        update = AgentConfigUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.description is None
        assert update.status is None

    def test_status_update(self) -> None:
        """Test status update."""
        update = AgentConfigUpdate(status=AgentConfigStatus.DISABLED)
        assert update.status == AgentConfigStatus.DISABLED

    def test_all_fields_update(self) -> None:
        """Test update with all fields."""
        update = AgentConfigUpdate(
            name="New Name",
            description="New description",
            default_config={"new": "config"},
            timeout_seconds=60,
            max_retries=3,
            priority=200,
            status=AgentConfigStatus.ACTIVE,
        )
        assert update.name == "New Name"
        assert update.timeout_seconds == 60


class TestCollectionAgentInput:
    """Test CollectionAgentInput schema."""

    def test_minimal_input(self) -> None:
        """Test minimal collection-agent input."""
        assoc = CollectionAgentInput(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
        )
        assert assoc.enabled is True  # default
        assert assoc.priority == 100  # default
        assert assoc.config_override == {}  # default

    def test_full_input(self) -> None:
        """Test full collection-agent input."""
        assoc = CollectionAgentInput(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            enabled=False,
            priority=50,
            config_override={"custom_setting": "value"},
        )
        assert assoc.enabled is False
        assert assoc.priority == 50
        assert assoc.config_override["custom_setting"] == "value"

    def test_priority_validation(self) -> None:
        """Test priority field validation."""
        with pytest.raises(ValidationError):
            CollectionAgentInput(
                agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
                priority=2000,  # Max is 1000
            )


class TestCollectionAgentUpdate:
    """Test CollectionAgentUpdate schema."""

    def test_enable_only(self) -> None:
        """Test updating only enabled field."""
        update = CollectionAgentUpdate(enabled=False)
        assert update.enabled is False
        assert update.priority is None

    def test_priority_only(self) -> None:
        """Test updating only priority field."""
        update = CollectionAgentUpdate(priority=25)
        assert update.priority == 25
        assert update.enabled is None


class TestBatchPriorityUpdate:
    """Test BatchPriorityUpdate schema."""

    def test_batch_update(self) -> None:
        """Test batch priority update."""
        update = BatchPriorityUpdate(
            priorities={
                UUID4("12345678-1234-5678-1234-567812345678"): 10,
                UUID4("87654321-4321-8765-4321-876543218765"): 20,
            }
        )
        assert len(update.priorities) == 2


class TestAgentContext:
    """Test AgentContext schema."""

    def test_minimal_context(self) -> None:
        """Test minimal context creation."""
        ctx = AgentContext(
            search_input={"question": "test"},
            collection_id=UUID4("12345678-1234-5678-1234-567812345678"),
            user_id=UUID4("87654321-4321-8765-4321-876543218765"),
            stage=AgentStage.PRE_SEARCH,
            query="test query",
        )
        assert ctx.query == "test query"
        assert ctx.query_results == []
        assert ctx.previous_results == []
        assert ctx.config == {}

    def test_full_context(self) -> None:
        """Test full context with all fields."""
        ctx = AgentContext(
            search_input={"question": "test", "config": {"top_k": 10}},
            collection_id=UUID4("12345678-1234-5678-1234-567812345678"),
            user_id=UUID4("87654321-4321-8765-4321-876543218765"),
            stage=AgentStage.POST_SEARCH,
            query="test query",
            query_results=[{"id": "doc1", "score": 0.9}],
            config={"threshold": 0.5},
            metadata={"source": "test"},
        )
        assert len(ctx.query_results) == 1
        assert ctx.config["threshold"] == 0.5


class TestAgentResult:
    """Test AgentResult schema."""

    def test_success_result(self) -> None:
        """Test successful result."""
        result = AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="Test Agent",
            agent_type="test",
            stage="pre_search",
            status=AgentExecutionStatus.SUCCESS,
            execution_time_ms=50.5,
        )
        assert result.status == AgentExecutionStatus.SUCCESS
        assert result.execution_time_ms == 50.5
        assert result.error_message is None

    def test_failed_result(self) -> None:
        """Test failed result."""
        result = AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="Test Agent",
            agent_type="test",
            stage="pre_search",
            status=AgentExecutionStatus.FAILED,
            execution_time_ms=100.0,
            error_message="Connection failed",
        )
        assert result.status == AgentExecutionStatus.FAILED
        assert "Connection" in result.error_message

    def test_result_with_modified_query(self) -> None:
        """Test result with modified query."""
        result = AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="Query Expander",
            agent_type="query_expander",
            stage="pre_search",
            status=AgentExecutionStatus.SUCCESS,
            execution_time_ms=30.0,
            modified_query="expanded query with more terms",
        )
        assert result.modified_query is not None
        assert "expanded" in result.modified_query


class TestAgentArtifact:
    """Test AgentArtifact schema."""

    def test_pdf_artifact(self) -> None:
        """Test PDF artifact creation."""
        artifact = AgentArtifact(
            artifact_type="pdf",
            content_type="application/pdf",
            filename="report.pdf",
            size_bytes=10240,
        )
        assert artifact.artifact_type == "pdf"
        assert artifact.content_type == "application/pdf"
        assert artifact.filename == "report.pdf"

    def test_artifact_with_data_url(self) -> None:
        """Test artifact with data URL."""
        artifact = AgentArtifact(
            artifact_type="chart",
            content_type="image/png",
            filename="chart.png",
            data_url="data:image/png;base64,ABC123",
            metadata={"chart_type": "bar", "title": "Sales"},
        )
        assert artifact.data_url.startswith("data:")
        assert artifact.metadata["chart_type"] == "bar"


class TestAgentExecutionSummary:
    """Test AgentExecutionSummary schema."""

    def test_empty_summary(self) -> None:
        """Test empty summary defaults."""
        summary = AgentExecutionSummary()
        assert summary.total_agents == 0
        assert summary.successful == 0
        assert summary.failed == 0
        assert summary.skipped == 0
        assert summary.total_execution_time_ms == 0.0
        assert summary.artifacts == []

    def test_populated_summary(self) -> None:
        """Test populated summary."""
        result = AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="Test",
            agent_type="test",
            stage="pre_search",
            status=AgentExecutionStatus.SUCCESS,
            execution_time_ms=50.0,
        )
        summary = AgentExecutionSummary(
            total_agents=3,
            successful=2,
            failed=1,
            total_execution_time_ms=150.0,
            pre_search_results=[result],
        )
        assert summary.total_agents == 3
        assert summary.successful == 2
        assert len(summary.pre_search_results) == 1


class TestPipelineMetadata:
    """Test PipelineMetadata schema."""

    def test_default_metadata(self) -> None:
        """Test default pipeline metadata."""
        meta = PipelineMetadata()
        assert meta.pipeline_version == "v2_with_agents"
        assert meta.stages_executed == []
        assert meta.total_execution_time_ms == 0.0

    def test_full_metadata(self) -> None:
        """Test full pipeline metadata."""
        summary = AgentExecutionSummary(total_agents=5)
        meta = PipelineMetadata(
            pipeline_version="v2_with_agents",
            stages_executed=["PipelineResolution", "QueryEnhancement", "PreSearchAgents"],
            total_execution_time_ms=500.0,
            agent_execution_summary=summary,
            timings={"PipelineResolution": 10.0, "QueryEnhancement": 50.0},
        )
        assert len(meta.stages_executed) == 3
        assert meta.agent_execution_summary.total_agents == 5
        assert "QueryEnhancement" in meta.timings
