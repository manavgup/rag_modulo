import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from sqlalchemy import inspect, text
from auth.oidc import verify_jwt_token
import jwt

# Import  core modules
from core.authentication_middleware import AuthenticationMiddleware
# from backend.core.authorization_decorator import AuthorizationMiddleware
from core.loggingcors_middleware import LoggingCORSMiddleware
from core.authorization import authorize_dependency
from core.config import settings

# Import all models
from rag_solution.file_management.database import Base, engine, get_db
from rag_solution.models.user import User
from rag_solution.models.collection import Collection
from rag_solution.models.file import File
from rag_solution.models.user_collection import UserCollection
from rag_solution.models.user_team import UserTeam
from rag_solution.models.team import Team

# Import all routers
from rag_solution.file_management.database import Base, engine
from rag_solution.router.collection_router import router as collection_router
from rag_solution.router.team_router import router as team_router
from rag_solution.router.user_router import router as user_router
from rag_solution.router.health_router import router as health_router
from rag_solution.router.auth_router import router as auth_router
from rag_solution.router.search_router import router as search_router

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting database initialization")
    try:
        inspector = inspect(engine)
        tables_before = inspector.get_table_names()
        logger.info(f"Tables before creation: {tables_before}")

        # Ensure all models are in the Base.metadata
        for model in [User, Collection, File, UserCollection, UserTeam, Team]:
            if model.__table__ not in Base.metadata.tables.values():
                Base.metadata.tables[model.__tablename__] = model.__table__

        Base.metadata.create_all(bind=engine)
        logger.info("Base.metadata.create_all() completed")

        tables_after = inspector.get_table_names()
        logger.info(f"Tables after creation: {tables_after}")

        # Check if all tables exist
        expected_tables = {'users', 'collections', 'files', 'user_collections', 'user_teams', 'teams'}
        missing_tables = expected_tables - set(tables_after)
        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}")
        else:
            logger.info("All expected tables exist in the database")

        logger.info("Models in Base.metadata:")
        for table_name, table in Base.metadata.tables.items():
            logger.info(f"  - {table_name}: {table}")

        # Try to execute a simple query to check database connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info(f"Database connection test result: {result.fetchone()}")

    except Exception as e:
        logger.error(f"Error during database initialization: {e}", exc_info=True)
        raise

    yield

    # Cleanup (if needed)
    logger.info("Shutting down")

app = FastAPI(
    lifespan=lifespan,
    title="RAG Modulo API",
    description="API for interacting with a fully customizable RAG solution",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add SessionMiddleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.ibm_client_secret,
    session_cookie="rag_modulo_session",
    max_age=3600,  # 1 hour
)

# Configure CORS
app.add_middleware(
    LoggingCORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend", "http://frontend:80", "https://prepiam.ice.ibmcloud.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-User-UUID"],
)

# Add Auth middleware
app.add_middleware(AuthenticationMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(collection_router)
app.include_router(user_router)
app.include_router(team_router)
app.include_router(search_router)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="RAG MODULO API",
        version="1.0.0",
        description="API for interacting with a fully customizable RAG solution",
        routes=app.routes,
    )

    def process_schema(schema, path=[]):
        if isinstance(schema, dict):
            for key, value in schema.items():
                if isinstance(value, type) and issubclass(value, BaseModel):
                    logging.warning(f"Found non-serializable model at path: {'.'.join(path + [key])}")
                    schema[key] = value.model_json_schema()
                else:
                    process_schema(value, path + [key])
        elif isinstance(schema, list):
            for i, item in enumerate(schema):
                process_schema(item, path + [str(i)])

    process_schema(openapi_schema)
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)