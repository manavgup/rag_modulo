"""Integration tests for PipelineService."""

from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import UUID4

from core.custom_exceptions import NotFoundError, ValidationError
from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.schemas.pipeline_schema import (
    ChunkingStrategy,
    ContextStrategy,
    PipelineConfigInput,
    PipelineResult,
    RetrieverType,
)
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.pipeline_service import PipelineService


# -------------------------------------------
# 🔧 Test Fixtures
# -------------------------------------------
@pytest.fixture
def search_input(base_collection: CollectionOutput) -> SearchInput:
    """Create test search input."""
    return SearchInput(
        question="What are the main features of Python?",
        collection_id=base_collection.id,
        pipeline_id=UUID4("00000000-0000-0000-0000-000000000000"),
        user_id=UUID4("00000000-0000-0000-0000-000000000000"),
        config_metadata={},
    )


# -------------------------------------------
# 🧪 Pipeline Service Tests
# -------------------------------------------
def test_service_initialization(pipeline_service: Any, base_user: UserOutput, ensure_watsonx_provider: Any) -> None:
    """Test service initialization."""
    assert base_user is not None
    assert base_user.id is not None

    assert pipeline_service.db is not None
    assert pipeline_service.query_rewriter is not None
    assert pipeline_service.vector_store is not None
    assert pipeline_service.evaluator is not None


@pytest.mark.asyncio
async def test_pipeline_initialization(pipeline_service: PipelineService, base_user: UserOutput, ensure_watsonx_provider: Any) -> None:
    """Test pipeline initialization."""
    assert base_user is not None
    assert base_user.id is not None

    await pipeline_service.initialize("test_collection")

    assert pipeline_service.document_store is not None
    assert pipeline_service.document_store.collection_name == "test_collection"
    assert pipeline_service.retriever is not None


@pytest.mark.asyncio
async def test_execute_pipeline_validation(pipeline_service: Any, search_input: SearchInput, base_user: UserOutput, base_collection: Any) -> None:
    """Test pipeline execution with validation."""
    await pipeline_service.initialize(base_collection.vector_db_name)

    # Create invalid input - properly immutable
    invalid_input = SearchInput(
        question="",  # Empty question
        collection_id=base_collection.id,
        pipeline_id=search_input.pipeline_id,
        user_id=base_user.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await pipeline_service.execute_pipeline(invalid_input, base_collection.vector_db_name)
    assert exc_info.value.status_code == 400
    assert "Query cannot be empty" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_pipeline_with_content(
    test_client: Any,
    pipeline_service: PipelineService,
    base_user: UserOutput,
    base_collection: Any,
    indexed_large_document: Any,
    ensure_watsonx_provider: Any,
    default_pipeline_config: Any,
    base_llm_parameters: Any,  # : LLMParametersOutput,
) -> None:
    """Test pipeline execution with comprehensive content."""
    # Initialize system
    await pipeline_service.initialize(base_collection.vector_db_name)

    # Test different types of queries
    test_queries: list[dict[str, str | list[str]]] = [
        {
            "question": "What is Python and who created it?",
            "expected_terms": ["guido", "van rossum", "1991", "programming"],
        },
        {"question": "What are the main features of Django?", "expected_terms": ["admin", "orm", "framework"]},
        {"question": "How can Python performance be optimized?", "expected_terms": ["cython", "asyncio"]},
        {
            "question": "What testing frameworks are available in Python?",
            "expected_terms": ["unittest", "pytest", "fixtures"],
        },
    ]

    for query in test_queries:
        question: str = query["question"]  # type: ignore[assignment]
        search_input = SearchInput(
            question=question,
            collection_id=base_collection.id,
            pipeline_id=default_pipeline_config.id,
            user_id=base_user.id,
            config_metadata={},
        )

        result = await pipeline_service.execute_pipeline(search_input, base_collection.vector_db_name)

        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert result.generated_answer is not None
        assert result.query_results is not None and len(result.query_results) > 0

        answer_lower = result.generated_answer.lower()
        matching_terms = [term for term in query["expected_terms"] if term in answer_lower]
        assert matching_terms, f"Answer for '{query['question']}' missing expected terms. " f"Expected any of {query['expected_terms']}, but got none. " f"Answer was: {result.generated_answer}"


def test_collection_default_pipeline(pipeline_service: PipelineService, base_collection: Any, default_pipeline_config: Any) -> None:
    """Test setting default pipeline for collection."""
    default = pipeline_service.set_default_pipeline(default_pipeline_config.id)

    assert default is not None
    assert default.is_default is True
    assert default.collection_id == base_collection.id
    assert default.chunking_strategy == "fixed"
    assert default.retriever == "vector"
    assert default.context_strategy == "simple"


# -------------------------------------------
# 🧪 Pipeline Configuration Tests
# -------------------------------------------
def test_create_pipeline_config(pipeline_service: PipelineService, base_user: UserOutput, base_collection: Any, ensure_watsonx_provider: Any) -> None:
    """Test creating pipeline configuration."""
    config_input = PipelineConfigInput(
        name="test-pipeline",
        description="Test pipeline configuration",
        chunking_strategy=ChunkingStrategy.FIXED,
        embedding_model="sentence-transformers/all-minilm-l6-v2",
        retriever=RetrieverType.VECTOR,
        context_strategy=ContextStrategy.SIMPLE,
        provider_id=ensure_watsonx_provider.id,
        collection_id=base_collection.id,
        user_id=base_user.id,
        enable_logging=True,
        max_context_length=2048,
        timeout=30.0,
        is_default=True,
    )

    config = pipeline_service.create_pipeline(config_input)
    assert config.name == config_input.name
    assert config.retriever == config_input.retriever
    assert config.provider_id == config_input.provider_id
    assert config.is_default is True


def test_get_pipeline_config(pipeline_service: PipelineService, default_pipeline_config: Any) -> None:
    """Test retrieving pipeline configuration."""
    config = pipeline_service.get_pipeline_config(default_pipeline_config.id)
    assert config is not None
    assert config.id == default_pipeline_config.id
    assert config.name == default_pipeline_config.name


def test_validate_pipeline(pipeline_service: PipelineService, default_pipeline_config: Any) -> None:
    """Test pipeline validation."""
    result = pipeline_service.validate_pipeline(default_pipeline_config.id)
    assert result.success is True
    assert result.error is None
    assert result.warnings == []


# -------------------------------------------
# 🧪 Error Handling Tests
# -------------------------------------------
def test_invalid_pipeline_id(pipeline_service: PipelineService, base_collection: Any) -> None:
    """Test handling of invalid pipeline ID."""
    with pytest.raises(NotFoundError):
        pipeline_service.get_pipeline_config(UUID4("00000000-0000-0000-0000-000000000000"))


def test_invalid_collection_id(pipeline_service: PipelineService, default_pipeline_config: Any, base_user: Any, base_collection: Any) -> None:
    """Test handling of invalid collection ID."""
    config_input = PipelineConfigInput(
        name="test-pipeline",
        description="Test pipeline for invalid collection ID",
        collection_id=UUID4("00000000-0000-0000-0000-000000000000"),  # Invalid ID
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        user_id=base_user.id,
        provider_id=default_pipeline_config.provider_id,
        chunking_strategy=ChunkingStrategy.FIXED,
        retriever=RetrieverType.VECTOR,
        context_strategy=ContextStrategy.SIMPLE,
    )

    with pytest.raises(ValidationError):
        pipeline_service.create_pipeline(config_input)


if __name__ == "__main__":
    pytest.main([__file__])
