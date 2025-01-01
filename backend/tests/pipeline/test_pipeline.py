"""Tests for RAG pipeline."""

import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy.orm import Session

from rag_solution.pipeline.pipeline import Pipeline, PipelineResult, GenerationVariables
from typing import Generator, List, Optional, Union, Dict, Any
from rag_solution.generation.providers.base import LLMProvider, ProviderConfig
from rag_solution.schemas.llm_parameters_schema import LLMParametersBase
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from vectordbs.data_types import QueryResult, DocumentChunk, DocumentMetadata, VectorQuery

class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""
    
    def __init__(self, response: str = "Test answer"):
        """Initialize mock provider.
        
        Args:
            response: Response to return
        """
        super().__init__()
        self.response = response
        
    def initialize_client(self) -> None:
        """Mock initialization."""
        pass
        
    def generate_text(
        self,
        prompt: Union[str, List[str]],
        model_parameters: LLMParametersBase,
        template: Optional[PromptTemplateBase] = None,
        provider_config: Optional[ProviderConfig] = None
    ) -> Union[str, List[str]]:
        """Mock text generation."""
        return self.response
        
    def generate_text_stream(
        self,
        prompt: str,
        model_parameters: LLMParametersBase,
        template: Optional[PromptTemplateBase] = None,
        provider_config: Optional[ProviderConfig] = None
    ) -> Generator[str, None, None]:
        """Mock streaming generation."""
        yield self.response
        
    def get_embeddings(
        self,
        texts: Union[str, List[str]],
        provider_config: Optional[ProviderConfig] = None
    ) -> List[List[float]]:
        """Mock embeddings."""
        return [[0.1, 0.2, 0.3]]

@pytest.fixture
def mock_provider():
    """Create mock provider instance."""
    return MockProvider()

@pytest.fixture
def mock_parameters() -> LLMParametersBase:
    """Create mock LLM parameters."""
    return LLMParametersBase(
        max_new_tokens=100,
        temperature=0.7,
        top_k=50,
        top_p=1.0
    )

@pytest.fixture
def mock_template() -> PromptTemplateBase:
    """Create mock prompt template."""
    return PromptTemplateBase(
        name="test-template",
        provider="test-provider",
        system_prompt="You are a helpful assistant",
        context_prefix="Context:",
        query_prefix="Question:",
        answer_prefix="Answer:"
    )

@pytest.fixture
def pipeline(
    db: Session,
    mock_provider: MockProvider,
    mock_parameters: LLMParametersBase,
    mock_template: PromptTemplateBase
):
    """Create pipeline instance with mock provider."""
    return Pipeline(
        db=db,
        provider=mock_provider,
        model_parameters=mock_parameters,
        prompt_template=mock_template,
        collection_name="test_collection"
    )

@pytest.fixture
def mock_query_results():
    """Create mock query results."""
    return [
        QueryResult(
            chunk=DocumentChunk(
                text="Test context 1",
                metadata=DocumentMetadata(
                    document_name="doc1.txt",
                    total_pages=1
                )
            ),
            score=0.9,
            document_id="doc1"
        ),
        QueryResult(
            chunk=DocumentChunk(
                text="Test context 2",
                metadata=DocumentMetadata(
                    document_name="doc2.txt",
                    total_pages=1
                )
            ),
            score=0.8,
            document_id="doc2"
        )
    ]

def test_pipeline_initialization(
    pipeline: Pipeline,
    mock_provider: MockProvider,
    mock_parameters: LLMParametersBase,
    mock_template: PromptTemplateBase
):
    """Test pipeline initialization."""
    # Test basic initialization
    assert pipeline.collection_name == "test_collection"
    assert pipeline.provider is mock_provider
    assert pipeline.query_rewriter is not None
    assert pipeline.retriever is not None
    assert pipeline.evaluator is not None
    
    # Test strongly typed parameters
    assert pipeline.model_parameters == mock_parameters
    assert pipeline.prompt_template == mock_template
    
    # Verify parameter values
    assert pipeline.model_parameters.max_new_tokens == 100
    assert pipeline.model_parameters.temperature == 0.7
    assert pipeline.model_parameters.top_k == 50
    assert pipeline.model_parameters.top_p == 1.0
    
    # Verify template values
    assert pipeline.prompt_template.name == "test-template"
    assert pipeline.prompt_template.provider == "test-provider"
    assert pipeline.prompt_template.system_prompt == "You are a helpful assistant"

@pytest.mark.asyncio
async def test_pipeline_process(
    pipeline: Pipeline,
    mock_provider: MockProvider,
    mock_query_results: list[QueryResult],
    monkeypatch
):
    """Test pipeline processing."""
    # Mock components
    mock_retrieve = Mock(return_value=mock_query_results)
    mock_rewrite = Mock(return_value="rewritten query")
    mock_evaluate = AsyncMock(return_value={"score": 0.9})
    mock_generate = Mock(return_value="Test answer")
    
    # Set up mocks
    monkeypatch.setattr(pipeline.retriever, "retrieve", mock_retrieve)
    monkeypatch.setattr(pipeline.query_rewriter, "rewrite", mock_rewrite)
    monkeypatch.setattr(pipeline.evaluator, "evaluate", mock_evaluate)
    monkeypatch.setattr(pipeline.provider, "generate_text", mock_generate)
    
    # Process query
    result = await pipeline.process(
        query="test query",
        collection_name="test_collection"
    )
    
    # Verify result
    assert isinstance(result, PipelineResult)
    assert result.rewritten_query == "rewritten query"
    assert result.query_results == mock_query_results
    assert result.generated_answer == "Test answer"
    assert result.evaluation == {"score": 0.9}
    
    # Verify generate_text called with correct parameters
    mock_generate.assert_called_once_with(
        prompt="test query",
        model_parameters=pipeline.model_parameters,
        template=pipeline.prompt_template,
        variables=GenerationVariables(
            context="Test context 1\nTest context 2",
            question="test query"
        )
    )

@pytest.mark.asyncio
async def test_pipeline_empty_query(pipeline: Pipeline):
    """Test pipeline with empty query."""
    with pytest.raises(ValueError, match="Query cannot be empty"):
        await pipeline.process(query="", collection_name="test_collection")

@pytest.mark.asyncio
async def test_pipeline_retrieval_error(
    pipeline: Pipeline,
    monkeypatch
):
    """Test pipeline handling retrieval error."""
    # Mock retriever to raise error
    def mock_retrieve(*args, **kwargs):
        raise Exception("Retrieval error")
    monkeypatch.setattr(pipeline.retriever, "retrieve", mock_retrieve)
    
    result = await pipeline.process(
        query="test query",
        collection_name="test_collection"
    )
    
    assert result.generated_answer == ""
    assert "Retrieval error" in result.evaluation["error"]

@pytest.mark.asyncio
async def test_pipeline_generation_error(
    pipeline: Pipeline,
    mock_query_results: list[QueryResult],
    monkeypatch
):
    """Test pipeline handling generation error."""
    # Mock retriever
    mock_retrieve = Mock(return_value=mock_query_results)
    monkeypatch.setattr(pipeline.retriever, "retrieve", mock_retrieve)
    
    # Mock provider to raise error
    def mock_generate(*args, **kwargs):
        raise Exception("Generation error")
    monkeypatch.setattr(pipeline.provider, "generate_text", mock_generate)
    
    result = await pipeline.process(
        query="test query",
        collection_name="test_collection"
    )
    
    assert result.generated_answer == ""
    assert "Generation error" in result.evaluation["error"]

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
