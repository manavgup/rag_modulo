"""Search router for RAG Modulo API.

This module provides FastAPI router endpoints for search operations,
including RAG (Retrieval-Augmented Generation) queries that combine
document retrieval with LLM-based answer generation.
"""

from typing import Annotated

from core.config import Settings, get_settings
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"},
    },
)
async def search(
    search_input: SearchInput,
    search_service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchOutput:
    """
    Process a search query through the RAG pipeline.

    Args:
        search_input (SearchInput): Input data containing question and collection ID
        search_service (SearchService): The search service instance from dependency injection

    Returns:
        SearchOutput: Contains the generated answer, source documents, and evaluation info

    Raises:
        HTTPException: With appropriate status code and error detail
    """
    try:
        print(f"🔍 ROUTER: Received search request: {search_input.question}")
        print(f"🔍 ROUTER: Config metadata: {search_input.config_metadata}")
        result: SearchOutput = await search_service.search(search_input)
        print(f"🔍 ROUTER: Search completed, cot_output type: {type(result.cot_output)}")
        return result
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing search: {e!s}"
        ) from e
