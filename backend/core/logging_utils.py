import logging
import os
from typing import Optional
from pathlib import Path
import logging.handlers
from core.config import settings

def setup_logging(log_dir: Optional[Path] = None) -> None:
    """Configure logging for the entire application."""
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

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
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure third-party loggers
    logging.getLogger('ibm-watson-machine-learning').setLevel(logging.ERROR)
    logging.getLogger('ibm-watsonx-ai').setLevel(logging.ERROR)
    logging.getLogger('ibm_watsonx_ai').setLevel(logging.ERROR)
    logging.getLogger('ibm_watsonx_ai.wml_resource').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    # Suppress SQLAlchemy logging
    sql_level = logging.CRITICAL
    logging.getLogger('sqlalchemy').setLevel(sql_level)
    logging.getLogger('sqlalchemy.engine').setLevel(sql_level)
    logging.getLogger('sqlalchemy.engine.base.Engine').setLevel(sql_level)
    logging.getLogger('sqlalchemy.dialects').setLevel(sql_level)
    logging.getLogger('sqlalchemy.pool').setLevel(sql_level)
    logging.getLogger('sqlalchemy.orm').setLevel(sql_level)

    

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)
