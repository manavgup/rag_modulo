import os
import sys

print("Python path:", sys.path)
print("Current working directory:", os.getcwd())
print("Contents of /app:", os.listdir('/app'))
print("Contents of /app/backend:", os.listdir('/app/backend'))

import logging

from contextlib import asynccontextmanager
from backend.rag_solution.file_management.database import Base, engine
from sqlalchemy import inspect
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

try:
    from backend.core.config import settings
    print("Successfully imported settings")
except ImportError as e:
    print(f"Error importing settings: {e}")
    raise

from backend.core.config import settings
from backend.rag_solution.router.collection_router import router as collection_router
from backend.rag_solution.router.file_router import router as file_router
from backend.rag_solution.router.team_router import router as team_router
from backend.rag_solution.router.user_router import router as user_router
from backend.rag_solution.router.health_router import router as health_router

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)
logger.info("Main module is being imported")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("****Starting database initialization")
    try:
        # Log all table names before creation
        inspector = inspect(engine)
        tables_before = inspector.get_table_names()
        logger.info(f"Tables before creation: {tables_before}")

        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Base.metadata.create_all() completed")

        # Log all table names after creation
        tables_after = inspector.get_table_names()
        logger.info(f"Tables after creation: {tables_after}")

        # Check for the Teams table
        if 'teams' in tables_after:
            logger.info("Teams table exists in the database")
        else:
            logger.warning("Teams table does not exist in the database")
            
        # Log all models in Base.metadata
        logger.info("Models in Base.metadata:")
        for table_name, table in Base.metadata.tables.items():
            logger.info(f"  - {table_name}: {table}")

    except Exception as e:
        logger.error(f"Error during database initialization: {e}", exc_info=True)
        raise

    yield
    # Shutdown: you can add cleanup code here if needed   

# Initialize FastAPI app
app = FastAPI(
    lifespan=lifespan,
    title="RAG Modulo API",
    description="API for interacting with a fully customizable RAG solution",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI endpoint
    redoc_url="/redoc"  # ReDoc endpoint
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(collection_router)
app.include_router(file_router)
app.include_router(team_router)
app.include_router(user_router)
app.include_router(health_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="RAG MODULO API",
        version="1.0.0",
        description="API for interacting with a fully customizable RAG solution",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
