from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.file_management.database import get_db
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
        500: {"description": "Internal server error"}
    }
)
async def search(
    search_input: SearchInput,
    search_service: SearchService = Depends(get_search_service),
    context: Optional[Dict[str, Any]] = None
) -> SearchOutput:
    """
    Process a search query through the RAG pipeline.
    
    Args:
        search_input (SearchInput): Input data containing question and collection.
        search_service (SearchService): The search service instance.
        context (Optional[Dict[str, Any]]): Additional context for query processing.
        
    Returns:
        SearchOutput: Contains the generated answer and related information.
        
    Raises:
        HTTPException: If there's an error processing the search.
    """
    try:
        return search_service.search(search_input, context)
    except HTTPException as he:
        # Pass through HTTP exceptions from the service
        raise he
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing search: {str(e)}"
        )

@router.post(
    "/stream",
    summary="Stream search results",
    description="Submit question to LLM and receive streaming response",
    response_class=StreamingResponse,
    responses={
        200: {"description": "Streaming response started successfully"},
        400: {"description": "Invalid input data"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"}
    }
)
async def search_stream(
    search_input: SearchInput,
    search_service: SearchService = Depends(get_search_service),
    context: Optional[Dict[str, Any]] = None
):
    """
    Process a search query through the RAG pipeline with streaming response.
    
    Args:
        search_input (SearchInput): Input data containing question and collection.
        search_service (SearchService): The search service instance.
        context (Optional[Dict[str, Any]]): Additional context for query processing.
        
    Returns:
        StreamingResponse: Streams the generated answer and related information.
        
    Raises:
        HTTPException: If there's an error processing the search.
    """
    try:
        # Get the generator from search service
        response_generator = search_service.search_stream(search_input, context)
        
        # Return a StreamingResponse
        return StreamingResponse(
            response_generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable buffering for nginx
            }
        )
    except HTTPException as he:
        # Pass through HTTP exceptions from the service
        raise he
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing streaming search: {str(e)}"
        )