"""Search router for RAG Modulo API.

This module provides FastAPI router endpoints for search operations,
including RAG (Retrieval-Augmented Generation) queries that combine
document retrieval with LLM-based answer generation.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from rag_solution.core.dependencies import get_current_user
from rag_solution.file_management.database import get_db
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.search_service import SearchService

router = APIRouter(prefix="/api/search", tags=["search"])


def get_search_service(
    db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]
) -> SearchService:
    """
    Dependency to create a new SearchService instance with the database session and settings.

    Args:
        db (Session): Database session from dependency injection
        settings (Settings): Application settings from dependency injection

    Returns:
        SearchService: Initialized search service instance
    """
    return SearchService(db, settings)


@router.post(
    "",
    response_model=SearchOutput,
    summary="Question LLM in a scope of documents added to selected collection",
    description="Submit question to LLM providing a collection of documents as a context",
    responses={
        200: {"description": "LLM response generated successfully"},
        400: {"description": "Invalid input data"},
        401: {"description": "Unauthorized"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"},
    },
)
async def search(
    search_input: SearchInput,
    current_user: Annotated[dict, Depends(get_current_user)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchOutput:
    """
    Process a search query through the RAG pipeline.

    SECURITY: Requires authentication. User ID is extracted from JWT token.

    Args:
        search_input (SearchInput): Input data containing question and collection ID
        current_user (dict): Authenticated user from JWT token
        search_service (SearchService): The search service instance from dependency injection

    Returns:
        SearchOutput: Contains the generated answer, source documents, and evaluation info

    Raises:
        HTTPException: With appropriate status code and error detail
    """
    try:
        # SECURITY FIX: Set user_id from authenticated session (never trust client input)
        # Standardize JWT user ID extraction - use "uuid" as the standard field
        user_id_from_token = current_user.get("uuid")

        if not user_id_from_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in authentication token",
            )

        # Override user_id from token (security best practice)
        search_input.user_id = UUID(user_id_from_token) if isinstance(user_id_from_token, str) else user_id_from_token

        result: SearchOutput = await search_service.search(search_input)
        return result
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing search: {e!s}"
        ) from e
