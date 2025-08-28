import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI
from sqlalchemy import inspect, text
from starlette.middleware.sessions import SessionMiddleware

# Logging
from core.logging_utils import setup_logging, get_logger

# Middleware & Config
from core.authentication_middleware import AuthenticationMiddleware
from core.loggingcors_middleware import LoggingCORSMiddleware
from core.authorization import authorize_dependency
from core.config import settings

# Database
from rag_solution.file_management.database import Base, engine, get_db

# Models
from rag_solution.models.user import User
from rag_solution.models.collection import Collection
from rag_solution.models.file import File
from rag_solution.models.user_collection import UserCollection
from rag_solution.models.user_team import UserTeam
from rag_solution.models.team import Team
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.models.llm_provider import LLMProvider
from rag_solution.models.llm_model import LLMModel
from rag_solution.models.pipeline import PipelineConfig
# Routers
from rag_solution.router.collection_router import router as collection_router
from rag_solution.router.team_router import router as team_router
from rag_solution.router.user_router import router as user_router
from rag_solution.router.health_router import router as health_router
from rag_solution.router.auth_router import router as auth_router
from rag_solution.router.search_router import router as search_router

# Services
from rag_solution.services.system_initialization_service import SystemInitializationService

# Setup logging
log_dir = Path("/app/logs") if os.getenv("CONTAINER_ENV") else Path(__file__).parent.parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
setup_logging(log_dir)
logger = get_logger(__name__)


# -------------------------------------------
# 🛠️ LIFESPAN EVENTS
# -------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application lifespan events")

    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        logger.info(f"Existing tables: {existing_tables}")

        # Ensure all tables are created
        Base.metadata.create_all(bind=engine)
        logger.info("All tables have been ensured in the database.")

        # Database sanity check
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info(f"Database connection test result: {result.fetchone()}")

        # Initialize LLM Providers
        logger.info("Initializing LLM Providers...")
        with next(get_db()) as db:
            system_init_service = SystemInitializationService(db)
            providers = system_init_service.initialize_providers(raise_on_error=True)
            logger.info(f"Initialized providers: {', '.join(p.name for p in providers)}")

    except Exception as e:
        logger.error(f"Application startup failed: {e}", exc_info=True)
        raise SystemExit(1)

    yield

    logger.info("Application shutdown complete.")


# -------------------------------------------
# 🚀 APPLICATION INITIALIZATION
# -------------------------------------------
app = FastAPI(
    lifespan=lifespan,
    title="RAG Modulo API",
    description="API for interacting with a fully customizable RAG solution",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.ibm_client_secret or "default_secret",
    session_cookie="rag_modulo_session",
    max_age=3600,
)

app.add_middleware(
    LoggingCORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend", "https://prepiam.ice.ibmcloud.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-User-UUID"],
)

app.add_middleware(AuthenticationMiddleware)

# Routers
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(collection_router)
app.include_router(user_router)
app.include_router(team_router)
app.include_router(search_router)


# -------------------------------------------
# 📊 CUSTOM OPENAPI SCHEMA
# -------------------------------------------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = app.openapi()
    app.openapi_schema = openapi_schema
    return openapi_schema


app.openapi = custom_openapi
