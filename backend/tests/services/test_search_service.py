"""Tests for search service."""

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session
from fastapi import HTTPException

from rag_solution.services.search_service import SearchService
from rag_solution.models.user_provider_preference import UserProviderPreference
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.models.provider_config import ProviderModelConfig
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.models.file import File, FileMetadata
from rag_solution.models.collection import Collection
from core.custom_exceptions import ConfigurationError
from core.config import settings

@pytest.fixture
def search_service(db: Session):
    """Create search service instance."""
    return SearchService(db)

@pytest.fixture
def test_collection(db: Session):
    """Create test collection."""
    collection = Collection(
        name="test-collection",
        description="Test collection",
        vector_db_name="test_collection"
    )
    db.add(collection)
    db.commit()
    return collection

@pytest.fixture
def test_file(db: Session, test_collection: Collection):
    """Create test file."""
    file = File(
        filename="test.txt",
        document_id="doc1",
        collection_id=test_collection.id,
        metadata=FileMetadata(
            total_pages=1,
            total_chunks=1,
            keywords=["test"]
        )
    )
    db.add(file)
    db.commit()
    return file

@pytest.fixture
def test_config(db: Session):
    """Create test configurations."""
    # Create LLM parameters
    params = LLMParameters(
        name="test-params",
        max_new_tokens=100,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        is_default=True
    )
    db.add(params)
    db.commit()
    
    # Create provider config
    provider = ProviderModelConfig(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model",
        parameters_id=params.id,
        is_default=True,
        is_active=True
    )
    db.add(provider)
    
    # Create prompt template
    template = PromptTemplate(
        name="test-template",
        provider="test-provider",
        system_prompt="You are a helpful assistant",
        context_prefix="Context:",
        query_prefix="Question:",
        answer_prefix="Answer:",
        is_default=True
    )
    db.add(template)
    db.commit()
    
    return {
        'parameters': params,
        'provider': provider,
        'template': template
    }

@pytest.mark.asyncio
async def test_search_basic(
    db: Session,
    search_service: SearchService,
    test_collection: Collection,
    test_file: File,
    test_config: dict
):
    """Test basic search functionality."""
    # Create search input
    search_input = SearchInput(
        question="What is the capital of France?",
        collection_id=test_collection.id
    )
    
    # Perform search
    result = await search_service.search(search_input)
    
    # Verify result structure
    assert isinstance(result, SearchOutput)
    assert result.rewritten_query  # Should have some value
    assert isinstance(result.query_results, list)
    assert isinstance(result.answer, str)
    assert len(result.documents) > 0
    assert result.documents[0].document_name == test_file.filename

@pytest.mark.asyncio
async def test_search_with_user_preference(
    db: Session,
    search_service: SearchService,
    test_collection: Collection,
    test_config: dict
):
    """Test search with user provider preference."""
    # Create alternate provider
    alt_provider = ProviderModelConfig(
        model_id="alt-model",
        provider_name="test-provider",
        api_key="alt-key",
        default_model_id="alt",
        parameters_id=test_config['parameters'].id,
        is_default=False,
        is_active=True
    )
    db.add(alt_provider)
    db.commit()
    
    # Create user preference
    user_id = uuid4()
    pref = UserProviderPreference(
        user_id=user_id,
        provider_config_id=alt_provider.id
    )
    db.add(pref)
    db.commit()
    
    # Create search input
    search_input = SearchInput(
        question="What is the capital of France?",
        collection_id=test_collection.id
    )
    
    # Perform search with user ID
    result = await search_service.search(search_input, user_id=user_id)
    
    # Verify result uses alternate provider
    pipeline = search_service._initialize_pipeline(user_id)
    assert pipeline.provider.model_id == "alt-model"

@pytest.mark.asyncio
async def test_search_collection_not_found(
    search_service: SearchService
):
    """Test handling of missing collection."""
    search_input = SearchInput(
        question="test query",
        collection_id=uuid4()  # Random non-existent ID
    )
    
    with pytest.raises(HTTPException) as exc:
        await search_service.search(search_input)
    assert exc.value.status_code == 404
    assert "Collection not found" in str(exc.value.detail)

@pytest.mark.asyncio
async def test_search_no_config(
    db: Session,
    search_service: SearchService,
    test_collection: Collection
):
    """Test handling of missing configuration."""
    # Create search input
    search_input = SearchInput(
        question="test query",
        collection_id=test_collection.id
    )
    
    with pytest.raises(HTTPException) as exc:
        await search_service.search(search_input)
    assert exc.value.status_code == 500
    assert "No valid provider configuration found" in str(exc.value.detail)

def test_prepare_query(search_service: SearchService):
    """Test query preparation."""
    # Test boolean operator removal
    query = "term1 AND term2 OR term3"
    clean = search_service._prepare_query(query)
    assert clean == "term1 term2 term3"
    
    # Test parentheses removal
    query = "(term1) AND (term2)"
    clean = search_service._prepare_query(query)
    assert clean == "term1 term2"

def test_clean_generated_answer(search_service: SearchService):
    """Test answer cleaning."""
    # Test duplicate removal
    answer = "line1\nline1\nline2"
    clean = search_service._clean_generated_answer(answer)
    assert clean == "line1\nline2"
    
    # Test empty answer
    assert search_service._clean_generated_answer("") == ""
    
    # Test whitespace cleanup
    answer = "  line1  \n  line2  "
    clean = search_service._clean_generated_answer(answer)
    assert clean == "line1\nline2"
    
    # Test boolean prefix removal
    answer = "AND (relevant info)\nAND (more info)"
    clean = search_service._clean_generated_answer(answer)
    assert clean == "relevant info\nmore info"

@pytest.mark.asyncio
async def test_search_invalid_query(
    db: Session,
    search_service: SearchService,
    test_collection: Collection,
    test_config: dict
):
    """Test handling of invalid query."""
    # Create search input with empty query
    search_input = SearchInput(
        question="   ",  # Empty after stripping
        collection_id=test_collection.id
    )
    
    with pytest.raises(ValueError, match="Query cannot be empty"):
        await search_service.search(search_input)

@pytest.mark.asyncio
async def test_search_with_evaluation(
    db: Session,
    search_service: SearchService,
    test_collection: Collection,
    test_file: File,
    test_config: dict
):
    """Test search with runtime evaluation."""
    # Store original setting
    original_eval = settings.runtime_eval
    
    try:
        # Enable runtime evaluation
        settings.runtime_eval = True
        
        # Create search input
        search_input = SearchInput(
            question="What is the capital of France?",
            collection_id=test_collection.id
        )
        
        # Perform search
        result = await search_service.search(search_input)
        
        # Verify evaluation results
        assert result.evaluation is not None
        assert isinstance(result.evaluation, dict)
        assert "score" in result.evaluation
    finally:
        # Restore original setting
        settings.runtime_eval = original_eval

@pytest.mark.asyncio
async def test_search_with_context(
    db: Session,
    search_service: SearchService,
    test_collection: Collection,
    test_file: File,
    test_config: dict
):
    """Test search with context."""
    # Create search input
    search_input = SearchInput(
        question="What is the capital of France?",
        collection_id=test_collection.id
    )
    
    # Add context
    context = {
        "user_role": "student",
        "language": "en",
        "detail_level": "high"
    }
    
    # Perform search with context
    result = await search_service.search(search_input, context=context)
    
    # Verify context was used in query rewriting
    assert result.rewritten_query != search_input.question
    assert isinstance(result.rewritten_query, str)
    assert len(result.rewritten_query) > 0

@pytest.mark.asyncio
async def test_query_rewriting(
    db: Session,
    search_service: SearchService,
    test_collection: Collection,
    test_file: File,
    test_config: dict
):
    """Test query rewriting."""
    # Test cases for query rewriting
    test_cases = [
        ("capital France", "What is the capital of France?"),  # Expand keywords
        ("who built eiffel tower?", "Who was responsible for constructing the Eiffel Tower?"),  # Rephrase
        ("paris weather", "What is the current weather in Paris?")  # Add context
    ]
    
    for original, expected_type in test_cases:
        # Create search input
        search_input = SearchInput(
            question=original,
            collection_id=test_collection.id
        )
        
        # Perform search
        result = await search_service.search(search_input)
        
        # Verify query was rewritten
        assert result.rewritten_query != original
        assert isinstance(result.rewritten_query, str)
        assert len(result.rewritten_query) > 0

@pytest.mark.asyncio
async def test_document_metadata_generation(
    db: Session,
    search_service: SearchService,
    test_collection: Collection,
    test_config: dict
):
    """Test document metadata generation."""
    # Create multiple files
    files = []
    for i in range(3):
        file = File(
            filename=f"doc{i}.txt",
            document_id=f"doc{i}",
            collection_id=test_collection.id,
            metadata=FileMetadata(
                total_pages=i+1,
                total_chunks=i+1,
                keywords=[f"test{i}"]
            )
        )
        db.add(file)
        files.append(file)
    db.commit()
    
    # Create search input
    search_input = SearchInput(
        question="test query",
        collection_id=test_collection.id
    )
    
    # Perform search
    result = await search_service.search(search_input)
    
    # Verify document metadata
    assert len(result.documents) == len(files)
    for doc in result.documents:
        assert doc.document_name in [f"doc{i}.txt" for i in range(3)]
        assert doc.total_pages is not None
        assert doc.total_chunks is not None
        assert doc.keywords is not None
