"""Router for question suggestion endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from pathlib import Path

from core.config import settings
from rag_solution.services.question_service import QuestionService
from rag_solution.schemas.question_schema import (
    QuestionConfig,
    TextRequest,
    QuestionSuggestionResponse,
    SourceDocument
)
from auth.oidc import get_current_user
from rag_solution.models.user import User
from rag_solution.file_management.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/suggest-questions", tags=["questions"])

@router.post("/collection/{collection_id}", response_model=QuestionSuggestionResponse)
async def suggest_questions_from_collection(
    collection_id: UUID,
    num_questions: Optional[int] = settings.question_suggestion_num,
    config: Optional[QuestionConfig] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> QuestionSuggestionResponse:
    """Generate questions from a collection."""
    question_service = QuestionService(db, config.model_dump() if config else None)
    try:
        # Get stored questions or generate new ones
        result = question_service.get_collection_questions(collection_id)
        if not result:
            # If no stored questions, get collection texts and generate new ones
            # Note: We'll need to get texts from the collection service or repository
            # This will be implemented when integrating with pipeline.py
            return QuestionSuggestionResponse(
                suggested_questions=[],
                source_documents=[]
            )
        
        return QuestionSuggestionResponse(
            suggested_questions=result,
            source_documents=[]  # We don't need to return source docs for stored questions
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate questions: {str(e)}"
        )

@router.post("/text", response_model=QuestionSuggestionResponse)
async def suggest_questions_from_text(
    request: TextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> QuestionSuggestionResponse:
    """Generate questions from text."""
    question_service = QuestionService(db)
    try:
        # Split text into chunks that respect context window
        text_chunks = [request.text]  # For now, single chunk. Will be improved with chunking logic
        
        # Generate questions
        result = question_service.suggest_questions(
            collection_id=UUID('00000000-0000-0000-0000-000000000000'),  # Default UUID for text-based questions
            texts=text_chunks,
            num_questions=request.num_questions
        )
        
        return QuestionSuggestionResponse(
            collection_id=result.collection_id,
            suggested_questions=result.suggested_questions,
            source_documents=[SourceDocument(text=text) for text in result.source_documents]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate questions: {str(e)}"
        )

@router.post("/collection/{collection_id}/regenerate", response_model=QuestionSuggestionResponse)
async def regenerate_collection_questions(
    collection_id: UUID,
    num_questions: Optional[int] = settings.question_suggestion_num,
    config: Optional[QuestionConfig] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> QuestionSuggestionResponse:
    """Force regeneration of questions for a collection."""
    question_service = QuestionService(db, config.dict() if config else None)
    try:
        # Note: We'll need to get texts from the collection service or repository
        # This will be implemented when integrating with pipeline.py
        texts = []  # Placeholder until we implement text retrieval
        
        result = question_service.regenerate_questions(
            collection_id=collection_id,
            texts=texts,
            num_questions=num_questions
        )
        
        return QuestionSuggestionResponse(
            collection_id=collection_id,
            suggested_questions=result.suggested_questions,
            source_documents=[SourceDocument(text=text) for text in result.source_documents]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to regenerate questions: {str(e)}"
        )
