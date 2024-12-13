from uuid import UUID
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict

class DocumentMetadata(BaseModel):
    source: str
    source_id: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    author: Optional[str] = None
    title: Optional[str] = None
    page_number: Optional[int] = None
    total_pages: Optional[int] = None
    document_name: Optional[str] = None 

class SourceDocument(BaseModel):
    text: str
    metadata: Optional[DocumentMetadata] = None
    score: Optional[float] = None
    document_id: Optional[str] = None

class SearchInput(BaseModel):
    question: str
    collection_id: UUID

class SearchOutput(BaseModel):
    answer: str  # Changed from generated_answer to match frontend
    source_documents: List[SourceDocument]
    rewritten_query: Optional[str] = None  # Changed from rewrittenQuery to match frontend
    evaluation: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
