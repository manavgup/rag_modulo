"""Tests for SearchService with PipelineService integration."""

from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import UUID4

from rag_solution.schemas.collection_schema import CollectionInput, CollectionStatus
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.schemas.user_schema import UserInput, UserOutput
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source


# -------------------------------------------
# 🧪 Basic Search Tests
# -------------------------------------------
@pytest.mark.asyncio
async def test_search_basic(search_service: Any, base_collection: Any, base_file: Any, base_user: Any, base_pipeline_config: Any) -> None:
    """Test basic search functionality with pipeline service."""
    search_input = SearchInput(
        question="What is the capital of France?",
        collection_id=base_collection.id,
        pipeline_id=base_pipeline_config["pipeline"].id,
        user_id=base_user.id,
    )

    result = await search_service.search(search_input)

    assert isinstance(result, SearchOutput)
    assert len(result.documents) > 0
    assert result.documents[0].document_name == "test.txt"
    assert result.rewritten_query is not None
    assert result.query_results is not None


@pytest.mark.asyncio
async def test_search_no_results(search_service: Any, base_collection: Any, base_user: Any, base_pipeline_config: Any) -> None:
    """Test search with a query that has no matching documents."""
    search_input = SearchInput(
        question="What is the capital of Mars?",  # Query that won't match any documents
        collection_id=base_collection.id,
        pipeline_id=base_pipeline_config["pipeline"].id,
        user_id=base_user.id,
    )

    result = await search_service.search(search_input)

    assert isinstance(result, SearchOutput)
    assert len(result.documents) == 0  # No matching documents found
    assert result.rewritten_query is not None
    assert result.answer == "I apologize, but couldn't find any relevant documents."


# -------------------------------------------
# 🧪 Authorization Tests
# -------------------------------------------
@pytest.mark.asyncio
async def test_search_invalid_collection(search_service: Any, base_user: UserOutput, base_pipeline_config: Any) -> None:
    """Test search with an invalid collection ID."""
    search_input = SearchInput(
        question="Test question",
        collection_id=UUID4(int=0),  # Invalid UUID
        pipeline_id=base_pipeline_config["pipeline"].id,
        user_id=base_user.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input)
    assert exc_info.value.status_code == 404
    assert "Collection with ID 00000000-0000-0000-0000-000000000000 not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_search_unauthorized_collection(search_service: Any, user_service: Any, collection_service: Any, base_pipeline_config: Any) -> None:
    """Test search with a collection the user doesn't have access to."""
    unauthorized_user = user_service.create_user(
        UserInput(
            name="Unauthorized User",
            email=f"unauthorized{uuid4()}@example.com",
            ibm_id=f"unauthorized-ibm-id-{uuid4()}",  # Unique IBM ID
        )
    )

    # Create private collection
    private_collection = collection_service.create_collection(
        CollectionInput(
            name="Private Collection",
            is_private=True,
            users=[],  # No users have access
            status=CollectionStatus.CREATED,
        )
    )

    search_input = SearchInput(
        question="Test question",
        collection_id=private_collection.id,
        pipeline_id=base_pipeline_config["pipeline"].id,
        user_id=unauthorized_user.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input)
    assert exc_info.value.status_code == 404
    assert "Collection not found" in str(exc_info.value.detail)


# -------------------------------------------
# 🧪 Multiple Document Tests
# -------------------------------------------
@pytest.mark.asyncio
@patch("core.config.settings.embedding_model", "test-embedding-model")
async def test_search_multiple_documents(
    search_service: Any,
    base_user: UserOutput,
    base_collection: Any,
    base_pipeline_config: Any,
    vector_store: Any,
    provider_factory: Any,
) -> None:
    """Test search with multiple documents in a collection."""
    watsonx = provider_factory.get_provider("watsonx")

    # Create and index test documents
    files_data = [
        {"doc_id": "france", "text": "Paris is the capital of France. It is known for the Eiffel Tower."},
        {"doc_id": "germany", "text": "Berlin is the capital of Germany. It is known for its rich history."},
    ]

    documents = []
    for data in files_data:
        # Mock the embeddings call for atomic test
        mock_embeddings = [[0.1, 0.2, 0.3, 0.4, 0.5]]  # Mock embedding vector
        with patch.object(watsonx, "get_embeddings", return_value=mock_embeddings):
            embeddings = watsonx.get_embeddings([data["text"]])
        document = Document(
            document_id=data["doc_id"],
            name=f"{data['doc_id']}.txt",
            chunks=[
                DocumentChunk(
                    chunk_id=f"chunk_{data['doc_id']}",
                    text=data["text"],
                    embeddings=embeddings[0],
                    metadata=DocumentChunkMetadata(source=Source.OTHER, document_id=data["doc_id"], page_number=1, chunk_number=1),
                )
            ],
        )
        documents.append(document)

    # Add documents to vector store
    vector_store.delete_collection(base_collection.vector_db_name)
    vector_store.create_collection(base_collection.vector_db_name, {"embedding_model": "test-embedding-model"})
    vector_store.add_documents(base_collection.vector_db_name, documents)

    # Perform search
    search_input = SearchInput(
        question="What are the capitals of European countries?",
        collection_id=base_collection.id,
        pipeline_id=base_pipeline_config["pipeline"].id,
        user_id=base_user.id,
    )

    result = await search_service.search(search_input)

    assert isinstance(result, SearchOutput)
    assert len(result.documents) == 2
    assert {doc.document_name for doc in result.documents} == {"france.txt", "germany.txt"}


# -------------------------------------------
# 🧪 Error Handling Tests
# -------------------------------------------
@pytest.mark.asyncio
async def test_search_invalid_pipeline(search_service: Any, base_collection: Any, base_user: Any) -> None:
    """Test search with an invalid pipeline ID."""
    search_input = SearchInput(
        question="Test question",
        collection_id=base_collection.id,
        pipeline_id=UUID4(int=0),  # Invalid UUID
        user_id=base_user.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input)
    assert exc_info.value.status_code == 404
    assert "Pipeline configuration not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_search_empty_question(search_service: Any, base_collection: Any, base_user: Any, base_pipeline_config: Any) -> None:
    """Test search with empty question string."""
    search_input = SearchInput(
        question="",
        collection_id=base_collection.id,
        pipeline_id=base_pipeline_config["pipeline"].id,
        user_id=base_user.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input)
    assert exc_info.value.status_code == 400
    assert "Query cannot be empty" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_search_vector_store_error(search_service: Any, base_collection: Any, base_user: Any, base_pipeline_config: Any, mocker: Any) -> None:
    """Test search when vector store connection fails."""
    mocker.patch("vectordbs.milvus_store.MilvusStore._connect", side_effect=Exception("Connection failed"))

    search_input = SearchInput(
        question="Test question",
        collection_id=base_collection.id,
        pipeline_id=base_pipeline_config["pipeline"].id,
        user_id=base_user.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input)
    assert exc_info.value.status_code == 500
    assert "Connection failed" in str(exc_info.value.detail)


# -------------------------------------------
# 🧪 Helper Function Tests
# -------------------------------------------
def test_clean_generated_answer(search_service: Any) -> None:
    """Test cleaning of generated answers."""
    test_cases = [
        ("AND this AND that", "this that"),
        ("the the answer answer is is here here", "the answer is here"),
        ("answer   with   extra   spaces", "answer with extra spaces"),
        ("", ""),
        ("answer", "answer"),
        ("AND answer! AND with? AND punctuation.", "answer! with? punctuation."),
    ]

    for input_text, expected in test_cases:
        cleaned = search_service._clean_generated_answer(input_text)
        assert cleaned == expected


if __name__ == "__main__":
    pytest.main([__file__])
