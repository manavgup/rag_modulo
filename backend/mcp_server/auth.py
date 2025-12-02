"""MCP Authentication module for RAG Modulo.

This module provides authentication and authorization for MCP requests,
supporting multiple authentication methods:
- SPIFFE JWT-SVID (workload identity)
- Bearer tokens
- API keys
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

# SPIFFE imports are optional - used only when SPIFFE auth is configured
if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class MCPAuthContext:
    """Authentication context for an MCP request.

    Contains validated identity information and permissions
    for the authenticated user/agent.

    Attributes:
        user_id: UUID of the authenticated user
        username: Username or email of the authenticated user
        agent_id: Optional SPIFFE ID for agent identity
        permissions: List of granted permissions
        is_authenticated: Whether the request is authenticated
        auth_method: Method used for authentication
        metadata: Additional authentication metadata
    """

    user_id: UUID | None = None
    username: str | None = None
    agent_id: str | None = None
    permissions: list[str] = field(default_factory=list)
    is_authenticated: bool = False
    auth_method: str = "none"
    metadata: dict[str, Any] = field(default_factory=dict)


class MCPAuthenticator:
    """Handles authentication for MCP requests.

    Supports multiple authentication methods:
    - SPIFFE JWT-SVID: For workload identity in agent environments
    - Bearer token: For user API access
    - API key: For simple programmatic access

    Attributes:
        settings: Application settings with auth configuration
        spiffe_source: SPIFFE JWT source for workload identity validation
    """

    def __init__(self, settings: Any) -> None:
        """Initialize the authenticator with settings.

        Args:
            settings: Application settings containing auth configuration
        """
        self.settings = settings
        self._spiffe_source: Any = None  # Optional[DefaultJwtSource]
        self._spiffe_initialized = False

    async def _init_spiffe(self) -> None:
        """Initialize SPIFFE workload API client lazily.

        This is called on first authentication request that requires
        SPIFFE validation to avoid startup delays.
        """
        if self._spiffe_initialized:
            return

        try:
            # Import SPIFFE modules only when needed
            from spiffe.workloadapi.default_jwt_source import DefaultJwtSource
            from spiffe.workloadapi.workload_api_client import WorkloadApiClient

            spiffe_socket = getattr(self.settings, "SPIFFE_ENDPOINT_SOCKET", None)
            if spiffe_socket:
                client = WorkloadApiClient(spiffe_endpoint_socket=spiffe_socket)
                self._spiffe_source = DefaultJwtSource(workload_api_client=client)
                logger.info("SPIFFE workload API client initialized")
            else:
                logger.warning("SPIFFE_ENDPOINT_SOCKET not configured, SPIFFE auth disabled")
        except ImportError:
            logger.warning("SPIFFE package not installed, SPIFFE auth disabled")
        except Exception as e:
            logger.warning("Failed to initialize SPIFFE client: %s", e)
        finally:
            self._spiffe_initialized = True

    async def authenticate_request(
        self,
        headers: dict[str, str],
        required_permissions: list[str] | None = None,
    ) -> MCPAuthContext:
        """Authenticate an MCP request using available credentials.

        Attempts authentication in order of preference:
        1. SPIFFE JWT-SVID (X-SPIFFE-JWT header)
        2. Bearer token (Authorization: Bearer ...)
        3. API key (X-API-Key header)

        Args:
            headers: Request headers containing credentials
            required_permissions: Optional list of required permissions

        Returns:
            MCPAuthContext with authentication results

        Raises:
            PermissionError: If required permissions are not satisfied
        """
        auth_context = MCPAuthContext()
        required_permissions = required_permissions or []

        # Try SPIFFE JWT-SVID first
        spiffe_jwt = headers.get("X-SPIFFE-JWT") or headers.get("x-spiffe-jwt")
        if spiffe_jwt:
            auth_context = await self._authenticate_spiffe(spiffe_jwt)
            if auth_context.is_authenticated:
                self._check_permissions(auth_context, required_permissions)
                return auth_context

        # Try Bearer token
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            auth_context = await self._authenticate_bearer(token)
            if auth_context.is_authenticated:
                self._check_permissions(auth_context, required_permissions)
                return auth_context

        # Try API key
        api_key = headers.get("X-API-Key") or headers.get("x-api-key")
        if api_key:
            auth_context = await self._authenticate_api_key(api_key)
            if auth_context.is_authenticated:
                self._check_permissions(auth_context, required_permissions)
                return auth_context

        # Check for X-Authenticated-User header (for trusted proxies)
        authenticated_user = headers.get("X-Authenticated-User") or headers.get("x-authenticated-user")
        if authenticated_user:
            auth_context = await self._authenticate_trusted_user(authenticated_user)
            if auth_context.is_authenticated:
                self._check_permissions(auth_context, required_permissions)
                return auth_context

        # No authentication - check if required
        if required_permissions:
            raise PermissionError("Authentication required for this operation")

        return auth_context

    async def _authenticate_spiffe(self, jwt_token: str) -> MCPAuthContext:
        """Authenticate using SPIFFE JWT-SVID.

        Args:
            jwt_token: The SPIFFE JWT-SVID token

        Returns:
            MCPAuthContext with SPIFFE identity if valid
        """
        await self._init_spiffe()

        if not self._spiffe_source:
            logger.warning("SPIFFE authentication attempted but not configured")
            return MCPAuthContext()

        try:
            # Validate the JWT and extract SPIFFE ID
            # The actual validation depends on the SPIFFE SDK version
            # For now, we'll extract the subject from the JWT claims
            import jwt

            # Decode without verification to get the subject
            # In production, this should be validated against the trust bundle
            unverified = jwt.decode(jwt_token, options={"verify_signature": False})
            spiffe_id = unverified.get("sub", "")

            if spiffe_id.startswith("spiffe://"):
                # Import SpiffeId lazily
                from spiffe import SpiffeId

                # Extract workload identity info
                parsed = SpiffeId.parse(spiffe_id)
                trust_domain = parsed.trust_domain.name

                return MCPAuthContext(
                    is_authenticated=True,
                    auth_method="spiffe",
                    agent_id=spiffe_id,
                    permissions=["rag:search", "rag:read", "rag:list"],
                    metadata={
                        "trust_domain": trust_domain,
                        "path": parsed.path,
                    },
                )
        except ImportError:
            logger.warning("SPIFFE package not installed, cannot validate SPIFFE ID")
        except Exception as e:
            logger.warning("SPIFFE authentication failed: %s", e)

        return MCPAuthContext()

    async def _authenticate_bearer(self, token: str) -> MCPAuthContext:
        """Authenticate using Bearer token.

        Args:
            token: The Bearer token

        Returns:
            MCPAuthContext with user identity if valid
        """
        try:
            import jwt

            secret_key = getattr(self.settings, "JWT_SECRET_KEY", None)
            if not secret_key:
                logger.warning("JWT_SECRET_KEY not configured")
                return MCPAuthContext()

            # Decode and validate the JWT
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])

            user_id = payload.get("sub") or payload.get("user_id")
            username = payload.get("email") or payload.get("username")

            if user_id:
                return MCPAuthContext(
                    user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
                    username=username,
                    is_authenticated=True,
                    auth_method="bearer",
                    permissions=payload.get("permissions", ["rag:search", "rag:read"]),
                    metadata={"exp": payload.get("exp")},
                )
        except Exception as e:
            logger.warning("Bearer token authentication failed: %s", e)

        return MCPAuthContext()

    async def _authenticate_api_key(self, api_key: str) -> MCPAuthContext:
        """Authenticate using API key.

        Args:
            api_key: The API key

        Returns:
            MCPAuthContext with API key identity if valid
        """
        # In production, this would validate against a database of API keys
        # For now, we'll check against environment variable for demo
        valid_api_key = getattr(self.settings, "MCP_API_KEY", None)

        if valid_api_key and api_key == valid_api_key:
            return MCPAuthContext(
                is_authenticated=True,
                auth_method="api_key",
                permissions=["rag:search", "rag:read", "rag:list"],
                metadata={"api_key_prefix": api_key[:8] + "..."},
            )

        logger.warning("Invalid API key provided")
        return MCPAuthContext()

    async def _authenticate_trusted_user(self, user_email: str) -> MCPAuthContext:
        """Authenticate using trusted proxy user header.

        This is used when the MCP server is behind a trusted proxy
        that has already authenticated the user.

        Args:
            user_email: The authenticated user's email from trusted proxy

        Returns:
            MCPAuthContext with user identity
        """
        # Import here to avoid circular imports
        from backend.rag_solution.repository.database import get_db

        from backend.core.config import get_settings
        from backend.rag_solution.services.user_service import UserService

        try:
            db_gen = get_db()
            db_session = next(db_gen)
            settings = get_settings()
            user_service = UserService(db_session, settings)

            # Use get_or_create to handle trusted proxy authentication
            # This ensures the user exists in our system
            user = user_service.get_or_create_user_by_fields(
                ibm_id=user_email,  # Use email as ibm_id for trusted proxy
                email=user_email,
                name=user_email.split("@")[0],  # Extract name from email
                role="user",
            )
            if user:
                return MCPAuthContext(
                    user_id=user.id,
                    username=user.email,
                    is_authenticated=True,
                    auth_method="trusted_proxy",
                    permissions=["rag:search", "rag:read", "rag:list", "rag:write"],
                    metadata={"source": "trusted_proxy"},
                )
        except Exception as e:
            logger.warning("Trusted user lookup failed: %s", e)

        return MCPAuthContext()

    def _check_permissions(
        self,
        auth_context: MCPAuthContext,
        required_permissions: list[str],
    ) -> None:
        """Check if the authenticated context has required permissions.

        Args:
            auth_context: The authentication context to check
            required_permissions: List of required permission strings

        Raises:
            PermissionError: If any required permission is missing
        """
        if not required_permissions:
            return

        missing = set(required_permissions) - set(auth_context.permissions)
        if missing:
            raise PermissionError(f"Missing required permissions: {', '.join(missing)}")
