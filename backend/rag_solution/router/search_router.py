from fastapi import APIRouter, Depends, HTTPException, status
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.file_management.database import get_db
from rag_solution.services.search_service import SearchService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/search", tags=["search"])

@router.post("", 
    response_model=SearchOutput,
    summary="Question LLM in a scope of documents added to selected collection",
    description="Submit question to LLM providing a collection of documents as a context",
    responses={
        200: {"description": "LLM response generated successfully"},
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"}
    }
)
def question_llm(search_input: SearchInput, db: Session = Depends(get_db)) -> SearchOutput:
    """
    Question LLM against collection of documents.

    Args:
        search_input (SearchInput): Input data containing question and collection with documents.
        db (Session): The database session.

    Returns:
        SearchOutput: contains LLM generated answer.

    Raises:
        HTTPException: If there's an error creating the team.
    """
    search_service = SearchService()
    try:
        return search_service.create_team(search_input)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))