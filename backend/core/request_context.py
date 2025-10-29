"""Request-scoped context management for caching user and session data.

This module provides thread-safe request-scoped caching to eliminate N+1 queries
by storing frequently accessed data (user, session) in context variables that persist
for the duration of a single HTTP request.

Following best practices from FastAPI and Starlette, we use contextvars for
thread-safe request isolation.
"""

import logging
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

# Context variables for request-scoped caching
# These are thread-safe and isolated per request
_request_user_cache: ContextVar[dict[str, Any] | None] = ContextVar("request_user_cache", default=None)
_request_session_cache: ContextVar[dict[str, Any] | None] = ContextVar("request_session_cache", default=None)


class RequestContext:
    """Request-scoped context for caching frequently accessed data.

    This class provides a clean API for storing and retrieving request-scoped data
    like user information and session data, eliminating redundant database queries
    within a single request.

    Example:
        >>> # In middleware or dependency
        >>> RequestContext.set_user(user_data)
        >>> RequestContext.set_session(session_data)
        >>>
        >>> # In service layer
        >>> user = RequestContext.get_user()
        >>> if user:
        >>>     # Use cached user data instead of querying database
        >>>     pass
    """

    @staticmethod
    def set_user(user_data: dict[str, Any]) -> None:
        """Set user data in request context.

        Args:
            user_data: Dictionary containing user information (id, email, name, etc.)
        """
        _request_user_cache.set(user_data)
        logger.debug("RequestContext: User data cached for request: %s", user_data.get("id"))

    @staticmethod
    def get_user() -> dict[str, Any] | None:
        """Get user data from request context.

        Returns:
            User data dictionary if cached, None otherwise
        """
        user = _request_user_cache.get()
        if user:
            logger.debug("RequestContext: Retrieved cached user: %s", user.get("id"))
        return user

    @staticmethod
    def set_session(session_data: dict[str, Any]) -> None:
        """Set session data in request context.

        Args:
            session_data: Dictionary containing session information
        """
        _request_session_cache.set(session_data)
        logger.debug("RequestContext: Session data cached for request")

    @staticmethod
    def get_session() -> dict[str, Any] | None:
        """Get session data from request context.

        Returns:
            Session data dictionary if cached, None otherwise
        """
        session = _request_session_cache.get()
        if session:
            logger.debug("RequestContext: Retrieved cached session")
        return session

    @staticmethod
    def clear() -> None:
        """Clear all request context data.

        This should be called after each request to prevent memory leaks
        and ensure context isolation between requests.
        """
        _request_user_cache.set(None)
        _request_session_cache.set(None)
        logger.debug("RequestContext: Cleared all context data")

    @staticmethod
    def has_user() -> bool:
        """Check if user data is cached in request context.

        Returns:
            True if user data is cached, False otherwise
        """
        return _request_user_cache.get() is not None

    @staticmethod
    def has_session() -> bool:
        """Check if session data is cached in request context.

        Returns:
            True if session data is cached, False otherwise
        """
        return _request_session_cache.get() is not None
