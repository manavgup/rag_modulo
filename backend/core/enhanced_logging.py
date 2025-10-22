"""Enhanced Logging Service Implementation.

This module implements structured logging with dual output formats (JSON/text),
entity context tracking, and in-memory log storage for the RAG Modulo application.

Based on patterns from IBM mcp-context-forge but adapted for RAG-specific needs.

Example:
    >>> from core.enhanced_logging import get_logger, log_operation
    >>> from core.logging_context import pipeline_stage_context
    >>>
    >>> logger = get_logger("rag.search")
    >>>
    >>> async def search(collection_id: str, user_id: str):
    ...     with log_operation(logger, "search_documents", "collection", collection_id, user_id=user_id):
    ...         with pipeline_stage_context("query_rewriting"):
    ...             logger.info("Rewriting query", extra={"query": "example"})
"""

import logging
import logging.handlers
import os
from asyncio import AbstractEventLoop, get_running_loop

from pythonjsonlogger import jsonlogger

from core.log_storage_service import LogLevel, LogStorageService

# Global handlers will be created lazily
_file_handler: logging.Handler | None = None
_text_handler: logging.StreamHandler | None = None
_storage_handler: logging.Handler | None = None

# Text formatter
_text_formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# JSON formatter
_json_formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(name)s %(levelname)s %(message)s %(context)s %(entity_type)s %(entity_id)s %(execution_time_ms)s"
)


def _get_file_handler(
    log_file: str = "rag_modulo.log",
    log_folder: str | None = "logs",
    log_rotation_enabled: bool = True,
    log_max_size_mb: int = 10,
    log_backup_count: int = 5,
    log_filemode: str = "a",
    log_format: str = "json",
) -> logging.Handler:
    """Get or create the file handler.

    Args:
        log_file: Log filename
        log_folder: Log folder path
        log_rotation_enabled: Enable log rotation
        log_max_size_mb: Maximum log file size in MB
        log_backup_count: Number of backup files to keep
        log_filemode: File mode (a=append, w=write)
        log_format: Log format (json or text)

    Returns:
        logging.Handler: Either a RotatingFileHandler or regular FileHandler

    Raises:
        ValueError: If file logging is disabled or no log file specified
    """
    global _file_handler
    if _file_handler is None:
        if not log_file:
            raise ValueError("No log file specified")

        # Ensure log folder exists
        if log_folder:
            os.makedirs(log_folder, exist_ok=True)
            log_path = os.path.join(log_folder, log_file)
        else:
            log_path = log_file

        # Create appropriate handler based on rotation settings
        if log_rotation_enabled:
            max_bytes = log_max_size_mb * 1024 * 1024  # Convert MB to bytes
            _file_handler = logging.handlers.RotatingFileHandler(
                log_path, maxBytes=max_bytes, backupCount=log_backup_count, mode=log_filemode
            )
        else:
            _file_handler = logging.FileHandler(log_path, mode=log_filemode)

        # Set formatter based on format type
        if log_format == "json":
            _file_handler.setFormatter(_json_formatter)
        else:
            _file_handler.setFormatter(_text_formatter)

    return _file_handler


def _get_text_handler() -> logging.StreamHandler:
    """Get or create the text handler for console output.

    Returns:
        logging.StreamHandler: The stream handler for console logging
    """
    global _text_handler
    if _text_handler is None:
        _text_handler = logging.StreamHandler()
        _text_handler.setFormatter(_text_formatter)
    return _text_handler


class StorageHandler(logging.Handler):
    """Custom logging handler that stores logs in LogStorageService."""

    def __init__(self, storage_service: LogStorageService) -> None:
        """Initialize the storage handler.

        Args:
            storage_service: The LogStorageService instance to store logs in
        """
        super().__init__()
        self.storage = storage_service
        self.loop: AbstractEventLoop | None = None

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to storage.

        Args:
            record: The LogRecord to emit
        """
        if not self.storage:
            return

        # Map Python log levels to LogLevel enum
        level_map = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.ERROR,
            "CRITICAL": LogLevel.CRITICAL,
        }

        log_level = level_map.get(record.levelname, LogLevel.INFO)

        # Extract context from record if available
        context = getattr(record, "context", None)
        if context is None:
            # Fall back to getting context from ContextVar
            from core.logging_context import get_context

            ctx = get_context()
            context = ctx.to_dict() if ctx else {}

        # Extract entity context
        entity_type = getattr(record, "entity_type", context.get("entity_type") if isinstance(context, dict) else None)
        entity_id = getattr(record, "entity_id", context.get("entity_id") if isinstance(context, dict) else None)
        entity_name = getattr(record, "entity_name", context.get("entity_name") if isinstance(context, dict) else None)
        request_id = context.get("request_id") if isinstance(context, dict) else None
        operation = context.get("operation") if isinstance(context, dict) else None
        pipeline_stage = context.get("pipeline_stage") if isinstance(context, dict) else None
        execution_time_ms = getattr(record, "execution_time_ms", None)

        # Format the message
        try:
            message = self.format(record)
        except Exception:
            message = record.getMessage()

        # Extract additional data from record
        data = None
        if hasattr(record, "__dict__"):
            # Collect non-standard attributes as metadata
            standard_attrs = {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "context",
                "entity_type",
                "entity_id",
                "entity_name",
                "execution_time_ms",
            }
            extra_data = {k: v for k, v in record.__dict__.items() if k not in standard_attrs and not k.startswith("_")}
            if extra_data:
                data = extra_data

        # Store the log asynchronously
        try:
            # Get or create event loop
            if not self.loop:
                try:
                    self.loop = get_running_loop()
                except RuntimeError:
                    # No running loop, can't store
                    return

            # Schedule the coroutine
            import asyncio

            asyncio.run_coroutine_threadsafe(
                self.storage.add_log(
                    level=log_level,
                    message=message,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    logger=record.name,
                    request_id=request_id,
                    operation=operation,
                    pipeline_stage=pipeline_stage,
                    execution_time_ms=execution_time_ms,
                    data=data,
                ),
                self.loop,
            )
        except Exception:
            # Silently fail to avoid logging recursion
            pass


class LoggingService:
    """Enhanced logging service for RAG Modulo.

    Implements structured logging with:
    - Dual output formats (JSON for production, text for development)
    - Entity context tracking (collection, user, pipeline, document)
    - Request correlation IDs
    - Pipeline stage tracking
    - In-memory log storage for querying
    - Performance timing integration
    """

    def __init__(self) -> None:
        """Initialize logging service."""
        self._loggers: dict[str, logging.Logger] = {}
        self._storage: LogStorageService | None = None
        self._initialized = False

    async def initialize(
        self,
        log_level: str = "INFO",
        log_format: str = "text",
        log_to_file: bool = True,
        log_file: str = "rag_modulo.log",
        log_folder: str | None = "logs",
        log_rotation_enabled: bool = True,
        log_max_size_mb: int = 10,
        log_backup_count: int = 5,
        log_filemode: str = "a",
        log_storage_enabled: bool = True,
        log_buffer_size_mb: int = 5,
    ) -> None:
        """Initialize logging service with configuration.

        Args:
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: Output format (text or json)
            log_to_file: Enable file logging
            log_file: Log filename
            log_folder: Log folder path
            log_rotation_enabled: Enable log rotation
            log_max_size_mb: Maximum log file size in MB
            log_backup_count: Number of backup files to keep
            log_filemode: File mode (a=append, w=write)
            log_storage_enabled: Enable in-memory log storage
            log_buffer_size_mb: Log storage buffer size in MB
        """
        if self._initialized:
            return

        root_logger = logging.getLogger()
        self._loggers[""] = root_logger

        # Clear existing handlers to avoid duplicates
        root_logger.handlers.clear()

        # Set log level
        log_level_value = getattr(logging, log_level.upper())
        root_logger.setLevel(log_level_value)

        # Always add console/text handler for stdout/stderr
        text_handler = _get_text_handler()
        text_handler.setLevel(log_level_value)
        root_logger.addHandler(text_handler)

        # Add file handler if enabled
        if log_to_file and log_file:
            try:
                file_handler = _get_file_handler(
                    log_file=log_file,
                    log_folder=log_folder,
                    log_rotation_enabled=log_rotation_enabled,
                    log_max_size_mb=log_max_size_mb,
                    log_backup_count=log_backup_count,
                    log_filemode=log_filemode,
                    log_format=log_format,
                )
                file_handler.setLevel(log_level_value)
                root_logger.addHandler(file_handler)

                if log_rotation_enabled:
                    logging.info(
                        f"File logging enabled with rotation: {log_folder or '.'}/{log_file} "
                        f"(max: {log_max_size_mb}MB, backups: {log_backup_count})"
                    )
                else:
                    logging.info(f"File logging enabled (no rotation): {log_folder or '.'}/{log_file}")
            except Exception as e:
                logging.warning(f"Failed to initialize file logging: {e}")
        else:
            logging.info("File logging disabled - logging to stdout/stderr only")

        # Initialize log storage if enabled
        if log_storage_enabled:
            self._storage = LogStorageService(max_size_mb=log_buffer_size_mb)

            # Add storage handler to capture all logs
            global _storage_handler
            _storage_handler = StorageHandler(self._storage)
            _storage_handler.setFormatter(_text_formatter)
            _storage_handler.setLevel(log_level_value)
            root_logger.addHandler(_storage_handler)

            logging.info(f"Log storage initialized with {log_buffer_size_mb}MB buffer")

        # Configure third-party loggers to reduce noise
        self._configure_third_party_loggers()

        logging.info(f"Logging service initialized (level={log_level}, format={log_format})")
        self._initialized = True

    def _configure_third_party_loggers(self) -> None:
        """Configure third-party loggers to reduce noise."""
        # Suppress noisy third-party libraries
        logging.getLogger("ibm-watson-machine-learning").setLevel(logging.ERROR)
        logging.getLogger("ibm-watsonx-ai").setLevel(logging.ERROR)
        logging.getLogger("ibm_watsonx_ai").setLevel(logging.ERROR)
        logging.getLogger("ibm_watsonx_ai.wml_resource").setLevel(logging.ERROR)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)

        # Suppress SQLAlchemy logging
        sql_level = logging.CRITICAL
        logging.getLogger("sqlalchemy").setLevel(sql_level)
        logging.getLogger("sqlalchemy.engine").setLevel(sql_level)
        logging.getLogger("sqlalchemy.engine.base.Engine").setLevel(sql_level)
        logging.getLogger("sqlalchemy.dialects").setLevel(sql_level)
        logging.getLogger("sqlalchemy.pool").setLevel(sql_level)
        logging.getLogger("sqlalchemy.orm").setLevel(sql_level)

    async def shutdown(self) -> None:
        """Shutdown logging service."""
        logging.info("Logging service shutdown")
        self._initialized = False

    def get_logger(self, name: str) -> logging.Logger:
        """Get or create logger instance.

        Args:
            name: Logger name

        Returns:
            Logger instance configured with enhanced logging
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)

            # Don't add handlers to child loggers - let them inherit from root
            # This prevents duplicate logging while maintaining dual output
            logger.propagate = True

            # Track the logger
            self._loggers[name] = logger

        return self._loggers[name]

    def get_storage(self) -> LogStorageService | None:
        """Get the log storage service if available.

        Returns:
            LogStorageService instance or None if not initialized
        """
        return self._storage


# Global logging service instance
_logging_service: LoggingService | None = None


def get_logging_service() -> LoggingService:
    """Get or create the global logging service instance.

    Returns:
        LoggingService instance
    """
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    This is a convenience function that uses the global logging service.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Hello world")
    """
    service = get_logging_service()
    return service.get_logger(name)


async def initialize_logging(
    log_level: str = "INFO",
    log_format: str = "text",
    log_to_file: bool = True,
    log_file: str = "rag_modulo.log",
    log_folder: str | None = "logs",
    log_rotation_enabled: bool = True,
    log_max_size_mb: int = 10,
    log_backup_count: int = 5,
    log_filemode: str = "a",
    log_storage_enabled: bool = True,
    log_buffer_size_mb: int = 5,
) -> LoggingService:
    """Initialize the global logging service.

    Args:
        log_level: Minimum log level
        log_format: Output format (text or json)
        log_to_file: Enable file logging
        log_file: Log filename
        log_folder: Log folder path
        log_rotation_enabled: Enable log rotation
        log_max_size_mb: Maximum log file size in MB
        log_backup_count: Number of backup files to keep
        log_filemode: File mode
        log_storage_enabled: Enable in-memory log storage
        log_buffer_size_mb: Log storage buffer size in MB

    Returns:
        Initialized LoggingService instance
    """
    service = get_logging_service()
    await service.initialize(
        log_level=log_level,
        log_format=log_format,
        log_to_file=log_to_file,
        log_file=log_file,
        log_folder=log_folder,
        log_rotation_enabled=log_rotation_enabled,
        log_max_size_mb=log_max_size_mb,
        log_backup_count=log_backup_count,
        log_filemode=log_filemode,
        log_storage_enabled=log_storage_enabled,
        log_buffer_size_mb=log_buffer_size_mb,
    )
    return service
