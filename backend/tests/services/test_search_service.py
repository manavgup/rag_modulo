"""Tests for SearchService."""

import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID
from datetime import datetime

from rag_solution.services.search_service import SearchService
from rag_solution.services.user_service import UserService
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.provider_config_service import ProviderConfigService
from rag_solution.services.runtime_config_service import RuntimeConfigService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.schemas.user_schema import UserInput
from rag_solution.schemas.collection_schema import CollectionInput
from rag_solution.schemas.file_schema import FileInput
from rag_solution.schemas.llm_parameters_schema import LLMParametersCreate
from rag_solution.schemas.provider_config_schema import ProviderConfig, ProviderRuntimeSettings
from rag_solution.schemas.prompt_template_schema import PromptTemplateCreate
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source
from rag_solution.generation.providers.watsonx import WatsonXProvider
from vectordbs.milvus_store import MilvusStore
from core.custom_exceptions import ConfigurationError
from core.config import settings


# -------------------------------------------
# 🛠️ FIXTURES
# -------------------------------------------

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user."""
    user_service = UserService(db_session)
    user_schema = UserInput(
        name="Test User",
        email="testuser@example.com",
        ibm_id="test-ibm-id"
    )
    return user_service.create_user(user_schema)


@pytest.fixture
def search_service(db_session: Session):
    """Create an instance of SearchService."""
    return SearchService(db_session)


@pytest.fixture
def test_collection(db_session: Session, test_user):
    """Create a test collection."""
    collection_service = CollectionService(db_session)
    collection_schema = CollectionInput(
        name="test-collection",
        is_private=False,
        users=[test_user.id],
        status="created"
    )
    return collection_service.create_collection(collection_schema)


@pytest.fixture
def test_file(db_session: Session, test_collection, test_user, test_config):
    """Create a test file and add its content to vector store."""
    # Create file record in database
    file_service = FileManagementService(db_session)
    file_schema = FileInput(
        collection_id=test_collection.id,
        filename="test.txt",
        file_path="/path/to/test.txt",
        file_type="txt",
        document_id="doc1",
        metadata={
            "total_pages": 1,
            "total_chunks": 1,
            "keywords": {"test": True}
        }
    )
    file = file_service.create_file(file_schema, test_user.id)

    # Get embeddings using WatsonX provider
    text = "Paris is the capital of France. It is known for the Eiffel Tower."
    provider_service = ProviderConfigService(db_session)
    watsonx = WatsonXProvider(provider_service)
    embeddings = watsonx.get_embeddings(text)

    # Create document for vector store
    chunk = DocumentChunk(
        chunk_id="chunk1",
        text=text,
        embeddings=embeddings[0],  # First embedding since we only have one text
        metadata=DocumentChunkMetadata(
            source=Source.OTHER,
            document_id="doc1",
            page_number=1,
            chunk_number=1,
            start_index=0,  # Add start_index
            end_index=len(text)  # Add end_index
        ),
        document_id="doc1"
    )
    document = Document(
        document_id="doc1",
        name="test.txt",
        chunks=[chunk]
    )

    # Add to vector store
    store = MilvusStore()
    store._connect(settings.milvus_host, settings.milvus_port)
    
    # Delete collection if it exists
    try:
        store.delete_collection(test_collection.vector_db_name)
    except:
        pass
    
    # Create collection and add documents
    store.create_collection(test_collection.vector_db_name, {"embedding_model": settings.embedding_model})
    store.add_documents(test_collection.vector_db_name, [document])

    yield file

    # Cleanup vector store collection
    try:
        store.delete_collection(test_collection.vector_db_name)
    except:
        pass


@pytest.fixture
def test_config(db_session: Session):
    """Get existing test configurations for LLM."""
    provider_service = ProviderConfigService(db_session)
    template_service = PromptTemplateService(db_session)
    
    # Get existing provider config
    provider = provider_service.get_provider_config("watsonx")
    if not provider:
        raise ValueError("WatsonX provider configuration not found")
        
    # Get default template for watsonx provider
    template = template_service.get_default_template("watsonx")
    if not template:
        raise ValueError("Default template not found")
    
    return {
        'provider': provider,
        'template': template
    }


# -------------------------------------------
# 🧪 TEST CASES
# -------------------------------------------

@pytest.mark.asyncio
async def test_search_basic(
    search_service: SearchService,
    test_collection,
    test_file
):
    """Test basic search functionality."""
    search_input = SearchInput(
        question="What is the capital of France?",
        collection_id=test_collection.id
    )
    
    result = await search_service.search(search_input)
    
    assert isinstance(result, SearchOutput)
    assert len(result.documents) > 0
    assert result.documents[0].document_name == test_file.filename


def test_prepare_query(search_service: SearchService):
    """Test query preprocessing."""
    assert search_service._prepare_query("term1 AND term2 OR term3") == "term1 term2 term3"
    assert search_service._prepare_query("(term1) AND (term2)") == "term1 term2"


def test_clean_generated_answer(search_service: SearchService):
    """Test answer cleaning."""
    # Test removing AND prefix
    assert search_service._clean_generated_answer("AND info1") == "info1"
    
    # Test preserving parentheses when they wrap the entire content
    assert search_service._clean_generated_answer("(info1 AND info2)") == "(info1 info2)"
    
    # Test removing AND prefix and preserving parentheses
    assert search_service._clean_generated_answer("AND (info1)\nAND (info2)") == "(info1) (info2)"
    
    # Test deduplication
    assert search_service._clean_generated_answer("info1\ninfo1\ninfo2") == "info1 info2"
    
    # Test multiple AND prefixes and parentheses
    assert search_service._clean_generated_answer("  AND (info1) AND (info2) ") == "(info1) (info2)"
