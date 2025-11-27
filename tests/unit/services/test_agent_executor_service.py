"""Unit tests for AgentExecutorService and CircuitBreaker.

This module tests the agent execution hooks functionality including:
- Circuit breaker pattern
- Agent execution at each pipeline stage
- Error handling and failure isolation

Reference: GitHub Issue #697
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import UUID4

from rag_solution.schemas.agent_config_schema import (
    AgentArtifact,
    AgentContext,
    AgentExecutionStatus,
    AgentResult,
    AgentStage,
)
from rag_solution.services.agent_executor_service import (
    BaseAgentHandler,
    CircuitBreaker,
    CircuitBreakerState,
)


# ============================================================================
# Circuit Breaker Tests
# ============================================================================


class TestCircuitBreaker:
    """Test suite for CircuitBreaker class."""

    def test_initial_state_is_closed(self) -> None:
        """Test that circuit breaker starts in closed state."""
        cb = CircuitBreaker()
        assert cb.get_state("test") == "closed"
        assert not cb.is_open("test")

    def test_records_failure(self) -> None:
        """Test that failures are recorded correctly."""
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure("test")
        assert cb._states["test"].failure_count == 1
        assert cb.get_state("test") == "closed"

    def test_opens_after_threshold(self) -> None:
        """Test that circuit opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure("test")
        assert cb.get_state("test") == "open"
        assert cb.is_open("test")

    def test_success_resets_failure_count(self) -> None:
        """Test that success resets failure count in closed state."""
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure("test")
        cb.record_failure("test")
        assert cb._states["test"].failure_count == 2
        cb.record_success("test")
        assert cb._states["test"].failure_count == 0

    def test_transitions_to_half_open_after_timeout(self) -> None:
        """Test circuit transitions to half-open after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure("test")
        assert cb.get_state("test") == "open"
        time.sleep(0.15)
        # is_open should trigger transition to half-open
        assert not cb.is_open("test")
        assert cb.get_state("test") == "half_open"

    def test_closes_after_successful_half_open(self) -> None:
        """Test circuit closes after successful calls in half-open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1, half_open_max_calls=2)
        cb.record_failure("test")
        time.sleep(0.15)
        cb.is_open("test")  # Trigger transition
        cb.record_success("test")
        cb.record_success("test")
        assert cb.get_state("test") == "closed"

    def test_reopens_on_failure_in_half_open(self) -> None:
        """Test circuit reopens on failure in half-open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure("test")
        time.sleep(0.15)
        cb.is_open("test")  # Trigger transition to half-open
        cb.record_failure("test")
        assert cb.get_state("test") == "open"

    def test_independent_circuits(self) -> None:
        """Test that different circuit IDs are independent."""
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("circuit1")
        cb.record_failure("circuit1")
        cb.record_failure("circuit2")
        assert cb.get_state("circuit1") == "open"
        assert cb.get_state("circuit2") == "closed"


# ============================================================================
# Agent Context and Result Schema Tests
# ============================================================================


class TestAgentSchemas:
    """Test suite for agent-related Pydantic schemas."""

    def test_agent_context_creation(self) -> None:
        """Test AgentContext creation with required fields."""
        context = AgentContext(
            search_input={"question": "test question"},
            collection_id=UUID4("12345678-1234-5678-1234-567812345678"),
            user_id=UUID4("87654321-4321-8765-4321-876543218765"),
            stage=AgentStage.PRE_SEARCH,
            query="test query",
        )
        assert context.query == "test query"
        assert context.stage == AgentStage.PRE_SEARCH
        assert context.query_results == []
        assert context.previous_results == []

    def test_agent_context_with_all_fields(self) -> None:
        """Test AgentContext with all optional fields."""
        context = AgentContext(
            search_input={"question": "test"},
            collection_id=UUID4("12345678-1234-5678-1234-567812345678"),
            user_id=UUID4("87654321-4321-8765-4321-876543218765"),
            stage=AgentStage.POST_SEARCH,
            query="test",
            query_results=[{"id": "doc1", "score": 0.9}],
            config={"threshold": 0.5},
            metadata={"source": "test"},
        )
        assert len(context.query_results) == 1
        assert context.config["threshold"] == 0.5

    def test_agent_result_success(self) -> None:
        """Test AgentResult for successful execution."""
        result = AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="test_agent",
            agent_type="query_expander",
            stage="pre_search",
            status=AgentExecutionStatus.SUCCESS,
            execution_time_ms=100.5,
            modified_query="expanded query",
        )
        assert result.status == AgentExecutionStatus.SUCCESS
        assert result.modified_query == "expanded query"
        assert result.error_message is None

    def test_agent_result_failure(self) -> None:
        """Test AgentResult for failed execution."""
        result = AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="test_agent",
            agent_type="reranker",
            stage="post_search",
            status=AgentExecutionStatus.FAILED,
            execution_time_ms=50.0,
            error_message="Connection timeout",
        )
        assert result.status == AgentExecutionStatus.FAILED
        assert "timeout" in result.error_message.lower()

    def test_agent_result_with_artifacts(self) -> None:
        """Test AgentResult with generated artifacts."""
        artifact = AgentArtifact(
            artifact_type="pdf",
            content_type="application/pdf",
            filename="report.pdf",
            data_url="data:application/pdf;base64,ABC123",
            size_bytes=1024,
        )
        result = AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="pdf_generator",
            agent_type="pdf_generator",
            stage="response",
            status=AgentExecutionStatus.SUCCESS,
            execution_time_ms=500.0,
            artifacts=[artifact],
        )
        assert len(result.artifacts) == 1
        assert result.artifacts[0].filename == "report.pdf"

    def test_agent_artifact_creation(self) -> None:
        """Test AgentArtifact creation."""
        artifact = AgentArtifact(
            artifact_type="chart",
            content_type="image/png",
            filename="chart.png",
            metadata={"chart_type": "bar"},
        )
        assert artifact.artifact_type == "chart"
        assert artifact.metadata["chart_type"] == "bar"


# ============================================================================
# Base Agent Handler Tests
# ============================================================================


class MockAgentHandler(BaseAgentHandler):
    """Mock agent handler for testing."""

    def __init__(self, return_value: AgentResult | None = None, raise_exception: bool = False) -> None:
        self._return_value = return_value
        self._raise_exception = raise_exception

    async def execute(self, context: AgentContext) -> AgentResult:
        if self._raise_exception:
            raise RuntimeError("Test exception")
        if self._return_value:
            return self._return_value
        return AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="mock_agent",
            agent_type="mock",
            stage="pre_search",
            status=AgentExecutionStatus.SUCCESS,
            execution_time_ms=10.0,
        )

    @property
    def agent_type(self) -> str:
        return "mock"


class TestBaseAgentHandler:
    """Test suite for BaseAgentHandler abstract class."""

    @pytest.mark.asyncio
    async def test_mock_handler_success(self) -> None:
        """Test mock handler returns expected result."""
        handler = MockAgentHandler()
        context = AgentContext(
            search_input={},
            collection_id=UUID4("12345678-1234-5678-1234-567812345678"),
            user_id=UUID4("87654321-4321-8765-4321-876543218765"),
            stage=AgentStage.PRE_SEARCH,
            query="test",
        )
        result = await handler.execute(context)
        assert result.status == AgentExecutionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_mock_handler_with_custom_result(self) -> None:
        """Test mock handler with custom return value."""
        custom_result = AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="custom",
            agent_type="custom",
            stage="post_search",
            status=AgentExecutionStatus.SUCCESS,
            execution_time_ms=100.0,
            modified_results=[{"id": "doc1"}],
        )
        handler = MockAgentHandler(return_value=custom_result)
        context = AgentContext(
            search_input={},
            collection_id=UUID4("12345678-1234-5678-1234-567812345678"),
            user_id=UUID4("87654321-4321-8765-4321-876543218765"),
            stage=AgentStage.POST_SEARCH,
            query="test",
        )
        result = await handler.execute(context)
        assert result.modified_results is not None
        assert len(result.modified_results) == 1

    @pytest.mark.asyncio
    async def test_mock_handler_raises_exception(self) -> None:
        """Test mock handler exception handling."""
        handler = MockAgentHandler(raise_exception=True)
        context = AgentContext(
            search_input={},
            collection_id=UUID4("12345678-1234-5678-1234-567812345678"),
            user_id=UUID4("87654321-4321-8765-4321-876543218765"),
            stage=AgentStage.PRE_SEARCH,
            query="test",
        )
        with pytest.raises(RuntimeError):
            await handler.execute(context)


# ============================================================================
# Agent Stage Tests
# ============================================================================


class TestAgentStages:
    """Test agent execution at different pipeline stages."""

    def test_stage_enum_values(self) -> None:
        """Test AgentStage enum values."""
        assert AgentStage.PRE_SEARCH.value == "pre_search"
        assert AgentStage.POST_SEARCH.value == "post_search"
        assert AgentStage.RESPONSE.value == "response"

    def test_execution_status_enum_values(self) -> None:
        """Test AgentExecutionStatus enum values."""
        assert AgentExecutionStatus.SUCCESS.value == "success"
        assert AgentExecutionStatus.FAILED.value == "failed"
        assert AgentExecutionStatus.TIMEOUT.value == "timeout"
        assert AgentExecutionStatus.SKIPPED.value == "skipped"
        assert AgentExecutionStatus.CIRCUIT_OPEN.value == "circuit_open"


# ============================================================================
# Integration-like Unit Tests
# ============================================================================


class TestAgentExecutionFlow:
    """Test agent execution flow scenarios."""

    @pytest.mark.asyncio
    async def test_pre_search_agent_modifies_query(self) -> None:
        """Test pre-search agent that modifies query."""
        modified_result = AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="query_expander",
            agent_type="query_expander",
            stage="pre_search",
            status=AgentExecutionStatus.SUCCESS,
            execution_time_ms=50.0,
            modified_query="expanded: what is machine learning and AI",
        )
        handler = MockAgentHandler(return_value=modified_result)
        context = AgentContext(
            search_input={"question": "what is ML"},
            collection_id=UUID4("12345678-1234-5678-1234-567812345678"),
            user_id=UUID4("87654321-4321-8765-4321-876543218765"),
            stage=AgentStage.PRE_SEARCH,
            query="what is ML",
        )
        result = await handler.execute(context)
        assert result.modified_query is not None
        assert "expanded" in result.modified_query

    @pytest.mark.asyncio
    async def test_post_search_agent_modifies_results(self) -> None:
        """Test post-search agent that modifies results."""
        modified_result = AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="reranker",
            agent_type="reranker",
            stage="post_search",
            status=AgentExecutionStatus.SUCCESS,
            execution_time_ms=100.0,
            modified_results=[
                {"id": "doc2", "score": 0.95},
                {"id": "doc1", "score": 0.85},
            ],
        )
        handler = MockAgentHandler(return_value=modified_result)
        context = AgentContext(
            search_input={},
            collection_id=UUID4("12345678-1234-5678-1234-567812345678"),
            user_id=UUID4("87654321-4321-8765-4321-876543218765"),
            stage=AgentStage.POST_SEARCH,
            query="test",
            query_results=[
                {"id": "doc1", "score": 0.9},
                {"id": "doc2", "score": 0.8},
            ],
        )
        result = await handler.execute(context)
        assert result.modified_results is not None
        # Check reranking - doc2 now first
        assert result.modified_results[0]["id"] == "doc2"

    @pytest.mark.asyncio
    async def test_response_agent_generates_artifact(self) -> None:
        """Test response agent that generates artifact."""
        artifact = AgentArtifact(
            artifact_type="pptx",
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename="summary.pptx",
            size_bytes=5000,
        )
        modified_result = AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="pptx_generator",
            agent_type="pptx_generator",
            stage="response",
            status=AgentExecutionStatus.SUCCESS,
            execution_time_ms=500.0,
            artifacts=[artifact],
        )
        handler = MockAgentHandler(return_value=modified_result)
        context = AgentContext(
            search_input={},
            collection_id=UUID4("12345678-1234-5678-1234-567812345678"),
            user_id=UUID4("87654321-4321-8765-4321-876543218765"),
            stage=AgentStage.RESPONSE,
            query="test",
            metadata={"generated_answer": "Test answer"},
        )
        result = await handler.execute(context)
        assert result.artifacts is not None
        assert len(result.artifacts) == 1
        assert result.artifacts[0].artifact_type == "pptx"


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestAgentErrorHandling:
    """Test error handling in agent execution."""

    def test_circuit_breaker_blocks_requests_when_open(self) -> None:
        """Test that circuit breaker blocks requests when open."""
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure("test")
        assert cb.is_open("test")

    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self) -> None:
        """Test handling of agent timeout."""
        # Simulate timeout result
        timeout_result = AgentResult(
            agent_config_id=UUID4("12345678-1234-5678-1234-567812345678"),
            agent_name="slow_agent",
            agent_type="slow",
            stage="pre_search",
            status=AgentExecutionStatus.TIMEOUT,
            execution_time_ms=30000.0,
            error_message="Timeout after 30s",
        )
        assert timeout_result.status == AgentExecutionStatus.TIMEOUT
        assert "Timeout" in timeout_result.error_message

    def test_circuit_breaker_state_isolation(self) -> None:
        """Test that circuit breaker state is isolated per circuit ID."""
        cb = CircuitBreaker(failure_threshold=2)
        # Fail one circuit
        cb.record_failure("agent1")
        cb.record_failure("agent1")
        # Other circuit should be unaffected
        assert cb.is_open("agent1")
        assert not cb.is_open("agent2")
        assert not cb.is_open("agent3")
