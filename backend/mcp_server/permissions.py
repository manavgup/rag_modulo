"""MCP Permission constants for RAG Modulo.

This module defines permission constants used throughout the MCP server
for authorization and access control. Centralizing permissions here prevents
hardcoding and ensures consistency across the codebase.

Permission Format:
    Permissions follow the pattern: "rag:{action}"

Actions:
    - search: Perform semantic search queries
    - read: Read document content and metadata
    - write: Create, update, or delete documents
    - list: List collections and resources
    - generate: Use LLM generation features
    - pipeline: Execute data pipelines
    - cot: Use Chain of Thought reasoning
    - admin: Administrative operations
    - podcast: Generate podcasts from content
    - ingest: Ingest documents into collections
"""

from typing import Final


class MCPPermissions:
    """Permission constants for MCP operations.

    These permissions control access to various RAG Modulo features
    through the MCP interface.
    """

    # Core RAG operations
    SEARCH: Final[str] = "rag:search"
    READ: Final[str] = "rag:read"
    WRITE: Final[str] = "rag:write"
    LIST: Final[str] = "rag:list"

    # Advanced features
    GENERATE: Final[str] = "rag:generate"
    PIPELINE: Final[str] = "rag:pipeline"
    COT: Final[str] = "rag:cot"

    # Content creation
    PODCAST: Final[str] = "rag:podcast"
    INGEST: Final[str] = "rag:ingest"

    # Administration
    ADMIN: Final[str] = "rag:admin"


# Permission sets for different authentication methods
class DefaultPermissionSets:
    """Default permission sets for different authentication methods."""

    # Basic read-only access for API keys
    API_KEY: Final[list[str]] = [
        MCPPermissions.SEARCH,
        MCPPermissions.READ,
        MCPPermissions.LIST,
    ]

    # Standard user access via Bearer token
    BEARER: Final[list[str]] = [
        MCPPermissions.SEARCH,
        MCPPermissions.READ,
    ]

    # Trusted proxy user access
    TRUSTED_PROXY: Final[list[str]] = [
        MCPPermissions.SEARCH,
        MCPPermissions.READ,
        MCPPermissions.LIST,
        MCPPermissions.WRITE,
    ]

    # Default agent access (when no capabilities specified)
    DEFAULT_AGENT: Final[list[str]] = [
        MCPPermissions.SEARCH,
        MCPPermissions.READ,
        MCPPermissions.LIST,
    ]

    # Full access for admin agents
    ADMIN_AGENT: Final[list[str]] = [
        MCPPermissions.SEARCH,
        MCPPermissions.READ,
        MCPPermissions.WRITE,
        MCPPermissions.LIST,
        MCPPermissions.GENERATE,
        MCPPermissions.PIPELINE,
        MCPPermissions.COT,
        MCPPermissions.PODCAST,
        MCPPermissions.INGEST,
        MCPPermissions.ADMIN,
    ]


# Tool-to-permission mapping for authorization
TOOL_PERMISSIONS: Final[dict[str, list[str]]] = {
    "rag_search": [MCPPermissions.SEARCH],
    "rag_list_collections": [MCPPermissions.LIST],
    "rag_ingest": [MCPPermissions.INGEST, MCPPermissions.WRITE],
    "rag_generate_podcast": [MCPPermissions.PODCAST, MCPPermissions.READ],
    "rag_smart_questions": [MCPPermissions.READ],
    "rag_get_document": [MCPPermissions.READ],
}
