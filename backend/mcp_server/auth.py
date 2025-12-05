"""MCP Authentication module for RAG Modulo.

This module provides authentication and authorization for MCP requests,
supporting multiple authentication methods:
- SPIFFE JWT-SVID (workload identity)
- Bearer tokens
- API keys

Security Notes:
    - SPIFFE JWT-SVID validation requires a running SPIRE agent
    - Fallback mode (when SPIRE unavailable) should only be used in development
    - All authentication failures are logged for security auditing
    - Timing attacks are mitigated using constant-time comparison
"""

import contextlib
import hmac
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

import jwt

from core.config import get_settings
from core.enhanced_logging import get_logger
from mcp_server.permissions import DefaultPermissionSets, MCPPermissions
from rag_solution.file_management.database import get_db
from rag_solution.models.user import User
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.user_service import UserService

# SPIFFE imports are optional - used only when SPIFFE auth is configured
if TYPE_CHECKING:
    from core.spiffe_auth import AgentPrincipal

logger = get_logger(__name__)

# Security: Check if we're in production mode
_IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"


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

        Uses the existing SPIFFEAuthenticator from backend/core/spiffe_auth.py
        for proper signature validation and trust domain verification.

        SECURITY: In production, signature validation is REQUIRED. The fallback
        mode (accepting tokens without signature validation) is ONLY allowed in
        non-production environments when SPIRE agent is unavailable.

        Args:
            jwt_token: The SPIFFE JWT-SVID token

        Returns:
            MCPAuthContext with SPIFFE identity if valid

        Raises:
            PermissionError: In production when signature validation fails
        """
        try:
            # Import the existing SPIFFE authenticator which has proper validation
            from core.spiffe_auth import get_spiffe_authenticator

            authenticator = get_spiffe_authenticator()

            # Validate the JWT-SVID with proper signature verification
            # The SPIFFEAuthenticator validates:
            # 1. Token format and SPIFFE ID structure
            # 2. Trust domain matches configuration
            # 3. Signature against SPIRE trust bundle (when available)
            # 4. Token expiration
            principal = authenticator.validate_jwt_svid(jwt_token)

            if principal is not None:
                # SECURITY CHECK: In production, require signature validation
                signature_validated = principal.metadata.get("signature_validated", False)
                if _IS_PRODUCTION and not signature_validated:
                    logger.error(
                        "SECURITY: Rejecting SPIFFE token without signature validation in production. "
                        "SPIFFE ID: %s. Ensure SPIRE agent is running and accessible.",
                        principal.spiffe_id,
                    )
                    return MCPAuthContext()

                if not signature_validated:
                    logger.warning(
                        "SPIFFE token accepted without signature validation (development mode). "
                        "SPIFFE ID: %s. This is NOT safe for production!",
                        principal.spiffe_id,
                    )

                # Map AgentPrincipal capabilities to MCP permissions
                mcp_permissions = self._map_agent_capabilities_to_permissions(principal)

                return MCPAuthContext(
                    is_authenticated=True,
                    auth_method="spiffe",
                    agent_id=principal.spiffe_id,
                    permissions=mcp_permissions,
                    metadata={
                        "trust_domain": principal.trust_domain,
                        "agent_type": principal.agent_type.value,
                        "capabilities": [cap.value for cap in principal.capabilities],
                        "signature_validated": signature_validated,
                    },
                )
        except ImportError:
            logger.warning("SPIFFE auth module not available")
        except Exception as e:
            logger.warning("SPIFFE authentication failed: %s", e)

        return MCPAuthContext()

    def _map_agent_capabilities_to_permissions(self, principal: "AgentPrincipal") -> list[str]:
        """Map SPIFFE agent capabilities to MCP permissions.

        Args:
            principal: The authenticated agent principal

        Returns:
            List of MCP permission strings
        """
        from core.spiffe_auth import AgentCapability

        # Mapping from SPIFFE capabilities to MCP permissions
        capability_to_permission = {
            AgentCapability.SEARCH_READ: MCPPermissions.SEARCH,
            AgentCapability.DOCUMENT_READ: MCPPermissions.READ,
            AgentCapability.DOCUMENT_WRITE: MCPPermissions.WRITE,
            AgentCapability.MCP_TOOL_INVOKE: MCPPermissions.LIST,
            AgentCapability.LLM_INVOKE: MCPPermissions.GENERATE,
            AgentCapability.PIPELINE_EXECUTE: MCPPermissions.PIPELINE,
            AgentCapability.COT_INVOKE: MCPPermissions.COT,
            AgentCapability.ADMIN: MCPPermissions.ADMIN,
        }

        permissions = []
        for cap in principal.capabilities:
            if cap in capability_to_permission:
                permissions.append(capability_to_permission[cap])

        # Ensure basic read permissions for any authenticated agent
        if not permissions:
            permissions = list(DefaultPermissionSets.DEFAULT_AGENT)

        return permissions

    async def _authenticate_bearer(self, token: str) -> MCPAuthContext:
        """Authenticate using Bearer token.

        Args:
            token: The Bearer token

        Returns:
            MCPAuthContext with user identity if valid
        """
        try:
            secret_key = getattr(self.settings, "JWT_SECRET_KEY", None)
            if not secret_key:
                logger.warning("JWT_SECRET_KEY not configured")
                return MCPAuthContext()

            # Decode and validate the JWT with expiration check
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=["HS256"],
                options={"verify_exp": True},  # Explicitly verify expiration
            )

            user_id = payload.get("sub") or payload.get("user_id")
            username = payload.get("email") or payload.get("username")

            if user_id:
                return MCPAuthContext(
                    user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
                    username=username,
                    is_authenticated=True,
                    auth_method="bearer",
                    permissions=payload.get("permissions", list(DefaultPermissionSets.BEARER)),
                    metadata={"exp": payload.get("exp")},
                )
        except Exception as e:
            logger.warning("Bearer token authentication failed: %s", e)

        return MCPAuthContext()

    async def _authenticate_api_key(self, api_key: str) -> MCPAuthContext:
        """Authenticate using API key.

        Uses constant-time comparison to prevent timing attacks.

        Args:
            api_key: The API key

        Returns:
            MCPAuthContext with API key identity if valid
        """
        # In production, this would validate against a database of API keys
        # For now, we'll check against environment variable for demo
        valid_api_key = getattr(self.settings, "MCP_API_KEY", None)

        # Use constant-time comparison to prevent timing attacks
        # hmac.compare_digest prevents timing attacks by comparing in constant time
        if valid_api_key and hmac.compare_digest(api_key.encode(), valid_api_key.encode()):
            return MCPAuthContext(
                is_authenticated=True,
                auth_method="api_key",
                permissions=list(DefaultPermissionSets.API_KEY),
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
        db_gen = None
        db_session = None
        try:
            db_gen = get_db()
            db_session = next(db_gen)
            settings = get_settings()

            # First, try to find existing user by email (not ibm_id)
            # This handles the case where user was created with a different ibm_id
            existing_user = db_session.query(User).filter(User.email == user_email).first()

            # Type annotation for user - can be User model or UserOutput schema
            user: User | UserOutput | None = None

            if existing_user:
                user = existing_user
                logger.debug("Found existing user by email: %s (id=%s)", user_email, user.id)
            else:
                # Create new user if not found by email
                user_service = UserService(db_session, settings)
                user = user_service.get_or_create_user_by_fields(
                    ibm_id=user_email,  # Use email as ibm_id for new trusted proxy users
                    email=user_email,
                    name=user_email.split("@")[0],  # Extract name from email
                    role="user",
                )
                logger.debug("Created new user for trusted proxy: %s (id=%s)", user_email, user.id)

            if user:
                return MCPAuthContext(
                    user_id=user.id,
                    username=user.email,
                    is_authenticated=True,
                    auth_method="trusted_proxy",
                    permissions=list(DefaultPermissionSets.TRUSTED_PROXY),
                    metadata={"source": "trusted_proxy"},
                )
        except Exception as e:
            logger.warning("Trusted user lookup failed: %s", e)
        finally:
            # Ensure proper cleanup of database session
            if db_gen is not None:
                with contextlib.suppress(StopIteration):
                    next(db_gen)

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
