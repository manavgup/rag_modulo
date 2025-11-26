"""SPIFFE/SPIRE authentication module for agent workload identity.

This module provides authentication support for AI agents using SPIFFE JWT-SVIDs.
It integrates with the py-spiffe library to fetch and validate SPIFFE identities,
enabling zero-trust agent authentication for the RAG Modulo platform.

Key components:
- SPIFFEConfig: Configuration for SPIFFE/SPIRE integration
- SPIFFEAuthenticator: Handles JWT-SVID fetching and validation
- AgentPrincipal: Represents an authenticated agent identity

Reference: https://spiffe.io/docs/latest/spire-about/spire-concepts/
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

import jwt
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# SPIFFE ID pattern: spiffe://trust-domain/path
SPIFFE_ID_PATTERN = re.compile(r"^spiffe://([a-zA-Z0-9._-]+)/(.+)$")

# Default SPIRE Workload API socket path
DEFAULT_SPIFFE_ENDPOINT_SOCKET = "unix:///var/run/spire/agent.sock"


class AgentType(str, Enum):
    """Enumeration of supported agent types in RAG Modulo.

    Each agent type has specific capabilities and is assigned
    a unique SPIFFE ID path.
    """

    SEARCH_ENRICHER = "search-enricher"
    COT_REASONING = "cot-reasoning"
    QUESTION_DECOMPOSER = "question-decomposer"
    SOURCE_ATTRIBUTION = "source-attribution"
    ENTITY_EXTRACTION = "entity-extraction"
    ANSWER_SYNTHESIS = "answer-synthesis"
    CUSTOM = "custom"


class AgentCapability(str, Enum):
    """Enumeration of agent capabilities for access control.

    Capabilities define what actions an agent is allowed to perform.
    """

    MCP_TOOL_INVOKE = "mcp:tool:invoke"
    SEARCH_READ = "search:read"
    SEARCH_WRITE = "search:write"
    LLM_INVOKE = "llm:invoke"
    PIPELINE_EXECUTE = "pipeline:execute"
    DOCUMENT_READ = "document:read"
    DOCUMENT_WRITE = "document:write"
    COT_INVOKE = "cot:invoke"
    AGENT_SPAWN = "agent:spawn"
    ADMIN = "admin"


# Default capabilities per agent type
AGENT_TYPE_CAPABILITIES: dict[AgentType, list[AgentCapability]] = {
    AgentType.SEARCH_ENRICHER: [
        AgentCapability.MCP_TOOL_INVOKE,
        AgentCapability.SEARCH_READ,
    ],
    AgentType.COT_REASONING: [
        AgentCapability.SEARCH_READ,
        AgentCapability.LLM_INVOKE,
        AgentCapability.PIPELINE_EXECUTE,
        AgentCapability.COT_INVOKE,
    ],
    AgentType.QUESTION_DECOMPOSER: [
        AgentCapability.SEARCH_READ,
        AgentCapability.LLM_INVOKE,
    ],
    AgentType.SOURCE_ATTRIBUTION: [
        AgentCapability.DOCUMENT_READ,
        AgentCapability.SEARCH_READ,
    ],
    AgentType.ENTITY_EXTRACTION: [
        AgentCapability.DOCUMENT_READ,
        AgentCapability.LLM_INVOKE,
    ],
    AgentType.ANSWER_SYNTHESIS: [
        AgentCapability.SEARCH_READ,
        AgentCapability.LLM_INVOKE,
        AgentCapability.COT_INVOKE,
    ],
    AgentType.CUSTOM: [],  # Custom agents have no default capabilities
}


@dataclass
class SPIFFEConfig:
    """Configuration for SPIFFE/SPIRE integration.

    Attributes:
        enabled: Whether SPIFFE authentication is enabled
        endpoint_socket: Path to SPIRE agent workload API socket
        trust_domain: The SPIFFE trust domain (e.g., "rag-modulo.example.com")
        default_audiences: Default audiences for JWT-SVID requests
        svid_ttl_seconds: Time-to-live for SVIDs in seconds
        fallback_to_jwt: Whether to fall back to legacy JWT if SPIRE unavailable
    """

    enabled: bool = False
    endpoint_socket: str = DEFAULT_SPIFFE_ENDPOINT_SOCKET
    trust_domain: str = "rag-modulo.example.com"
    default_audiences: list[str] = field(default_factory=lambda: ["backend-api", "mcp-gateway"])
    svid_ttl_seconds: int = 3600  # 1 hour
    fallback_to_jwt: bool = True

    @classmethod
    def from_env(cls) -> SPIFFEConfig:
        """Create SPIFFEConfig from environment variables.

        Environment variables (aligned with .env.example):
            SPIFFE_ENABLED: Enable SPIFFE authentication (default: false)
            SPIFFE_ENDPOINT_SOCKET: Workload API socket path
            SPIFFE_TRUST_DOMAIN: Trust domain name
            SPIFFE_JWT_AUDIENCES: Comma-separated list of audiences
            SPIFFE_SVID_TTL_SECONDS: SVID TTL in seconds
            SPIFFE_FALLBACK_TO_JWT: Enable JWT fallback (default: true)
        """
        enabled = os.getenv("SPIFFE_ENABLED", "false").lower() == "true"
        endpoint_socket = os.getenv("SPIFFE_ENDPOINT_SOCKET", DEFAULT_SPIFFE_ENDPOINT_SOCKET)
        trust_domain = os.getenv("SPIFFE_TRUST_DOMAIN", "rag-modulo.example.com")
        audiences_str = os.getenv("SPIFFE_JWT_AUDIENCES", "rag-modulo,mcp-gateway")
        default_audiences = [a.strip() for a in audiences_str.split(",") if a.strip()]
        svid_ttl = int(os.getenv("SPIFFE_SVID_TTL_SECONDS", "3600"))
        fallback_to_jwt = os.getenv("SPIFFE_FALLBACK_TO_JWT", "true").lower() == "true"

        return cls(
            enabled=enabled,
            endpoint_socket=endpoint_socket,
            trust_domain=trust_domain,
            default_audiences=default_audiences,
            svid_ttl_seconds=svid_ttl,
            fallback_to_jwt=fallback_to_jwt,
        )


class AgentPrincipal(BaseModel):
    """Represents an authenticated agent identity.

    This model captures the identity information extracted from a SPIFFE JWT-SVID
    or from the local agent registration.

    Attributes:
        spiffe_id: Full SPIFFE ID (e.g., "spiffe://rag-modulo.example.com/agent/search-enricher/abc123")
        trust_domain: The trust domain portion of the SPIFFE ID
        agent_type: The type of agent (from AgentType enum)
        agent_id: Unique identifier for this agent instance
        capabilities: List of capabilities this agent has
        audiences: Audiences this SVID is valid for
        issued_at: When the SVID was issued
        expires_at: When the SVID expires
        metadata: Additional metadata from the SVID or registration
    """

    spiffe_id: str = Field(..., description="Full SPIFFE ID")
    trust_domain: str = Field(..., description="Trust domain from SPIFFE ID")
    agent_type: AgentType = Field(..., description="Agent type classification")
    agent_id: str = Field(..., description="Unique agent instance identifier")
    capabilities: list[AgentCapability] = Field(default_factory=list, description="Agent capabilities")
    audiences: list[str] = Field(default_factory=list, description="Valid audiences")
    issued_at: datetime | None = Field(default=None, description="SVID issue time")
    expires_at: datetime | None = Field(default=None, description="SVID expiration time")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @classmethod
    def from_spiffe_id(
        cls,
        spiffe_id: str,
        capabilities: list[AgentCapability] | None = None,
        audiences: list[str] | None = None,
        issued_at: datetime | None = None,
        expires_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentPrincipal:
        """Create an AgentPrincipal from a SPIFFE ID string.

        Args:
            spiffe_id: Full SPIFFE ID (e.g., "spiffe://domain/agent/type/id")
            capabilities: Optional list of capabilities (defaults to type-based)
            audiences: Optional list of audiences
            issued_at: Optional issue timestamp
            expires_at: Optional expiration timestamp
            metadata: Optional additional metadata

        Returns:
            AgentPrincipal instance

        Raises:
            ValueError: If SPIFFE ID format is invalid
        """
        match = SPIFFE_ID_PATTERN.match(spiffe_id)
        if not match:
            raise ValueError(f"Invalid SPIFFE ID format: {spiffe_id}")

        trust_domain = match.group(1)
        path = match.group(2)

        # Parse path: expected format is "agent/{type}/{id}" or "agent/{type}"
        path_parts = path.split("/")
        if len(path_parts) < 2 or path_parts[0] != "agent":
            raise ValueError(f"Invalid agent SPIFFE ID path: {path}")

        agent_type_str = path_parts[1]
        try:
            agent_type = AgentType(agent_type_str)
        except ValueError:
            agent_type = AgentType.CUSTOM

        agent_id = path_parts[2] if len(path_parts) > 2 else agent_type_str

        # Use default capabilities for agent type if not provided
        if capabilities is None:
            capabilities = list(AGENT_TYPE_CAPABILITIES.get(agent_type, []))

        return cls(
            spiffe_id=spiffe_id,
            trust_domain=trust_domain,
            agent_type=agent_type,
            agent_id=agent_id,
            capabilities=capabilities,
            audiences=audiences or [],
            issued_at=issued_at,
            expires_at=expires_at,
            metadata=metadata or {},
        )

    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if this agent has a specific capability.

        Args:
            capability: The capability to check

        Returns:
            True if the agent has the capability
        """
        return capability in self.capabilities

    def has_any_capability(self, capabilities: list[AgentCapability]) -> bool:
        """Check if this agent has any of the specified capabilities.

        Args:
            capabilities: List of capabilities to check

        Returns:
            True if the agent has at least one of the capabilities
        """
        return any(cap in self.capabilities for cap in capabilities)

    def has_all_capabilities(self, capabilities: list[AgentCapability]) -> bool:
        """Check if this agent has all of the specified capabilities.

        Args:
            capabilities: List of capabilities to check

        Returns:
            True if the agent has all of the capabilities
        """
        return all(cap in self.capabilities for cap in capabilities)

    def is_valid_for_audience(self, audience: str) -> bool:
        """Check if this agent's SVID is valid for a specific audience.

        Args:
            audience: The audience to check

        Returns:
            True if the SVID is valid for the audience
        """
        return audience in self.audiences

    def is_expired(self) -> bool:
        """Check if this agent's SVID has expired.

        Returns:
            True if the SVID has expired
        """
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at


class SPIFFEAuthenticator:
    """Authenticator for SPIFFE JWT-SVIDs.

    This class handles:
    - Fetching JWT-SVIDs from the SPIRE agent via Workload API
    - Validating incoming JWT-SVIDs
    - Extracting agent identity from validated tokens
    - Graceful fallback when SPIRE is unavailable

    Usage:
        authenticator = SPIFFEAuthenticator()

        # Fetch SVID for outbound calls
        token = authenticator.fetch_jwt_svid(audiences=["mcp-gateway"])

        # Validate incoming SVID
        principal = authenticator.validate_jwt_svid(token)
    """

    def __init__(self, config: SPIFFEConfig | None = None) -> None:
        """Initialize the SPIFFE authenticator.

        Args:
            config: Optional SPIFFEConfig. If not provided, loads from environment.
        """
        self.config = config or SPIFFEConfig.from_env()
        self._workload_client: Any = None
        self._jwt_source: Any = None
        self._initialized = False
        self._spire_available = False

    def _initialize(self) -> bool:
        """Initialize the SPIFFE workload API client.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return self._spire_available

        if not self.config.enabled:
            logger.info("SPIFFE authentication is disabled")
            self._initialized = True
            self._spire_available = False
            return False

        try:
            # Set environment variable for py-spiffe
            os.environ.setdefault("SPIFFE_ENDPOINT_SOCKET", self.config.endpoint_socket)

            # Import py-spiffe (may not be available in all environments)
            from spiffe import JwtSource, WorkloadApiClient  # type: ignore[import-not-found]

            self._workload_client = WorkloadApiClient()
            self._jwt_source = JwtSource()
            self._spire_available = True
            self._initialized = True
            logger.info("SPIFFE authenticator initialized successfully")
            return True
        except ImportError:
            logger.warning("py-spiffe library not available, SPIFFE authentication disabled")
            self._initialized = True
            self._spire_available = False
            return False
        except Exception as e:
            logger.warning("Failed to initialize SPIFFE authenticator: %s", e)
            self._initialized = True
            self._spire_available = False
            return False

    @property
    def is_available(self) -> bool:
        """Check if SPIFFE authentication is available.

        Returns:
            True if SPIFFE is enabled and SPIRE agent is reachable
        """
        if not self._initialized:
            self._initialize()
        return self._spire_available

    def fetch_jwt_svid(self, audiences: list[str] | None = None) -> str | None:
        """Fetch a JWT-SVID from the SPIRE agent.

        Args:
            audiences: List of audiences for the JWT-SVID

        Returns:
            JWT-SVID token string, or None if unavailable
        """
        if not self._initialize():
            return None

        try:
            if audiences is None:
                audiences = self.config.default_audiences

            # Use JwtSource for auto-refreshing tokens
            with self._jwt_source as source:
                svid = source.fetch_svid(audience=set(audiences))
                return svid.token
        except Exception as e:
            logger.error("Failed to fetch JWT-SVID: %s", e)
            return None

    def validate_jwt_svid(self, token: str, required_audience: str | None = None) -> AgentPrincipal | None:
        """Validate a JWT-SVID and extract the agent principal.

        This method validates the JWT-SVID signature against the SPIRE trust bundle
        and extracts the agent identity information.

        SECURITY NOTE: By default, signature validation is REQUIRED. The fallback_to_jwt
        config option only controls whether we fall back when SPIRE is UNAVAILABLE,
        NOT when signature validation FAILS. Failed signature validation always rejects.

        Args:
            token: The JWT-SVID token string
            required_audience: Optional audience that must be present in the token

        Returns:
            AgentPrincipal if validation successful, None otherwise
        """
        try:
            # First, decode without verification to check if it's a SPIFFE JWT-SVID
            unverified = jwt.decode(token, options={"verify_signature": False})

            # Check if this is a SPIFFE JWT-SVID (has 'sub' claim with spiffe:// prefix)
            subject = unverified.get("sub", "")
            if not subject.startswith("spiffe://"):
                logger.debug("Token is not a SPIFFE JWT-SVID")
                return None

            # Validate trust domain matches our configuration
            match = SPIFFE_ID_PATTERN.match(subject)
            if not match:
                logger.warning("Invalid SPIFFE ID format in token: %s", subject)
                return None

            token_trust_domain = match.group(1)
            if token_trust_domain != self.config.trust_domain:
                logger.warning(
                    "SPIFFE ID trust domain mismatch: expected %s, got %s",
                    self.config.trust_domain,
                    token_trust_domain,
                )
                return None

            # Validate audience if required
            audiences = unverified.get("aud", [])
            if isinstance(audiences, str):
                audiences = [audiences]

            if required_audience and required_audience not in audiences:
                logger.warning("JWT-SVID missing required audience: %s", required_audience)
                return None

            # Signature validation - CRITICAL SECURITY CHECK
            signature_validated = False

            if self.is_available:
                try:
                    # Use workload client to validate signature with trust bundle
                    with self._workload_client as client:
                        jwt_bundle = client.fetch_jwt_bundles()
                        bundle = jwt_bundle.get_bundle_for_trust_domain(token_trust_domain)
                        if bundle:
                            # Validate token signature with bundle
                            bundle.validate_jwt_svid(token, audiences=set(audiences) if audiences else None)
                            signature_validated = True
                            logger.debug("JWT-SVID signature validated successfully")
                        else:
                            logger.error("No trust bundle found for domain: %s", token_trust_domain)
                            return None
                except Exception as e:
                    # SECURITY: Signature validation FAILED - always reject
                    logger.error(
                        "JWT-SVID signature validation FAILED: %s. Token rejected for security.",
                        e,
                    )
                    return None
            else:
                # SPIRE is not available
                if self.config.fallback_to_jwt:
                    # Allow fallback only when SPIRE is unavailable (not when validation fails)
                    logger.warning(
                        "SPIRE unavailable, accepting token without signature validation. "
                        "This is ONLY safe in development environments."
                    )
                else:
                    logger.error("SPIRE unavailable and fallback disabled. Token rejected.")
                    return None

            # Extract timestamps with UTC timezone
            issued_at = None
            expires_at = None
            if "iat" in unverified:
                issued_at = datetime.fromtimestamp(unverified["iat"], tz=UTC)
            if "exp" in unverified:
                expires_at = datetime.fromtimestamp(unverified["exp"], tz=UTC)

            # Create agent principal from SPIFFE ID
            principal = AgentPrincipal.from_spiffe_id(
                spiffe_id=subject,
                audiences=audiences,
                issued_at=issued_at,
                expires_at=expires_at,
                metadata={
                    "raw_claims": unverified,
                    "signature_validated": signature_validated,
                },
            )

            # Check expiration
            if principal.is_expired():
                logger.warning("JWT-SVID has expired")
                return None

            return principal

        except jwt.InvalidTokenError as e:
            logger.warning("Invalid JWT-SVID: %s", e)
            return None
        except ValueError as e:
            logger.warning("Failed to parse SPIFFE ID from JWT-SVID: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected error validating JWT-SVID: %s", e)
            return None

    def get_auth_headers(self, audiences: list[str] | None = None) -> dict[str, str]:
        """Get authentication headers with JWT-SVID for outbound requests.

        Args:
            audiences: List of audiences for the JWT-SVID

        Returns:
            Dictionary of headers to include in requests
        """
        token = self.fetch_jwt_svid(audiences)
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}


def is_spiffe_jwt_svid(token: str) -> bool:
    """Check if a token is a SPIFFE JWT-SVID.

    Args:
        token: JWT token string

    Returns:
        True if the token is a SPIFFE JWT-SVID
    """
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
        subject = unverified.get("sub", "")
        return subject.startswith("spiffe://")
    except Exception:
        return False


def parse_spiffe_id(spiffe_id: str) -> tuple[str, str] | None:
    """Parse a SPIFFE ID into trust domain and path.

    Args:
        spiffe_id: Full SPIFFE ID string

    Returns:
        Tuple of (trust_domain, path) or None if invalid
    """
    match = SPIFFE_ID_PATTERN.match(spiffe_id)
    if match:
        return (match.group(1), match.group(2))
    return None


def build_spiffe_id(trust_domain: str, agent_type: AgentType, agent_id: str | None = None) -> str:
    """Build a SPIFFE ID for an agent.

    Args:
        trust_domain: The trust domain (e.g., "rag-modulo.example.com")
        agent_type: The type of agent
        agent_id: Optional unique identifier for the agent instance

    Returns:
        Full SPIFFE ID string
    """
    if agent_id:
        return f"spiffe://{trust_domain}/agent/{agent_type.value}/{agent_id}"
    return f"spiffe://{trust_domain}/agent/{agent_type.value}"


# Global authenticator instance (lazy initialization)
_authenticator: SPIFFEAuthenticator | None = None


def get_spiffe_authenticator() -> SPIFFEAuthenticator:
    """Get the global SPIFFE authenticator instance.

    Returns:
        SPIFFEAuthenticator instance
    """
    global _authenticator
    if _authenticator is None:
        _authenticator = SPIFFEAuthenticator()
    return _authenticator


def require_capabilities(
    *required_capabilities: AgentCapability,
    require_all: bool = True,
) -> Any:
    """Decorator to enforce capability requirements on endpoint handlers.

    This decorator checks if the authenticated agent has the required capabilities
    before allowing access to the endpoint. It works with FastAPI's dependency
    injection system.

    Args:
        *required_capabilities: One or more capabilities required to access the endpoint
        require_all: If True, all capabilities are required. If False, any one suffices.

    Returns:
        FastAPI dependency that validates capabilities

    Example:
        @router.post("/search")
        @require_capabilities(AgentCapability.SEARCH_READ)
        async def search_endpoint(request: Request):
            ...

        @router.post("/admin")
        @require_capabilities(AgentCapability.ADMIN, AgentCapability.SEARCH_WRITE, require_all=True)
        async def admin_endpoint(request: Request):
            ...
    """
    from functools import wraps

    from fastapi import HTTPException, Request, status

    def decorator(func: Any) -> Any:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find the request object in args or kwargs
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")

            if request is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found in handler",
                )

            # Check if request has agent principal
            agent_principal: AgentPrincipal | None = getattr(request.state, "agent_principal", None)

            if agent_principal is None:
                # Not an agent request - check if we should allow user requests
                user = getattr(request.state, "user", None)
                if user:
                    # User requests are allowed by default (they have implicit capabilities)
                    return await func(*args, **kwargs)

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Verify agent has required capabilities
            if require_all:
                has_permission = agent_principal.has_all_capabilities(list(required_capabilities))
            else:
                has_permission = agent_principal.has_any_capability(list(required_capabilities))

            if not has_permission:
                capability_names = [cap.value for cap in required_capabilities]
                mode = "all of" if require_all else "any of"
                logger.warning(
                    "Agent %s denied access: missing %s capabilities %s (has: %s)",
                    agent_principal.spiffe_id,
                    mode,
                    capability_names,
                    [cap.value for cap in agent_principal.capabilities],
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Agent lacks required capabilities: {capability_names}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def get_agent_principal_from_request(request: Any) -> AgentPrincipal | None:
    """Extract agent principal from request state if present.

    This is a utility function for handlers that need to check agent identity
    without requiring it.

    Args:
        request: FastAPI Request object

    Returns:
        AgentPrincipal if request is from an authenticated agent, None otherwise
    """
    return getattr(request.state, "agent_principal", None)
