"""Log Storage Service Implementation.

This service provides in-memory storage for recent logs with entity context,
supporting filtering, pagination, and real-time streaming.

Based on patterns from IBM mcp-context-forge but adapted for RAG Modulo.
"""

import asyncio
import sys
import uuid
from collections import deque
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class LogLevel(str, Enum):
    """RFC 5424 log severity levels."""

    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"
    EMERGENCY = "emergency"


@dataclass
class LogEntry:
    """Simple log entry for in-memory storage.

    Attributes:
        id: Unique identifier for the log entry
        timestamp: When the log entry was created
        level: Severity level of the log
        entity_type: Type of entity (collection, user, pipeline, document)
        entity_id: ID of the related entity
        entity_name: Name of the related entity for display
        message: The log message
        logger: Logger name/source
        data: Additional structured data
        request_id: Associated request ID for tracing
        operation: Operation being performed
        pipeline_stage: RAG pipeline stage
        execution_time_ms: Operation execution time in milliseconds
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    level: LogLevel = LogLevel.INFO
    entity_type: str | None = None
    entity_id: str | None = None
    entity_name: str | None = None
    message: str = ""
    logger: str | None = None
    data: dict[str, Any] | None = None
    request_id: str | None = None
    operation: str | None = None
    pipeline_stage: str | None = None
    execution_time_ms: float | None = None
    _size: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        """Calculate memory size after initialization."""
        # Estimate memory size (rough approximation)
        self._size = sys.getsizeof(self.id)
        self._size += sys.getsizeof(self.timestamp)
        self._size += sys.getsizeof(self.level)
        self._size += sys.getsizeof(self.message)
        self._size += sys.getsizeof(self.entity_type) if self.entity_type else 0
        self._size += sys.getsizeof(self.entity_id) if self.entity_id else 0
        self._size += sys.getsizeof(self.entity_name) if self.entity_name else 0
        self._size += sys.getsizeof(self.logger) if self.logger else 0
        self._size += sys.getsizeof(self.data) if self.data else 0
        self._size += sys.getsizeof(self.request_id) if self.request_id else 0
        self._size += sys.getsizeof(self.operation) if self.operation else 0
        self._size += sys.getsizeof(self.pipeline_stage) if self.pipeline_stage else 0
        self._size += sys.getsizeof(self.execution_time_ms) if self.execution_time_ms else 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the log entry
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "message": self.message,
            "logger": self.logger,
            "data": self.data,
            "request_id": self.request_id,
            "operation": self.operation,
            "pipeline_stage": self.pipeline_stage,
            "execution_time_ms": self.execution_time_ms,
        }


class LogStorageService:
    """Service for storing and retrieving log entries in memory.

    Provides:
    - Size-limited circular buffer (configurable MB)
    - Entity context tracking
    - Real-time streaming
    - Filtering and pagination
    """

    def __init__(self, max_size_mb: int = 5) -> None:
        """Initialize log storage service.

        Args:
            max_size_mb: Maximum buffer size in megabytes (default: 5MB)
        """
        # Calculate max buffer size in bytes
        self._max_size_bytes = int(max_size_mb * 1024 * 1024)
        self._current_size_bytes = 0

        # Use deque for efficient append/pop operations
        self._buffer: deque[LogEntry] = deque()
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []

        # Indices for efficient filtering
        self._entity_index: dict[str, list[str]] = {}  # entity_key -> [log_ids]
        self._request_index: dict[str, list[str]] = {}  # request_id -> [log_ids]
        self._pipeline_stage_index: dict[str, list[str]] = {}  # stage -> [log_ids]

    async def add_log(
        self,
        level: LogLevel,
        message: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        entity_name: str | None = None,
        logger: str | None = None,
        data: dict[str, Any] | None = None,
        request_id: str | None = None,
        operation: str | None = None,
        pipeline_stage: str | None = None,
        execution_time_ms: float | None = None,
    ) -> LogEntry:
        """Add a log entry to storage.

        Args:
            level: Log severity level
            message: Log message
            entity_type: Type of entity (collection, user, pipeline, document)
            entity_id: ID of the related entity
            entity_name: Name of the related entity
            logger: Logger name/source
            data: Additional structured data
            request_id: Associated request ID for tracing
            operation: Operation being performed
            pipeline_stage: RAG pipeline stage
            execution_time_ms: Operation execution time

        Returns:
            The created LogEntry
        """
        log_entry = LogEntry(
            level=level,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            logger=logger,
            data=data,
            request_id=request_id,
            operation=operation,
            pipeline_stage=pipeline_stage,
            execution_time_ms=execution_time_ms,
        )

        # Add to buffer and update size
        self._buffer.append(log_entry)
        self._current_size_bytes += log_entry._size

        # Update indices BEFORE eviction so they can be cleaned up properly
        if entity_id:
            key = f"{entity_type}:{entity_id}" if entity_type else entity_id
            if key not in self._entity_index:
                self._entity_index[key] = []
            self._entity_index[key].append(log_entry.id)

        if request_id:
            if request_id not in self._request_index:
                self._request_index[request_id] = []
            self._request_index[request_id].append(log_entry.id)

        if pipeline_stage:
            if pipeline_stage not in self._pipeline_stage_index:
                self._pipeline_stage_index[pipeline_stage] = []
            self._pipeline_stage_index[pipeline_stage].append(log_entry.id)

        # Remove old entries if size limit exceeded
        while self._current_size_bytes > self._max_size_bytes and self._buffer:
            old_entry = self._buffer.popleft()
            self._current_size_bytes -= old_entry._size
            self._remove_from_indices(old_entry)

        # Notify subscribers
        await self._notify_subscribers(log_entry)

        return log_entry

    def _remove_from_indices(self, entry: LogEntry) -> None:
        """Remove entry from indices when evicted from buffer.

        Args:
            entry: LogEntry to remove from indices
        """
        # Remove from entity index
        if entry.entity_id:
            key = f"{entry.entity_type}:{entry.entity_id}" if entry.entity_type else entry.entity_id
            if key in self._entity_index:
                try:
                    self._entity_index[key].remove(entry.id)
                    if not self._entity_index[key]:
                        del self._entity_index[key]
                except ValueError:
                    pass

        # Remove from request index
        if entry.request_id and entry.request_id in self._request_index:
            try:
                self._request_index[entry.request_id].remove(entry.id)
                if not self._request_index[entry.request_id]:
                    del self._request_index[entry.request_id]
            except ValueError:
                pass

        # Remove from pipeline stage index
        if entry.pipeline_stage and entry.pipeline_stage in self._pipeline_stage_index:
            try:
                self._pipeline_stage_index[entry.pipeline_stage].remove(entry.id)
                if not self._pipeline_stage_index[entry.pipeline_stage]:
                    del self._pipeline_stage_index[entry.pipeline_stage]
            except ValueError:
                pass

    async def _notify_subscribers(self, log_entry: LogEntry) -> None:
        """Notify subscribers of new log entry.

        Args:
            log_entry: New log entry
        """
        message = {"type": "log_entry", "data": log_entry.to_dict()}

        # Remove dead subscribers
        dead_subscribers = []
        for queue in self._subscribers:
            try:
                # Non-blocking put with timeout
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # Skip if subscriber is too slow
                pass
            except Exception:
                # Mark for removal if queue is broken
                dead_subscribers.append(queue)

        # Clean up dead subscribers
        for queue in dead_subscribers:
            self._subscribers.remove(queue)

    async def get_logs(
        self,
        entity_type: str | None = None,
        entity_id: str | None = None,
        level: LogLevel | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        request_id: str | None = None,
        pipeline_stage: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "desc",
    ) -> list[dict[str, Any]]:
        """Get filtered log entries.

        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            level: Minimum log level
            start_time: Start of time range
            end_time: End of time range
            request_id: Filter by request ID
            pipeline_stage: Filter by pipeline stage
            search: Search in message text
            limit: Maximum number of results
            offset: Number of results to skip
            order: Sort order (asc or desc)

        Returns:
            List of matching log entries as dictionaries
        """
        # Start with all logs or filtered by indices
        if entity_id:
            key = f"{entity_type}:{entity_id}" if entity_type else entity_id
            log_ids = set(self._entity_index.get(key, []))
            candidates = [log for log in self._buffer if log.id in log_ids]
        elif request_id:
            log_ids = set(self._request_index.get(request_id, []))
            candidates = [log for log in self._buffer if log.id in log_ids]
        elif pipeline_stage:
            log_ids = set(self._pipeline_stage_index.get(pipeline_stage, []))
            candidates = [log for log in self._buffer if log.id in log_ids]
        else:
            candidates = list(self._buffer)

        # Apply filters
        filtered = []
        for log in candidates:
            # Entity type filter
            if entity_type and log.entity_type != entity_type:
                continue

            # Level filter
            if level and not self._meets_level_threshold(log.level, level):
                continue

            # Time range filters
            if start_time and log.timestamp < start_time:
                continue
            if end_time and log.timestamp > end_time:
                continue

            # Search filter
            if search and search.lower() not in log.message.lower():
                continue

            filtered.append(log)

        # Sort
        filtered.sort(key=lambda x: x.timestamp, reverse=order == "desc")

        # Paginate
        paginated = filtered[offset : offset + limit]

        # Convert to dictionaries
        return [log.to_dict() for log in paginated]

    def _meets_level_threshold(self, log_level: LogLevel, min_level: LogLevel) -> bool:
        """Check if log level meets minimum threshold.

        Args:
            log_level: Log level to check
            min_level: Minimum required level

        Returns:
            True if log level meets or exceeds minimum
        """
        level_values = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.NOTICE: 2,
            LogLevel.WARNING: 3,
            LogLevel.ERROR: 4,
            LogLevel.CRITICAL: 5,
            LogLevel.ALERT: 6,
            LogLevel.EMERGENCY: 7,
        }

        return level_values.get(log_level, 0) >= level_values.get(min_level, 0)

    async def subscribe(self) -> AsyncGenerator[dict[str, Any], None]:
        """Subscribe to real-time log updates.

        Yields:
            Log entry events as they occur
        """
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        try:
            while True:
                message = await queue.get()
                yield message
        finally:
            self._subscribers.remove(queue)

    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        level_counts: dict[LogLevel, int] = {}
        entity_counts: dict[str, int] = {}
        stage_counts: dict[str, int] = {}

        for log in self._buffer:
            # Count by level
            level_counts[log.level] = level_counts.get(log.level, 0) + 1

            # Count by entity type
            if log.entity_type:
                entity_counts[log.entity_type] = entity_counts.get(log.entity_type, 0) + 1

            # Count by pipeline stage
            if log.pipeline_stage:
                stage_counts[log.pipeline_stage] = stage_counts.get(log.pipeline_stage, 0) + 1

        return {
            "total_logs": len(self._buffer),
            "buffer_size_bytes": self._current_size_bytes,
            "buffer_size_mb": round(self._current_size_bytes / (1024 * 1024), 2),
            "max_size_mb": round(self._max_size_bytes / (1024 * 1024), 2),
            "usage_percent": round((self._current_size_bytes / self._max_size_bytes) * 100, 1),
            "unique_entities": len(self._entity_index),
            "unique_requests": len(self._request_index),
            "unique_pipeline_stages": len(self._pipeline_stage_index),
            "level_distribution": {level.value: count for level, count in level_counts.items()},
            "entity_distribution": entity_counts,
            "pipeline_stage_distribution": stage_counts,
        }

    def clear(self) -> int:
        """Clear all logs from buffer.

        Returns:
            Number of logs cleared
        """
        count = len(self._buffer)
        self._buffer.clear()
        self._entity_index.clear()
        self._request_index.clear()
        self._pipeline_stage_index.clear()
        self._current_size_bytes = 0
        return count
