"""Tests for PipelineService implementation."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from core.custom_exceptions import ConfigurationError, ValidationError
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.models.user import User
from rag_solution.schemas.pipeline_schema import PipelineConfigInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateType
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.pipeline_service import PipelineResult, PipelineService
from rag_solution.services.prompt_template_service import PromptTemplateService
from vectordbs.data_types import DocumentChunk, DocumentChunkMetadata, QueryResult, Source


@pytest.fixture
@pytest.mark.atomic
def test_user(db_session: Session) -> User:
    """Create test user."""
    user = User(id=uuid4(), ibm_id="test_user", email="test@example.com", name="Test User")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_llm_parameters(db_session: Session, test_user: User) -> LLMParameters:
    """Create test LLM parameters."""
    params = LLMParameters(
        id=uuid4(),
        user_id=test_user.id,
        name="Test Parameters",
        max_new_tokens=100,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        is_default=True,
    )
    db_session.add(params)
    db_session.commit()
    return params


@pytest.fixture
def test_templates(db_session: Session, test_user: User) -> dict[str, PromptTemplate]:
    """Create test prompt templates."""
    templates = {}
    template_base = {
        "provider": "watsonx",
        "template_format": "Question: {question}\nContext: {context}",
        "input_variables": {"context": "str", "question": "str"},
        "validation_schema": {
            "model": "PromptVariables",
            "fields": {"context": {"type": "str", "min_length": 1}, "question": {"type": "str", "min_length": 1}},
            "required": ["context", "question"],
        },
        "example_inputs": {"context": "Python was created by Guido van Rossum.", "question": "Who created Python?"},
        "is_default": True,
    }

    for template_type in [PromptTemplateType.RAG_QUERY, PromptTemplateType.RESPONSE_EVALUATION]:
        template = PromptTemplate(
            id=uuid4(),
            user_id=test_user.id,
            name=f"Test {template_type.value}",
            description=f"Test template for {template_type.value}",
            template_type=template_type,
            **template_base,
        )
        db_session.add(template)
        templates[template_type] = template
    db_session.commit()
    return templates


@pytest.fixture
def pipeline_service(db_session: Session) -> PipelineService:
    """Create pipeline service instance."""
    return PipelineService(db_session)


@pytest.fixture
def search_input() -> SearchInput:
    """Create test search input."""
    return SearchInput(
        question="What is the capital of France?",
        collection_id=UUID("12345678-1234-5678-1234-567812345678"),
        pipeline_id=UUID("87654321-4321-8765-4321-876543210987"),
        metadata={"max_length": 100},
    )


@pytest.fixture
def mock_query_results(db_session: Session) -> list[QueryResult]:
    """Create mock query results."""
    provider_service = LLMProviderService(db_session)
    provider = provider_service.get_provider_by_name("watsonx")

    text1 = "Test context 1"
    text2 = "Test context 2"
    embeddings = provider.generate_embeddings([text1, text2])

    return [
        QueryResult(
            chunk=DocumentChunk(
                chunk_id="chunk1",
                text=text1,
                embeddings=embeddings[0],
                metadata=DocumentChunkMetadata(source=Source.OTHER, document_id="doc1", page_number=1, chunk_number=1),
                document_id="doc1",
            ),
            score=0.9,
            document_id="doc1",
            embeddings=embeddings[0],
        ),
        QueryResult(
            chunk=DocumentChunk(
                chunk_id="chunk2",
                text=text2,
                embeddings=embeddings[1],
                metadata=DocumentChunkMetadata(source=Source.OTHER, document_id="doc2", page_number=1, chunk_number=1),
                document_id="doc2",
            ),
            score=0.8,
            document_id="doc2",
            embeddings=embeddings[1],
        ),
    ]


def test_service_initialization(pipeline_service: PipelineService):
    """Test service initialization."""
    assert pipeline_service.db is not None
    assert pipeline_service.query_rewriter is not None
    assert pipeline_service.vector_store is not None
    assert pipeline_service.evaluator is not None


@pytest.mark.asyncio
async def test_pipeline_initialization(pipeline_service: PipelineService):
    """Test pipeline initialization."""
    # Initialize for test collection
    await pipeline_service.initialize("test_collection")

    # Verify document store setup
    assert pipeline_service.document_store is not None
    assert pipeline_service.document_store.collection_name == "test_collection"

    # Verify retriever setup
    assert pipeline_service.retriever is not None


@pytest.mark.asyncio
async def test_execute_pipeline(
    pipeline_service: PipelineService,
    search_input: SearchInput,
    test_user: User,
    test_llm_parameters: LLMParameters,
    test_templates: dict[str, PromptTemplate],
):
    """Test pipeline execution."""
    # Initialize pipeline
    await pipeline_service.initialize("test_collection")

    # Execute pipeline
    result = await pipeline_service.execute_pipeline(search_input, test_user.id)

    # Verify result structure
    assert isinstance(result, PipelineResult)
    assert isinstance(result.rewritten_query, str)
    assert isinstance(result.query_results, list)
    assert isinstance(result.generated_answer, str)

    # Since no documents are loaded, should get no documents found message
    assert "couldn't find any relevant documents" in result.generated_answer


@pytest.mark.asyncio
async def test_pipeline_configuration_error(
    pipeline_service: PipelineService, search_input: SearchInput, test_user: User
):
    """Test pipeline handling configuration error."""
    # Don't initialize to trigger error
    with pytest.raises(ConfigurationError):
        await pipeline_service.execute_pipeline(search_input, test_user.id)


@pytest.mark.asyncio
async def test_pipeline_validation_error(pipeline_service: PipelineService, search_input: SearchInput, test_user: User):
    """Test pipeline handling validation error."""
    # Initialize pipeline
    await pipeline_service.initialize("test_collection")

    # Break the search input
    search_input.question = ""

    with pytest.raises(ValidationError):
        await pipeline_service.execute_pipeline(search_input, test_user.id)


@pytest.mark.asyncio
async def test_pipeline_template_error(
    pipeline_service: PipelineService, search_input: SearchInput, test_user: User, db_session: Session
):
    """Test pipeline handling template error."""
    # Initialize pipeline
    await pipeline_service.initialize("test_collection")

    # Break the template service
    template_service = PromptTemplateService(db_session)
    pipeline_service._prompt_template_service = template_service

    # Execute pipeline - should handle template error gracefully
    result = await pipeline_service.execute_pipeline(search_input, test_user.id)
    assert result.generated_answer != ""
    assert isinstance(result.generated_answer, str)


@pytest.mark.asyncio
async def test_pipeline_provider_error(
    pipeline_service: PipelineService, search_input: SearchInput, test_user: User, db_session: Session
):
    """Test pipeline handling provider error."""
    # Initialize pipeline
    await pipeline_service.initialize("test_collection")

    # Break the provider service
    provider_service = LLMProviderService(db_session)
    pipeline_service._llm_provider_service = provider_service

    # Execute pipeline - should handle provider error gracefully
    result = await pipeline_service.execute_pipeline(search_input, test_user.id)
    assert result.evaluation is not None
    assert "error" in result.evaluation


def test_pipeline_result_methods(mock_query_results: list[QueryResult]):
    """Test PipelineResult helper methods."""
    result = PipelineResult(
        rewritten_query="test", query_results=mock_query_results, generated_answer="answer", evaluation={"score": 0.9}
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


def test_get_collection_default_pipeline(pipeline_service: PipelineService, test_collection, test_config):
    """Test getting default pipeline for collection."""
    default = pipeline_service.pipeline_repository.get_collection_default(test_collection.id)
    assert default is None  # Initially no default

    # Set default and verify
    updated = pipeline_service.set_default_pipeline(test_config["pipeline"].id)
    assert updated.is_default is True

    default = pipeline_service.pipeline_repository.get_collection_default(test_collection.id)
    assert default is not None
    assert default.id == test_config["pipeline"].id


def test_validate_collection_default_rules(pipeline_service: PipelineService, test_config):
    """Test validation rules for collection defaults."""
    # Try to set system-wide pipeline as default
    config_input = PipelineConfigInput(
        name="test-system",
        description="Test system pipeline",
        chunking_strategy="fixed",
        embedding_model="sentence-transformers/all-mpnet-base-v2",
        retriever="vector",
        context_strategy="priority",
        provider_id=test_config["pipeline"].provider_id,
        enable_logging=True,
        max_context_length=2048,
        timeout=30.0,
        is_default=True,  # This should fail validation
    )

    with pytest.raises(ValidationError):
        pipeline_service.create_pipeline(config_input)
