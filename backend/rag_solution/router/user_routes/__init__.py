"""User routes package for organizing user-related endpoints."""

from . import (
    base,
    llm_routes,
    prompt_routes,
    pipeline_routes,
    collection_routes,
    file_routes,
    provider_routes
)

__all__ = [
    'base',
    'llm_routes',
    'prompt_routes',
    'pipeline_routes',
    'collection_routes',
    'file_routes',
    'provider_routes'
]
