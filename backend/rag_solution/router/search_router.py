from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.search_service import SearchService

router = APIRouter(prefix="/api/search", tags=["search"])


def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    """
    Dependency to create a new SearchService instance with the database session.

    Args:
        db (Session): Database session from dependency injection

    Returns:
        SearchService: Initialized search service instance
    """
    return SearchService(db)


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
    search_service: SearchService = Depends(get_search_service),
    context: dict[str, Any] | None = None,
) -> SearchOutput:
    """
    Process a search query through the RAG pipeline.

    Args:
        search_input (SearchInput): Input data containing question and collection ID
        search_service (SearchService): The search service instance from dependency injection
        context (Optional[Dict[str, Any]]): Additional context for query processing

    Returns:
        SearchOutput: Contains the generated answer, source documents, and evaluation info

    Raises:
        HTTPException: With appropriate status code and error detail
    """
    try:
        result: SearchOutput = await search_service.search(search_input, context)
        return result
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing search: {e!s}")
