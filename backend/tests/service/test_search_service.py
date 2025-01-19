"""Tests for SearchService with PipelineService integration."""

import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID
from datetime import datetime
from unittest.mock import Mock, patch

from rag_solution.services.search_service import SearchService
from rag_solution.services.user_service import UserService
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.repository.pipeline_repository import PipelineConfigRepository
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.schemas.user_schema import UserInput
from rag_solution.schemas.collection_schema import CollectionInput
from rag_solution.schemas.file_schema import FileInput
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.generation.providers.watsonx import WatsonXLLM
from vectordbs.milvus_store import MilvusStore
from core.custom_exceptions import ConfigurationError, NotFoundError
from core.config import settings


# -------------------------------------------
# 🔧 FIXTURES
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
def test_file(db_session: Session, test_collection, test_user, test_config, provider_factory: LLMProviderFactory):
    """Create a test file and add its content to vector store."""
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

    text = "Paris is the capital of France. It is known for the Eiffel Tower."
    watsonx = provider_factory.get_provider("watsonx")
    embeddings = watsonx.get_embeddings(text)

    chunk = DocumentChunk(
        chunk_id="chunk1",
        text=text,
        embeddings=embeddings[0],
        metadata=DocumentChunkMetadata(
            source=Source.OTHER,
            document_id="doc1",
            page_number=1,
            chunk_number=1,
            start_index=0,
            end_index=len(text)
        ),
        document_id="doc1"
    )
    document = Document(
        document_id="doc1",
        name="test.txt",
        chunks=[chunk]
    )

    store = MilvusStore()
    store._connect(settings.milvus_host, settings.milvus_port)
    
    try:
        store.delete_collection(test_collection.vector_db_name)
    except:
        pass

    store.create_collection(test_collection.vector_db_name, {"embedding_model": settings.embedding_model})
    store.add_documents(test_collection.vector_db_name, [document])

    yield file

    try:
        store.delete_collection(test_collection.vector_db_name)
    except:
        pass


@pytest.fixture
def test_config(db_session: Session, test_user, test_collection):
    """Create test configurations for user."""
    parameters_service = LLMParametersService(db_session)
    template_service = PromptTemplateService(db_session)
    pipeline_repository = PipelineConfigRepository(db_session)
    provider_service = LLMProviderService(db_session)
    
    # Get existing WatsonX provider
    watsonx_provider = provider_service.get_provider_by_name("watsonx")
    if not watsonx_provider:
        raise ValueError("WatsonX provider not found")

    parameters_input = LLMParametersInput(
        name="test-parameters",
        temperature=0.7,
        max_new_tokens=1000,
        top_k=50,
        top_p=0.95,
        is_default=True
    )
    parameters = parameters_service.create_or_update_parameters(
        test_user.id,
        parameters_input
    )

    templates = {}
    for template_type in [PromptTemplateType.RAG_QUERY, PromptTemplateType.RESPONSE_EVALUATION]:
        template_input = PromptTemplateInput(
            name=f"test-{template_type.value}",
            provider="watsonx",
            template_type=template_type,
            template_format="Context:\n{context}\nQuestion:{question}",
            input_variables={"context": "Retrieved passages from knowledge base", "question": "User's question to answer"},
            is_default=True
        )
        templates[template_type] = template_service.create_or_update_template(
            test_user.id,
            template_input
        )

    pipeline_config = pipeline_repository.create({
        "name": "test-pipeline",
        "description": "Test pipeline configuration",
        "chunking_strategy": "fixed",
        "embedding_model": "sentence-transformers/all-minilm-l6-v2",
        "retriever": "vector",
        "context_strategy": "simple",
        "provider_id": watsonx_provider.id,  # Use existing WatsonX provider ID
        "collection_id": test_collection.id,
        "enable_logging": True,
        "max_context_length": 2048,
        "timeout": 30.0
    })

    return {
        'parameters': parameters,
        'templates': templates,
        'pipeline': pipeline_config
    }


# -------------------------------------------
# 🧪 TEST CASES
# -------------------------------------------

@pytest.mark.asyncio
async def test_search_basic(
    search_service: SearchService,
    test_collection,
    test_file,
    test_user,
    test_config
):
    """Test basic search functionality with pipeline service."""
    search_input = SearchInput(
        question="What is the capital of France?",
        collection_id=test_collection.id,
        pipeline_id=test_config['pipeline'].id
    )
    
    result = await search_service.search(search_input, test_user.id)
    
    assert isinstance(result, SearchOutput)
    assert len(result.documents) > 0
    assert result.documents[0].document_name == test_file.filename
    assert result.rewritten_query is not None
    assert result.query_results is not None

@pytest.mark.asyncio
async def test_search_no_results(
    search_service: SearchService,
    test_collection,
    test_user,
    test_config
):
    """Test search with a query that has no matching documents."""
    search_input = SearchInput(
        question="What is the capital of Mars?",
        collection_id=test_collection.id,
        pipeline_id=test_config['pipeline'].id
    )

    result = await search_service.search(search_input, test_user.id)

    assert isinstance(result, SearchOutput)
    assert len(result.documents) == 0
    assert result.rewritten_query is not None

@pytest.mark.asyncio
async def test_search_invalid_collection(
    search_service: SearchService,
    test_user,
    test_config
):
    """Test search with an invalid collection ID."""
    search_input = SearchInput(
        question="Test question",
        collection_id=str(UUID(int=0)),  # Invalid UUID
        pipeline_id=test_config['pipeline'].id
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input, test_user.id)
    assert exc_info.value.status_code == 404
    assert "Collection not found" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_search_unauthorized_collection(
    search_service: SearchService,
    db_session: Session,
    test_config
):
    """Test search with a collection the user doesn't have access to."""
    # Create a new user and collection
    user_service = UserService(db_session)
    collection_service = CollectionService(db_session)

    unauthorized_user = user_service.create_user(UserInput(
        name="Unauthorized User",
        email="unauthorized@example.com",
        ibm_id="unauthorized-ibm-id"
    ))

    # Create LLM parameters
    llm_params_service = LLMParametersService(db_session)
    llm_params = llm_params_service.create_or_update_parameters(
        unauthorized_user.id,
        LLMParametersInput(
            name="test-params",
            temperature=0.7,
            max_new_tokens=1000,
            top_k=50,
            top_p=0.95,
            is_default=True
        )
    )

    # Create private collection without parameters
    private_collection = collection_service.create_collection(CollectionInput(
        name="Private Collection",
        is_private=True,
        users=[],
        status="created"
    ))

    search_input = SearchInput(
        question="Test question",
        collection_id=private_collection.id,
        pipeline_id=test_config['pipeline'].id
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input, unauthorized_user.id)
    assert exc_info.value.status_code == 404
    assert "Collection not found" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_search_multiple_documents(
    search_service: SearchService,
    db_session: Session,
    test_user,
    test_collection,
    test_config,
    provider_factory: LLMProviderFactory
):
    """Test search with multiple documents in a collection."""
    file_service = FileManagementService(db_session)
    watsonx = provider_factory.get_provider("watsonx")
    store = MilvusStore()
    store._connect(settings.milvus_host, settings.milvus_port)

    # Create multiple test files
    files_data = [
        {
            "filename": "france.txt",
            "text": "Paris is the capital of France. It is known for the Eiffel Tower."
        },
        {
            "filename": "germany.txt",
            "text": "Berlin is the capital of Germany. It is known for its rich history."
        }
    ]

    documents = []
    for file_info in files_data:
        file_schema = FileInput(
            collection_id=test_collection.id,
            filename=file_info["filename"],
            file_path=f"/path/to/{file_info['filename']}",
            file_type="txt",
            document_id=file_info["filename"].split('.')[0],
            metadata={
                "total_pages": 1,
                "total_chunks": 1,
                "keywords": {"test": True}
            }
        )
        file = file_service.create_file(file_schema, test_user.id)

        embeddings = watsonx.get_embeddings(file_info["text"])
        chunk = DocumentChunk(
            chunk_id=f"chunk_{file_info['filename']}",
            text=file_info["text"],
            embeddings=embeddings[0],
            metadata=DocumentChunkMetadata(
                source=Source.OTHER,
                document_id=file_info["filename"].split('.')[0],
                page_number=1,
                chunk_number=1,
                start_index=0,
                end_index=len(file_info["text"])
            ),
            document_id=file_info["filename"].split('.')[0]
        )
        document = Document(
            document_id=file_info["filename"].split('.')[0],
            name=file_info["filename"],
            chunks=[chunk]
        )
        documents.append(document)

    # Add documents to vector store
    store.delete_collection(test_collection.vector_db_name)
    store.create_collection(test_collection.vector_db_name, {"embedding_model": settings.embedding_model})
    store.add_documents(test_collection.vector_db_name, documents)

    # Perform search
    search_input = SearchInput(
        question="What are the capitals of European countries?",
        collection_id=test_collection.id,
        pipeline_id=test_config['pipeline'].id
    )

    result = await search_service.search(search_input, test_user.id)

    assert isinstance(result, SearchOutput)
    assert len(result.documents) == 2
    assert {doc.document_name for doc in result.documents} == {"france.txt", "germany.txt"}

@pytest.mark.asyncio
async def test_search_invalid_pipeline(
    search_service: SearchService,
    test_collection,
    test_user
):
    """Test search with an invalid pipeline ID."""
    search_input = SearchInput(
        question="Test question",
        collection_id=test_collection.id,
        pipeline_id=str(UUID(int=0))  # Invalid UUID
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input, test_user.id)
    assert exc_info.value.status_code == 404
    assert "Pipeline configuration not found" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_search_empty_question(
    search_service: SearchService,
    test_collection,
    test_user,
    test_config
):
    """Test search with empty question string."""
    search_input = SearchInput(
        question="",
        collection_id=test_collection.id,
        pipeline_id=test_config['pipeline'].id
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input, test_user.id)
    assert exc_info.value.status_code == 400
    assert "Query cannot be empty" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_search_vector_store_error(
    search_service: SearchService,
    test_collection,
    test_user,
    test_config,
    mocker
):
    """Test search when vector store connection fails."""
    mocker.patch('vectordbs.milvus_store.MilvusStore._connect', 
                side_effect=Exception("Connection failed"))
    
    search_input = SearchInput(
        question="Test question",
        collection_id=test_collection.id,
        pipeline_id=test_config['pipeline'].id
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input, test_user.id)
    assert exc_info.value.status_code == 500
    assert "Connection failed" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_search_llm_provider_error(
    search_service: SearchService,
    test_collection,
    test_user,
    test_config,
    mocker
):
    """Test search when LLM provider fails."""
    mocker.patch('rag_solution.generation.providers.watsonx.WatsonXLLM.get_embeddings',
                side_effect=Exception("LLM provider error"))
    
    search_input = SearchInput(
        question="Test question",
        collection_id=test_collection.id,
        pipeline_id=test_config['pipeline'].id
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input, test_user.id)
    assert exc_info.value.status_code == 500
    assert "LLM provider error" in str(exc_info.value.detail)

def test_clean_generated_answer(search_service: SearchService):
    """Test cleaning of generated answers."""
    test_cases = [
        # Remove AND prefixes
        ("AND this AND that", "this that"),
        # Remove duplicate words
        ("the the answer answer is is here here", "the answer is here"),
        # Handle multiple spaces
        ("answer   with   extra   spaces", "answer with extra spaces"),
        # Handle empty input
        ("", ""),
        # Handle single word
        ("answer", "answer"),
        # Handle special characters
        ("AND answer! AND with? AND punctuation.", "answer! with? punctuation."),
    ]
    
    for input_text, expected in test_cases:
        cleaned = search_service._clean_generated_answer(input_text)
        assert cleaned == expected

def test_generate_document_metadata_missing_files(
    search_service: SearchService,
    test_collection,
    test_user
):
    """Test metadata generation with missing files."""
    # Create query results with non-existent document IDs
    query_results = [
        QueryResult(
            document_id="nonexistent1",
            data=[DocumentChunk(chunk_id="chunk1", text="test")]
        ),
        QueryResult(
            document_id="nonexistent2",
            data=[DocumentChunk(chunk_id="chunk2", text="test")]
        )
    ]
    
    metadata = search_service._generate_document_metadata(
        query_results,
        test_collection.id
    )
    assert len(metadata) == 0

def test_generate_document_metadata_error(
    search_service: SearchService,
    test_collection,
    mocker
):
    """Test metadata generation with file service error."""
    mocker.patch.object(
        search_service.file_service,
        'get_files_by_collection',
        side_effect=Exception("File service error")
    )
    
    query_results = [
        QueryResult(
            document_id="test",
            data=[DocumentChunk(chunk_id="chunk1", text="test")]
        )
    ]
    
    with pytest.raises(ConfigurationError) as exc_info:
        search_service._generate_document_metadata(
            query_results,
            test_collection.id
        )
    assert "Metadata generation failed" in str(exc_info.value)

def test_lazy_service_initialization(db_session: Session):
    """Test lazy initialization of services."""
    service = SearchService(db_session)
    
    # Initially services should be None
    assert service._file_service is None
    assert service._collection_service is None
    assert service._pipeline_service is None
    
    # Access services to trigger initialization
    assert service.file_service is not None
    assert service.collection_service is not None
    assert service.pipeline_service is not None
    
    # Services should remain initialized
    assert service._file_service is not None
    assert service._collection_service is not None
    assert service._pipeline_service is not None

@pytest.mark.asyncio
async def test_initialize_pipeline_error(
    search_service: SearchService,
    test_collection,
    mocker
):
    """Test pipeline initialization error."""
    mocker.patch.object(
        search_service.pipeline_service,
        'initialize',
        side_effect=ConfigurationError("Pipeline initialization failed")
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await search_service._initialize_pipeline(test_collection.id)
    assert exc_info.value.status_code == 500
    assert "Pipeline initialization failed" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_search_with_context(
    search_service: SearchService,
    test_collection,
    test_file,
    test_user,
    test_config
):
    """Test search with additional context."""
    search_input = SearchInput(
        question="What is the capital of France?",
        collection_id=test_collection.id,
        pipeline_id=test_config['pipeline'].id
    )
    
    context = {
        "user_preferences": {"language": "en"},
        "session_data": {"previous_queries": ["What is France known for?"]}
    }
    
    result = await search_service.search(
        search_input,
        test_user.id,
        context=context
    )
    
    assert isinstance(result, SearchOutput)
    assert len(result.documents) > 0
    assert result.metadata is not None
    assert "execution_time" in result.metadata
