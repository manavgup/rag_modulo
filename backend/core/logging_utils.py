import logging
import logging.handlers
from pathlib import Path
from typing import Any


# Lazy import to avoid test isolation issues
def get_app_settings() -> Any:
    from core.config import get_settings

    return get_settings()


def setup_logging(log_dir: Path | None = None) -> None:
    """Configure logging for the entire application."""

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Configure root logger
    root_logger = logging.getLogger()

    # Get log level safely with fallback for test isolation
    try:
        settings = get_app_settings()
        log_level = getattr(settings, "log_level", "INFO")
        # Handle case where settings might be mocked during tests
        if hasattr(log_level, "_mock_name") or not isinstance(log_level, str):
            log_level = "INFO"
        root_logger.setLevel(log_level)
    except (ImportError, AttributeError, TypeError):
        # Fallback to INFO if settings cannot be loaded (e.g., during test isolation)
        root_logger.setLevel("INFO")

    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if log_dir is provided
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "rag_modulo.log",
            maxBytes=10485760,  # 10MB
            backupCount=5,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure third-party loggers
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


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)
