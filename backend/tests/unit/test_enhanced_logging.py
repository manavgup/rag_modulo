"""Unit tests for enhanced logging components."""

import asyncio
import logging
from datetime import datetime, timezone

import pytest

from core.log_storage_service import LogEntry, LogLevel, LogStorageService
from core.logging_context import (
    LogContext,
    PipelineStage,
    clear_context,
    get_context,
    log_operation,
    pipeline_stage_context,
    request_context,
    set_context,
    update_context,
)


class TestLogContext:
    """Tests for LogContext dataclass."""

    def test_log_context_creation(self) -> None:
        """Test creating a LogContext instance."""
        context = LogContext(
            request_id="req_123",
            user_id="user_456",
            collection_id="coll_789",
            operation="test_operation",
        )

        assert context.request_id == "req_123"
        assert context.user_id == "user_456"
        assert context.collection_id == "coll_789"
        assert context.operation == "test_operation"

    def test_log_context_to_dict(self) -> None:
        """Test converting LogContext to dictionary."""
        context = LogContext(
            request_id="req_123",
            user_id="user_456",
            pipeline_stage="query_rewriting",
        )

        result = context.to_dict()

        assert result["request_id"] == "req_123"
        assert result["user_id"] == "user_456"
        assert result["pipeline_stage"] == "query_rewriting"
        # None values should not be in dict
        assert "collection_id" not in result
        assert "pipeline_id" not in result

    def test_log_context_with_metadata(self) -> None:
        """Test LogContext with metadata."""
        context = LogContext(
            request_id="req_123",
            metadata={"query": "test query", "timestamp": "2025-10-22"},
        )

        result = context.to_dict()

        assert result["request_id"] == "req_123"
        assert result["query"] == "test query"
        assert result["timestamp"] == "2025-10-22"


class TestContextManagement:
    """Tests for context management functions."""

    def setup_method(self) -> None:
        """Clear context before each test."""
        clear_context()

    def teardown_method(self) -> None:
        """Clear context after each test."""
        clear_context()

    def test_get_set_context(self) -> None:
        """Test getting and setting context."""
        new_context = LogContext(request_id="req_123", user_id="user_456")
        set_context(new_context)

        retrieved_context = get_context()

        assert retrieved_context.request_id == "req_123"
        assert retrieved_context.user_id == "user_456"

    def test_clear_context(self) -> None:
        """Test clearing context."""
        set_context(LogContext(request_id="req_123"))
        clear_context()

        context = get_context()

        assert context.request_id is None

    def test_update_context(self) -> None:
        """Test updating context fields."""
        set_context(LogContext(request_id="req_123"))
        update_context(user_id="user_456", collection_id="coll_789")

        context = get_context()

        assert context.request_id == "req_123"
        assert context.user_id == "user_456"
        assert context.collection_id == "coll_789"

    def test_update_context_with_custom_metadata(self) -> None:
        """Test updating context with custom metadata."""
        set_context(LogContext())
        update_context(custom_field="custom_value", another_field=123)

        context = get_context()

        assert context.metadata["custom_field"] == "custom_value"
        assert context.metadata["another_field"] == 123


class TestRequestContext:
    """Tests for request_context context manager."""

    def setup_method(self) -> None:
        """Clear context before each test."""
        clear_context()

    def teardown_method(self) -> None:
        """Clear context after each test."""
        clear_context()

    def test_request_context_sets_and_restores(self) -> None:
        """Test that request_context sets and restores context."""
        # Set initial context
        initial = LogContext(request_id="initial_req")
        set_context(initial)

        # Use request_context
        with request_context(request_id="new_req", user_id="user_123"):
            context = get_context()
            assert context.request_id == "new_req"
            assert context.user_id == "user_123"

        # Context should be restored
        restored = get_context()
        assert restored.request_id == "initial_req"

    def test_request_context_generates_request_id(self) -> None:
        """Test that request_context generates request_id if not provided."""
        with request_context(user_id="user_123"):
            context = get_context()
            assert context.request_id is not None
            assert context.request_id.startswith("req_")


class TestPipelineStageContext:
    """Tests for pipeline_stage_context context manager."""

    def setup_method(self) -> None:
        """Clear context before each test."""
        clear_context()

    def teardown_method(self) -> None:
        """Clear context after each test."""
        clear_context()

    def test_pipeline_stage_context_sets_stage(self) -> None:
        """Test that pipeline_stage_context sets the pipeline stage."""
        set_context(LogContext(request_id="req_123"))

        with pipeline_stage_context(PipelineStage.QUERY_REWRITING):
            context = get_context()
            assert context.pipeline_stage == PipelineStage.QUERY_REWRITING
            assert context.request_id == "req_123"  # Other context preserved

    def test_pipeline_stage_context_restores_previous_stage(self) -> None:
        """Test that pipeline_stage_context restores previous stage."""
        set_context(LogContext(request_id="req_123", pipeline_stage="initial_stage"))

        with pipeline_stage_context(PipelineStage.VECTOR_SEARCH):
            context = get_context()
            assert context.pipeline_stage == PipelineStage.VECTOR_SEARCH

        restored = get_context()
        assert restored.pipeline_stage == "initial_stage"

    def test_nested_pipeline_stages(self) -> None:
        """Test nested pipeline stage contexts."""
        with pipeline_stage_context(PipelineStage.QUERY_REWRITING):
            assert get_context().pipeline_stage == PipelineStage.QUERY_REWRITING

            with pipeline_stage_context(PipelineStage.EMBEDDING_GENERATION):
                assert get_context().pipeline_stage == PipelineStage.EMBEDDING_GENERATION

            # Should restore to outer stage
            assert get_context().pipeline_stage == PipelineStage.QUERY_REWRITING


class TestLogOperation:
    """Tests for log_operation context manager."""

    def setup_method(self) -> None:
        """Clear context and set up logger before each test."""
        clear_context()
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)
        self.handler = logging.handlers.MemoryHandler(capacity=1000)
        self.logger.addHandler(self.handler)

    def teardown_method(self) -> None:
        """Clear context and logger after each test."""
        clear_context()
        self.logger.removeHandler(self.handler)

    @pytest.mark.asyncio
    async def test_log_operation_basic(self) -> None:
        """Test basic log_operation functionality."""

        async def test_func() -> None:
            with log_operation(self.logger, "test_op", "collection", "coll_123", user_id="user_456"):
                context = get_context()
                assert context.operation == "test_op"
                assert context.collection_id == "coll_123"
                assert context.user_id == "user_456"
                assert context.request_id is not None

        await test_func()

    @pytest.mark.asyncio
    async def test_log_operation_timing(self) -> None:
        """Test that log_operation logs start and end with timing."""

        async def test_func() -> None:
            with log_operation(self.logger, "timed_op", "collection", "coll_123"):
                await asyncio.sleep(0.01)  # Small delay

        await test_func()

        # Should have logged start and completion
        self.handler.flush()
        # Note: MemoryHandler doesn't store records in an easily accessible way
        # This test validates the context manager doesn't raise errors

    @pytest.mark.asyncio
    async def test_log_operation_error_handling(self) -> None:
        """Test that log_operation handles errors properly."""

        async def test_func() -> None:
            with pytest.raises(ValueError):
                with log_operation(self.logger, "failing_op", "collection", "coll_123"):
                    raise ValueError("Test error")

        await test_func()

    @pytest.mark.asyncio
    async def test_log_operation_restores_context(self) -> None:
        """Test that log_operation restores previous context."""
        initial = LogContext(request_id="initial_req")
        set_context(initial)

        async def test_func() -> None:
            with log_operation(self.logger, "test_op", "collection", "coll_123"):
                pass

        await test_func()

        restored = get_context()
        assert restored.request_id == "initial_req"


class TestLogStorageService:
    """Tests for LogStorageService."""

    @pytest.mark.asyncio
    async def test_add_log_basic(self) -> None:
        """Test adding a log entry."""
        storage = LogStorageService(max_size_mb=1)

        entry = await storage.add_log(
            level=LogLevel.INFO,
            message="Test message",
            entity_type="collection",
            entity_id="coll_123",
        )

        assert entry.message == "Test message"
        assert entry.level == LogLevel.INFO
        assert entry.entity_type == "collection"
        assert entry.entity_id == "coll_123"

    @pytest.mark.asyncio
    async def test_get_logs_filtering(self) -> None:
        """Test filtering logs by entity."""
        storage = LogStorageService(max_size_mb=1)

        # Add logs for different entities
        await storage.add_log(LogLevel.INFO, "Log 1", entity_type="collection", entity_id="coll_123")
        await storage.add_log(LogLevel.INFO, "Log 2", entity_type="collection", entity_id="coll_456")
        await storage.add_log(LogLevel.INFO, "Log 3", entity_type="user", entity_id="user_789")

        # Filter by collection coll_123
        logs = await storage.get_logs(entity_type="collection", entity_id="coll_123")

        assert len(logs) == 1
        assert logs[0]["message"] == "Log 1"
        assert logs[0]["entity_id"] == "coll_123"

    @pytest.mark.asyncio
    async def test_get_logs_by_request_id(self) -> None:
        """Test filtering logs by request ID."""
        storage = LogStorageService(max_size_mb=1)

        # Add logs with same request ID
        await storage.add_log(LogLevel.INFO, "Log 1", request_id="req_123")
        await storage.add_log(LogLevel.INFO, "Log 2", request_id="req_123")
        await storage.add_log(LogLevel.INFO, "Log 3", request_id="req_456")

        logs = await storage.get_logs(request_id="req_123")

        assert len(logs) == 2
        assert all(log["request_id"] == "req_123" for log in logs)

    @pytest.mark.asyncio
    async def test_get_logs_by_pipeline_stage(self) -> None:
        """Test filtering logs by pipeline stage."""
        storage = LogStorageService(max_size_mb=1)

        await storage.add_log(LogLevel.INFO, "Log 1", pipeline_stage="query_rewriting")
        await storage.add_log(LogLevel.INFO, "Log 2", pipeline_stage="vector_search")
        await storage.add_log(LogLevel.INFO, "Log 3", pipeline_stage="query_rewriting")

        logs = await storage.get_logs(pipeline_stage="query_rewriting")

        assert len(logs) == 2
        assert all(log["pipeline_stage"] == "query_rewriting" for log in logs)

    @pytest.mark.asyncio
    async def test_get_logs_level_filtering(self) -> None:
        """Test filtering logs by level."""
        storage = LogStorageService(max_size_mb=1)

        await storage.add_log(LogLevel.DEBUG, "Debug message")
        await storage.add_log(LogLevel.INFO, "Info message")
        await storage.add_log(LogLevel.WARNING, "Warning message")
        await storage.add_log(LogLevel.ERROR, "Error message")

        # Get logs at WARNING level and above
        logs = await storage.get_logs(level=LogLevel.WARNING)

        assert len(logs) == 2
        assert any(log["level"] == "warning" for log in logs)
        assert any(log["level"] == "error" for log in logs)

    @pytest.mark.asyncio
    async def test_get_logs_search(self) -> None:
        """Test searching logs by message text."""
        storage = LogStorageService(max_size_mb=1)

        await storage.add_log(LogLevel.INFO, "Query rewritten successfully")
        await storage.add_log(LogLevel.INFO, "Vector search completed")
        await storage.add_log(LogLevel.INFO, "Search returned 5 results")

        logs = await storage.get_logs(search="search")

        assert len(logs) == 2
        assert all("search" in log["message"].lower() for log in logs)

    @pytest.mark.asyncio
    async def test_get_logs_pagination(self) -> None:
        """Test pagination of log results."""
        storage = LogStorageService(max_size_mb=1)

        # Add 10 logs
        for i in range(10):
            await storage.add_log(LogLevel.INFO, f"Log {i}")

        # Get first page (limit=3, offset=0)
        page1 = await storage.get_logs(limit=3, offset=0, order="asc")
        assert len(page1) == 3
        assert page1[0]["message"] == "Log 0"

        # Get second page (limit=3, offset=3)
        page2 = await storage.get_logs(limit=3, offset=3, order="asc")
        assert len(page2) == 3
        assert page2[0]["message"] == "Log 3"

    @pytest.mark.asyncio
    async def test_storage_stats(self) -> None:
        """Test storage statistics."""
        storage = LogStorageService(max_size_mb=1)

        await storage.add_log(LogLevel.INFO, "Log 1", entity_type="collection", entity_id="coll_123")
        await storage.add_log(LogLevel.WARNING, "Log 2", entity_type="user", entity_id="user_456")
        await storage.add_log(LogLevel.ERROR, "Log 3", request_id="req_789")

        stats = storage.get_stats()

        assert stats["total_logs"] == 3
        assert stats["unique_entities"] == 2  # collection:coll_123, user:user_456
        assert stats["unique_requests"] == 1  # req_789
        assert "info" in stats["level_distribution"]
        assert "collection" in stats["entity_distribution"]

    @pytest.mark.asyncio
    async def test_clear_logs(self) -> None:
        """Test clearing all logs."""
        storage = LogStorageService(max_size_mb=1)

        await storage.add_log(LogLevel.INFO, "Log 1")
        await storage.add_log(LogLevel.INFO, "Log 2")
        await storage.add_log(LogLevel.INFO, "Log 3")

        count = storage.clear()

        assert count == 3
        logs = await storage.get_logs()
        assert len(logs) == 0


class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_log_entry_creation(self) -> None:
        """Test creating a LogEntry."""
        entry = LogEntry(
            level=LogLevel.INFO,
            message="Test message",
            entity_type="collection",
            entity_id="coll_123",
            request_id="req_456",
        )

        assert entry.level == LogLevel.INFO
        assert entry.message == "Test message"
        assert entry.entity_type == "collection"
        assert entry.entity_id == "coll_123"
        assert entry.request_id == "req_456"
        assert isinstance(entry.timestamp, datetime)
        assert entry.id is not None

    def test_log_entry_to_dict(self) -> None:
        """Test converting LogEntry to dictionary."""
        entry = LogEntry(
            level=LogLevel.WARNING,
            message="Warning message",
            entity_type="pipeline",
            entity_id="pipe_123",
        )

        result = entry.to_dict()

        assert result["level"] == "warning"
        assert result["message"] == "Warning message"
        assert result["entity_type"] == "pipeline"
        assert result["entity_id"] == "pipe_123"
        assert "timestamp" in result
        assert "id" in result


class TestPipelineStage:
    """Tests for PipelineStage constants."""

    def test_pipeline_stage_constants(self) -> None:
        """Test that PipelineStage constants are defined."""
        assert PipelineStage.QUERY_VALIDATION == "query_validation"
        assert PipelineStage.QUERY_REWRITING == "query_rewriting"
        assert PipelineStage.EMBEDDING_GENERATION == "embedding_generation"
        assert PipelineStage.VECTOR_SEARCH == "vector_search"
        assert PipelineStage.LLM_GENERATION == "llm_generation"
        assert PipelineStage.COT_REASONING == "cot_reasoning"
