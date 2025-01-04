"""Tests for RAG pipeline."""

import pytest
from sqlalchemy.orm import Session

from rag_solution.pipeline.pipeline import Pipeline, PipelineResult
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.services.provider_config_service import ProviderConfigService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.runtime_config_service import RuntimeConfigService
from vectordbs.data_types import QueryResult, DocumentChunk, DocumentChunkMetadata, VectorQuery, Source
from core.config import settings

@pytest.fixture
def pipeline(db_session: Session):
    """Create pipeline instance with real provider."""
    # Get runtime configuration
    runtime_config = RuntimeConfigService(db_session).get_runtime_config()
    
    # Get provider instance
    provider = LLMProviderFactory(db_session).get_provider("watsonx")
    
    # Create pipeline
    pipeline = Pipeline(
        db=db_session,
        provider=provider,
        model_parameters=runtime_config.llm_parameters,
        prompt_template=runtime_config.prompt_template,
        collection_name="test_collection"
    )
    
    # Create collection
    try:
        pipeline.vector_store.delete_collection("test_collection")
    except:
        pass
    pipeline.vector_store.create_collection("test_collection", {"embedding_model": settings.embedding_model})
    
    yield pipeline
    
    # Cleanup
    try:
        pipeline.vector_store.delete_collection("test_collection")
    except:
        pass

@pytest.fixture
def mock_query_results(db_session: Session):
    """Create mock query results."""
    # Get embeddings using WatsonX provider
    provider = LLMProviderFactory(db_session).get_provider("watsonx")
    text1 = "Test context 1"
    text2 = "Test context 2"
    embeddings = provider.get_embeddings([text1, text2])
    
    return [
        QueryResult(
            chunk=DocumentChunk(
                chunk_id="chunk1",
                text=text1,
                embeddings=embeddings[0],
                metadata=DocumentChunkMetadata(
                    source=Source.OTHER,
                    document_id="doc1",
                    page_number=1,
                    chunk_number=1
                ),
                document_id="doc1"  # Set document_id at chunk level
            ),
            score=0.9,
            document_id="doc1",  # Set document_id at result level
            embeddings=embeddings[0]
        ),
        QueryResult(
            chunk=DocumentChunk(
                chunk_id="chunk2",
                text=text2,
                embeddings=embeddings[1],
                metadata=DocumentChunkMetadata(
                    source=Source.OTHER,
                    document_id="doc2",
                    page_number=1,
                    chunk_number=1
                ),
                document_id="doc2"  # Set document_id at chunk level
            ),
            score=0.8,
            document_id="doc2",  # Set document_id at result level
            embeddings=embeddings[1]
        )
    ]

def test_pipeline_initialization(pipeline: Pipeline):
    """Test pipeline initialization."""
    # Test basic initialization
    assert pipeline.collection_name == "test_collection"
    assert pipeline.provider is not None
    assert pipeline.query_rewriter is not None
    assert pipeline.retriever is not None
    assert pipeline.evaluator is not None
    
    # Test provider initialization
    assert pipeline.provider.client is not None
    
    # Test configuration
    assert pipeline.model_parameters is not None
    assert pipeline.prompt_template is not None
    assert pipeline.prompt_template.provider == "watsonx"

@pytest.mark.asyncio
async def test_pipeline_process(pipeline: Pipeline):
    """Test pipeline processing."""
    # Process query
    result = await pipeline.process(
        query="What is the capital of France?",
        collection_name="test_collection"
    )
    
    # Verify result structure
    assert isinstance(result, PipelineResult)
    assert isinstance(result.rewritten_query, str)
    assert isinstance(result.query_results, list)
    assert isinstance(result.generated_answer, str)
    
    # Verify provider was used
    assert pipeline.provider.client is not None
    
    # Verify query rewriting
    assert result.rewritten_query != ""
    
    # Since we don't have documents loaded, we should get the no documents found message
    assert "couldn't find any relevant documents" in result.generated_answer

@pytest.mark.asyncio
async def test_pipeline_empty_query(pipeline: Pipeline):
    """Test pipeline with empty query."""
    with pytest.raises(ValueError, match="Query cannot be empty"):
        await pipeline.process(query="", collection_name="test_collection")

@pytest.mark.asyncio
async def test_pipeline_retrieval_error(pipeline: Pipeline):
    """Test pipeline handling retrieval error."""
    # Use non-existent collection to trigger error
    result = await pipeline.process(
        query="What is the capital of France?",
        collection_name="non_existent_collection"
    )
    
    # Should handle error gracefully
    assert result.generated_answer == ""
    assert result.evaluation is not None
    assert "error" in result.evaluation

@pytest.mark.asyncio
async def test_pipeline_template_error(pipeline: Pipeline):
    """Test pipeline handling template formatting error."""
    # Set invalid template format to trigger error
    pipeline.prompt_template.template_format = None
    
    result = await pipeline.process(
        query="What is the capital of France?",
        collection_name="test_collection"
    )
    
    # Should still get the no documents found message
    assert result.generated_answer != ""
    assert isinstance(result.generated_answer, str)
    assert "couldn't find any relevant documents" in result.generated_answer

@pytest.mark.asyncio
async def test_pipeline_generation_error(pipeline: Pipeline):
    """Test pipeline handling generation error."""
    # Break the provider client to trigger error
    pipeline.provider.client = None
    
    result = await pipeline.process(
        query="What is the capital of France?",
        collection_name="test_collection"
    )
    
    # Should handle error gracefully
    assert result.generated_answer == ""
    assert result.evaluation is not None
    assert "error" in result.evaluation

def test_pipeline_result_methods(mock_query_results: list[QueryResult]):
    """Test PipelineResult helper methods."""
    result = PipelineResult(
        rewritten_query="test",
        query_results=mock_query_results,
        generated_answer="answer",
        evaluation={"score": 0.9}
    )
    
    # Test sorting
    sorted_results = result.get_sorted_results()
    assert sorted_results[0].score == 0.9
    assert sorted_results[1].score == 0.8
    
    # Test top k
    top_result = result.get_top_k_results(1)
    assert len(top_result) == 1
    assert top_result[0].score == 0.9
    
    # Test text extraction
    texts = result.get_all_texts()
    assert texts == ["Test context 1", "Test context 2"]
    
    # Test document IDs
    doc_ids = result.get_unique_document_ids()
    assert doc_ids == {"doc1", "doc2"}
    
    # Test document filtering
    doc1_results = result.get_results_for_document("doc1")
    assert len(doc1_results) == 1
    assert doc1_results[0].document_id == "doc1"
