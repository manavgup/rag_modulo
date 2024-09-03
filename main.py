import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Secret
from sqlalchemy import inspect

from backend.core.config import settings
from backend.core.auth_middleware import AuthMiddleware
from backend.rag_solution.file_management.database import Base, engine
from backend.rag_solution.router.collection_router import router as collection_router
from backend.rag_solution.router.file_router import router as file_router
from backend.rag_solution.router.team_router import router as team_router
from backend.rag_solution.router.user_router import router as user_router
from backend.rag_solution.router.user_collection_router import router as user_collection_router
from backend.rag_solution.router.user_team_router import router as user_team_router
from backend.rag_solution.router.health_router import router as health_router
from backend.rag_solution.router.auth_router import router as auth_router
from backend.auth.oidc import get_current_user, oauth

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

class CustomSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if 'session' in request.scope:
            # Modify the Set-Cookie header to include SameSite and Secure attributes
            for key, value in response.headers.items():
                if key.lower() == 'set-cookie' and value.startswith('session='):
                    new_value = value + '; SameSite=None; Secure'
                    response.headers[key] = new_value
        return response
    
class LoggingCORSMiddleware(CORSMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            logger.debug(f"CORS Request: method={scope['method']}, path={scope['path']}")
            logger.debug(f"CORS Request headers: {scope['headers']}")
        
        response = await super().__call__(scope, receive, send)
        
        if scope["type"] == "http":
            logger.debug(f"CORS Response headers: {response.headers}")
        
        return response
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting database initialization")
    try:
        inspector = inspect(engine)
        tables_before = inspector.get_table_names()
        logger.info(f"Tables before creation: {tables_before}")

        Base.metadata.create_all(bind=engine)
        logger.info("Base.metadata.create_all() completed")

        tables_after = inspector.get_table_names()
        logger.info(f"Tables after creation: {tables_after}")

        if 'teams' in tables_after:
            logger.info("Teams table exists in the database")
        else:
            logger.warning("Teams table does not exist in the database")

        logger.info("Models in Base.metadata:")
        for table_name, table in Base.metadata.tables.items():
            logger.info(f"  - {table_name}: {table}")

    except Exception as e:
        logger.error(f"Error during database initialization: {e}", exc_info=True)
        raise

    yield

app = FastAPI(
    lifespan=lifespan,
    title="RAG Modulo API",
    description="API for interacting with a fully customizable RAG solution",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add SessionMiddleware first
app.add_middleware(
    SessionMiddleware,
    secret_key=Secret(settings.ibm_client_secret),
    session_cookie="session",
    max_age=86400  # 1 day in seconds
)

# Add the custom middleware after SessionMiddleware
app.add_middleware(CustomSessionMiddleware)

# Configure CORS
app.add_middleware(
    LoggingCORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend", "http://frontend:80", "https://prepiam.ice.ibmcloud.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Auth middleware last
app.add_middleware(AuthMiddleware)

async def auth_dependency(user: Annotated[dict, Depends(get_current_user)]):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

@app.middleware("http")
async def debug_middleware(request: Request, call_next):
    logger.debug("Middleware stack:")
    for middleware in app.user_middleware:
        logger.debug(f" - {middleware.__class__.__name__}")
    response = await call_next(request)
    return response

# Include routers
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(collection_router, dependencies=[Depends(auth_dependency)])
app.include_router(file_router, dependencies=[Depends(auth_dependency)])
app.include_router(team_router, dependencies=[Depends(auth_dependency)])
app.include_router(user_router, dependencies=[Depends(auth_dependency)])
app.include_router(user_collection_router, dependencies=[Depends(auth_dependency)])
app.include_router(user_team_router, dependencies=[Depends(auth_dependency)])


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