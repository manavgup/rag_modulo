"""User router aggregator for managing all user-related operations."""

from fastapi import APIRouter

from .user_routes import (
    base,
    collection_routes,
    file_routes,
    llm_routes,
    pipeline_routes,
    prompt_routes,
    provider_routes,
)

router = APIRouter(prefix="/api/users", tags=["users"])

# Include all user-related routes
router.include_router(base.router)
router.include_router(llm_routes.router)
router.include_router(prompt_routes.router)
router.include_router(pipeline_routes.router)
router.include_router(collection_routes.router)
router.include_router(file_routes.router)
router.include_router(provider_routes.router)
