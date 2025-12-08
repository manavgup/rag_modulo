"""RAG Modulo FastAPI Application.

This module contains the main FastAPI application for the RAG Modulo system,
including middleware configuration, router registration, database initialization,
and LLM provider setup.
"""

import contextlib
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from sqlalchemy import inspect, text
from starlette.middleware.sessions import SessionMiddleware

# Middleware & Config
from core.authentication_middleware import AuthenticationMiddleware
from core.config import get_settings

# Logging
from core.logging_utils import get_logger, setup_logging
from core.loggingcors_middleware import LoggingCORSMiddleware

# Database
from rag_solution.file_management.database import Base, engine, get_db
from rag_solution.router.agent_config_router import collection_agent_router, config_router as agent_config_router
from rag_solution.router.agent_router import router as agent_router

# Models
from rag_solution.router.auth_router import router as auth_router

# Routers
from rag_solution.router.chat_router import router as chat_router
from rag_solution.router.collection_router import router as collection_router
from rag_solution.router.conversation_router import router as conversation_router
from rag_solution.router.dashboard_router import router as dashboard_router
from rag_solution.router.health_router import router as health_router
from rag_solution.router.mcp_router import router as mcp_router
from rag_solution.router.podcast_router import router as podcast_router
from rag_solution.router.runtime_config_router import router as runtime_config_router
from rag_solution.router.search_router import router as search_router
from rag_solution.router.team_router import router as team_router
from rag_solution.router.token_warning_router import router as token_warning_router
from rag_solution.router.user_router import router as user_router
from rag_solution.router.voice_router import router as voice_router
from rag_solution.router.websocket_router import router as websocket_router

# Services
from rag_solution.services.system_initialization_service import SystemInitializationService

# Setup logging
log_dir = Path("/app/logs") if os.getenv("CONTAINER_ENV") else Path(__file__).parent.parent / "logs"

# Only create log directory if not in testing mode
if not os.getenv("TESTING"):
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        setup_logging(log_dir)
    except PermissionError:
        # Fallback to current directory if we can't create logs directory
        log_dir = Path.cwd() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        setup_logging(log_dir)
else:
    # In testing mode, just set up logging without creating directories
    setup_logging(log_dir)
logger = get_logger(__name__)


def validate_production_security() -> None:
    """Validate security configuration to prevent dangerous misconfigurations in production.

    Raises:
        RuntimeError: If insecure configuration detected in production environment
    """
    settings = get_settings()
    environment = os.getenv("ENVIRONMENT", "development").lower()

    # Prevent SKIP_AUTH in production
    if environment == "production" and settings.skip_auth:
        error_msg = (
            "🚨 SECURITY ERROR: SKIP_AUTH=true is not allowed in production environment. "
            "This would allow unauthenticated access to the application. "
            "Set SKIP_AUTH=false or remove the SKIP_AUTH variable from production .env"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Log warning if SKIP_AUTH is enabled in any environment
    if settings.skip_auth:
        logger.warning("⚠️  SKIP_AUTH is enabled - authentication is bypassed!")
        logger.warning("⚠️  This should ONLY be used in development/testing environments")
        logger.warning("⚠️  Current environment: %s", environment)


# -------------------------------------------
# 🛠️ LIFESPAN EVENTS
# -------------------------------------------
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events.

    Handles database initialization, table creation, and LLM provider setup
    during application startup, and cleanup during shutdown.

    Args:
        _app: FastAPI application instance

    Yields:
        None: Control back to the application

    Raises:
        SystemExit: If critical initialization fails
    """
    logger.info("Starting application lifespan events")

    # Validate security configuration before proceeding
    validate_production_security()

    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        logger.info("Existing tables: %s", existing_tables)

        # Ensure all tables are created
        Base.metadata.create_all(bind=engine)
        logger.info("All tables have been ensured in the database.")

        # Database sanity check
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("Database connection test result: %s", result.fetchone())

        # Initialize LLM Providers
        logger.info("Initializing LLM Providers...")
        db_gen = get_db()
        try:
            db = next(db_gen)

            # Clear any cached provider instances to ensure fresh initialization
            # This is critical when .env settings change between restarts
            from rag_solution.generation.providers.factory import LLMProviderFactory

            settings = get_settings()
            factory = LLMProviderFactory(db, settings)
            factory.cleanup_all()
            logger.info("Cleared cached provider instances")

            system_init_service = SystemInitializationService(db, settings)
            providers = system_init_service.initialize_providers(raise_on_error=True)
            logger.info("Initialized providers: %s", ", ".join(p.name for p in providers))

            # Initialize default users (mock user in development mode)
            success = system_init_service.initialize_default_users(raise_on_error=True)
            if success:
                logger.info("Default users initialized successfully")
            else:
                logger.warning("Default users initialization skipped or failed")
        except StopIteration:
            logger.error("Failed to get database session")
            return
        finally:
            with contextlib.suppress(StopIteration):
                next(db_gen)

    except Exception as e:
        logger.error("Application startup failed: %s", e, exc_info=True)
        raise SystemExit(1) from e

    yield

    logger.info("Application shutdown complete.")


# -------------------------------------------
# 🚀 APPLICATION INITIALIZATION
# -------------------------------------------

# OpenAPI tags metadata for API documentation
tags_metadata = [
    {
        "name": "agents",
        "description": "AI Agent management with SPIFFE-based workload identity. "
        "Register, manage, and authenticate AI agents using SPIRE for secure "
        "machine-to-machine communication.",
        "externalDocs": {
            "description": "SPIFFE Integration Architecture",
            "url": "https://spiffe.io/",
        },
    },
    {
        "name": "auth",
        "description": "User authentication and authorization endpoints.",
    },
    {
        "name": "collections",
        "description": "Document collection management operations.",
    },
    {
        "name": "search",
        "description": "RAG search and query operations.",
    },
    {
        "name": "users",
        "description": "User profile and settings management.",
    },
    {
        "name": "teams",
        "description": "Team management and collaboration.",
    },
]

app = FastAPI(
    lifespan=lifespan,
    title="RAG Modulo API",
    description="API for interacting with a fully customizable RAG solution",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
)

# Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=get_settings().ibm_client_secret or "default_secret",
    session_cookie="rag_modulo_session",
    max_age=3600,
)

app.add_middleware(
    LoggingCORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://frontend",
        "https://prepiam.ice.ibmcloud.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-User-UUID"],
)

app.add_middleware(AuthenticationMiddleware)

# Routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(mcp_router)
app.include_router(dashboard_router)
app.include_router(health_router)
app.include_router(collection_router)
app.include_router(podcast_router)
app.include_router(runtime_config_router)
app.include_router(user_router)
app.include_router(team_router)
app.include_router(search_router)
app.include_router(token_warning_router)
app.include_router(voice_router)
app.include_router(websocket_router)
app.include_router(agent_router)
app.include_router(agent_config_router)
app.include_router(collection_agent_router)


# Root endpoint
@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint that provides basic API information."""
    return {
        "message": "RAG Modulo API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


# -------------------------------------------
# 📊 CUSTOM OPENAPI SCHEMA
# -------------------------------------------

# OpenAPI tag metadata for improved documentation organization
OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "Health check endpoints for monitoring service availability",
    },
    {
        "name": "auth",
        "description": "Authentication and authorization endpoints",
    },
    {
        "name": "users",
        "description": "User management and profile operations",
    },
    {
        "name": "teams",
        "description": "Team management and membership operations",
    },
    {
        "name": "collections",
        "description": "Document collection management and configuration",
    },
    {
        "name": "search",
        "description": "RAG search operations with Chain of Thought reasoning",
    },
    {
        "name": "chat",
        "description": "Conversational AI chat interface",
    },
    {
        "name": "conversations",
        "description": "Conversation history and session management",
    },
    {
        "name": "agents",
        "description": (
            "AI agent management with SPIFFE/SPIRE workload identity. "
            "Provides registration, capability management, and JWT-SVID validation "
            "for machine-to-machine authentication."
        ),
        "externalDocs": {
            "description": "SPIFFE Integration Architecture",
            "url": "https://spiffe.io/docs/latest/spire-about/spire-concepts/",
        },
    },
    {
        "name": "agent-configs",
        "description": (
            "Agent configuration management for the 3-stage search pipeline. "
            "Create and manage agent configurations for pre-search, post-search, "
            "and response stages. Reference: GitHub Issue #697."
        ),
    },
    {
        "name": "collection-agents",
        "description": (
            "Collection-agent associations for the search pipeline. "
            "Associate agent configurations with collections and manage "
            "execution priorities. Reference: GitHub Issue #697."
        ),
    },
    {
        "name": "podcast",
        "description": "AI-powered podcast generation from document collections",
    },
    {
        "name": "voice",
        "description": "Voice synthesis and audio preview operations",
    },
    {
        "name": "dashboard",
        "description": "Dashboard data and analytics endpoints",
    },
    {
        "name": "runtime-config",
        "description": "Runtime configuration management",
    },
    {
        "name": "token-warning",
        "description": "Token usage warnings and limits",
    },
    {
        "name": "websocket",
        "description": "WebSocket connections for real-time updates",
    },
]


def custom_openapi() -> dict[str, Any]:
    """Generate custom OpenAPI schema for the application.

    Creates and caches the OpenAPI schema using FastAPI's default generation.
    This function prevents recursion issues and provides consistent API documentation.

    Returns:
        dict[str, Any]: The OpenAPI schema dictionary
    """
    if app.openapi_schema:
        return app.openapi_schema
    # Use the default FastAPI openapi generation without recursion
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=OPENAPI_TAGS,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]
