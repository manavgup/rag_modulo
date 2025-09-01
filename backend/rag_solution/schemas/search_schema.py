"""API schemas for search functionality."""

from typing import Any

from pydantic import BaseModel, ConfigDict, UUID4
from vectordbs.data_types import DocumentMetadata, QueryResult


class SearchInput(BaseModel):
    """Input schema for search requests.

    Defines the structure of search requests to the API.

    Attributes:
        question: The user's query text
        collection_id: UUID of the collection to search in
    """

    question: str
    collection_id: UUID4
    pipeline_id: UUID4
    user_id: UUID4
    config_metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class SearchOutput(BaseModel):
    """Output schema for search responses.

    Defines the structure of search responses from the API.
    This maps directly to what the UI needs to display:
    - The generated answer
    - List of document metadata for showing document info
    - List of chunks with their scores for showing relevant passages

    Attributes:
        answer: Generated answer to the query
        documents: List of document metadata for UI display
        query_results: List of QueryResult
        rewritten_query: Optional rewritten version of the original query
        evaluation: Optional evaluation metrics and results
    """

    answer: str
    documents: list[DocumentMetadata]
    query_results: list[QueryResult]
    rewritten_query: str | None = None
    evaluation: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)
