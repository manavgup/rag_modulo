"""CLI command classes for RAG Modulo.

This package contains command classes that implement the business logic
for CLI operations, wrapping API calls and providing user-friendly interfaces.
"""

from typing import Final

from .auth import AuthCommands
from .collections import CollectionCommands
from .config import ConfigCommands
from .documents import DocumentCommands
from .health import HealthCommands
from .search import SearchCommands
from .users import UserCommands

__all__: Final[list[str]] = [
    "AuthCommands",
    "CollectionCommands",
    "ConfigCommands",
    "DocumentCommands",
    "HealthCommands",
    "SearchCommands",
    "UserCommands",
]
