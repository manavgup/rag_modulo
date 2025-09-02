"""Tests for SearchService with PipelineService integration."""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import settings
from core.custom_exceptions import ConfigurationError, LLMProviderError
from core.logging_utils import get_logger
from rag_solution.schemas.collection_schema import CollectionInput
from rag_solution.schemas.file_schema import FileInput
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.schemas.user_schema import UserInput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.search_service import SearchService
from rag_solution.services.user_service import UserService
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, QueryResult, Source
from vectordbs.milvus_store import MilvusStore

logger = get_logger("tests.rag_solution.services.test_search_service")


# -------------------------------------------
# 🧪 TEST CASES
# -------------------------------------------


@pytest.mark.asyncio
async def test_search_basic(search_service: SearchService, base_collection, base_file, base_user, base_pipeline_config):
    """Test basic search functionality with pipeline service."""
    search_input = SearchInput(
        question="What is the capital of France?",
        collection_id=base_collection.id,
        pipeline_id=base_pipeline_config["pipeline"].id,
    )

    context = {
        "user_preferences": {"language": "en"},
        "session_data": {"previous_queries": ["What is France known for?"]},
    }
    result = await search_service.search(search_input, base_user.id, context=context)

    assert isinstance(result, SearchOutput)
    assert len(result.documents) > 0
    assert result.documents[0].document_name == "test.txt"
    assert result.rewritten_query is not None
    assert result.query_results is not None


@pytest.mark.asyncio
async def test_search_no_results(
    search_service: SearchService,
    base_collection,
    base_user,
    base_pipeline_config,
    base_file_with_content,  # Use the new fixture to ensure the collection has a file
):
    """Test search with a query that has no matching documents."""
    search_input = SearchInput(
        question="What is the capital of Mars?",  # Query that won't match any documents
        collection_id=base_collection.id,
        pipeline_id=base_pipeline_config["pipeline"].id,
    )

    context = {
        "user_preferences": {"language": "en"},
        "session_data": {"previous_queries": ["What is France known for?"]},
    }

    result = await search_service.search(search_input, base_user.id, context=context)

    assert isinstance(result, SearchOutput)
    assert len(result.documents) == 0  # No matching documents found
    assert result.rewritten_query is not None
    assert result.answer == "I apologize, but couldn't find any relevant documents."


@pytest.mark.asyncio
async def test_search_invalid_collection(search_service: SearchService, base_user, base_pipeline_config):
    """Test search with an invalid collection ID."""
    search_input = SearchInput(
        question="Test question",
        collection_id=str(UUID4(int=0)),  # Invalid UUID
        pipeline_id=base_pipeline_config["pipeline"].id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input, base_user.id)
    assert exc_info.value.status_code == 404
    assert "Collection with ID 00000000-0000-0000-0000-000000000000 not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_search_unauthorized_collection(search_service: SearchService, db_session, base_pipeline_config):
    """Test search with a collection the user doesn't have access to."""
    # Create a new user and collection
    user_service = UserService(db_session)
    collection_service = CollectionService(db_session)

    unauthorized_user = user_service.create_user(
        UserInput(
            name="Unauthorized User",
            email=f"unauthorized{uuid.uuid4()}@example.com",  # Unique email
            ibm_id=f"unauthorized-ibm-id-{uuid.uuid4()}",  # Unique IBM ID
        )
    )

    # Initialize default templates for the user
    prompt_template_service = PromptTemplateService(db_session)
    prompt_template_service.initialize_default_templates(unauthorized_user.id, "watsonx")

    # Create LLM parameters
    llm_params_service = LLMParametersService(db_session)
    llm_params_service.create_or_update_parameters(
        unauthorized_user.id,
        LLMParametersInput(
            name="test-params", temperature=0.7, max_new_tokens=1000, top_k=50, top_p=0.95, is_default=True
        ),
    )

    # Create private collection without parameters
    private_collection = collection_service.create_collection(
        CollectionInput(
            name="Private Collection",
            is_private=True,
            users=[],  # No users have access
            status="created",
        )
    )

    search_input = SearchInput(
        question="Test question", collection_id=private_collection.id, pipeline_id=base_pipeline_config["pipeline"].id
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input, unauthorized_user.id)
    assert exc_info.value.status_code == 404
    assert "Collection not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_search_multiple_documents(
    search_service: SearchService, db_session, base_user, base_collection, base_pipeline_config, provider_factory
):
    """Test search with multiple documents in a collection."""
    file_service = FileManagementService(db_session)
    watsonx = provider_factory.get_provider("watsonx")
    store = MilvusStore()
    store._connect(settings.milvus_host, settings.milvus_port)

    # Create multiple test files
    files_data = [
        {"filename": "france.txt", "text": "Paris is the capital of France. It is known for the Eiffel Tower."},
        {"filename": "germany.txt", "text": "Berlin is the capital of Germany. It is known for its rich history."},
    ]

    documents = []
    for file_info in files_data:
        file_schema = FileInput(
            collection_id=base_collection.id,
            filename=file_info["filename"],
            file_path=f"/path/to/{file_info['filename']}",
            file_type="txt",
            document_id=file_info["filename"].split(".")[0],
            metadata={"total_pages": 1, "total_chunks": 1, "keywords": {"test": True}},
        )
        file_service.create_file(file_schema, base_user.id)

        embeddings = watsonx.get_embeddings(file_info["text"])
        chunk = DocumentChunk(
            chunk_id=f"chunk_{file_info['filename']}",
            text=file_info["text"],
            embeddings=embeddings[0],
            metadata=DocumentChunkMetadata(
                source=Source.OTHER,
                document_id=file_info["filename"].split(".")[0],
                page_number=1,
                chunk_number=1,
                start_index=0,
                end_index=len(file_info["text"]),
            ),
            document_id=file_info["filename"].split(".")[0],
        )
        document = Document(document_id=file_info["filename"].split(".")[0], name=file_info["filename"], chunks=[chunk])
        documents.append(document)

    # Add documents to vector store
    store.delete_collection(base_collection.vector_db_name)
    store.create_collection(base_collection.vector_db_name, {"embedding_model": settings.embedding_model})
    store.add_documents(base_collection.vector_db_name, documents)

    # Perform search
    search_input = SearchInput(
        question="What are the capitals of European countries?",
        collection_id=base_collection.id,
        pipeline_id=base_pipeline_config["pipeline"].id,
    )

    result = await search_service.search(search_input, base_user.id)

    assert isinstance(result, SearchOutput)
    assert len(result.documents) == 2
    assert {doc.document_name for doc in result.documents} == {"france.txt", "germany.txt"}


@pytest.mark.asyncio
async def test_search_invalid_pipeline(search_service: SearchService, base_collection, base_user):
    """Test search with an invalid pipeline ID."""
    search_input = SearchInput(
        question="Test question",
        collection_id=base_collection.id,
        pipeline_id=str(UUID4(int=0)),  # Invalid UUID
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input, base_user.id)
    assert exc_info.value.status_code == 404
    assert "Pipeline configuration not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_search_empty_question(search_service: SearchService, base_collection, base_user, base_pipeline_config):
    """Test search with empty question string."""
    search_input = SearchInput(
        question="", collection_id=base_collection.id, pipeline_id=base_pipeline_config["pipeline"].id
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input, base_user.id)
    assert exc_info.value.status_code == 400
    assert "Query cannot be empty" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_search_vector_store_error(
    search_service: SearchService, base_collection, base_user, base_pipeline_config, mocker
):
    """Test search when vector store connection fails."""
    mocker.patch("vectordbs.milvus_store.MilvusStore._connect", side_effect=Exception("Connection failed"))

    search_input = SearchInput(
        question="Test question", collection_id=base_collection.id, pipeline_id=base_pipeline_config["pipeline"].id
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input, base_user.id)
    assert exc_info.value.status_code == 500
    assert "Connection failed" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_search_llm_provider_error(
    search_service: SearchService, base_collection, base_user, base_pipeline_config, mocker, caplog
):
    """Test search when LLM provider fails."""
    caplog.set_level("DEBUG")
    logger.info("Starting test_search_llm_provider_error")

    error = LLMProviderError(provider="watsonx", error_type="generation_failed", message="LLM provider error")
    logger.debug(f"Created LLMProviderError: {error}")

    # First mock retrieve_documents to ensure we get some results
    mock_results = [
        QueryResult(
            document_id="test_doc",
            chunk=DocumentChunk(
                chunk_id="chunk1",
                text="test content",
                embeddings=[0.1, 0.2],
                metadata=DocumentChunkMetadata(source=Source.OTHER),
            ),
            score=0.9,
            embeddings=[0.1, 0.2],
        )
    ]
    mocker.patch(
        "rag_solution.services.pipeline_service.PipelineService._retrieve_documents", return_value=mock_results
    )

    # Then mock generate_answer to raise our error
    mocker.patch("rag_solution.services.pipeline_service.PipelineService._generate_answer", side_effect=error)

    search_input = SearchInput(
        question="Test question", collection_id=base_collection.id, pipeline_id=base_pipeline_config["pipeline"].id
    )
    logger.debug(f"Created search input: {search_input}")

    with pytest.raises(HTTPException) as exc_info:
        await search_service.search(search_input, base_user.id)

    assert exc_info.value.status_code == 500
    assert "LLM provider error" in str(exc_info.value.detail)

    logger.info("Test completed successfully")


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


def test_generate_document_metadata_missing_files(search_service: SearchService, base_collection, base_user):
    # Create query results with non-existent document IDs
    query_results = [
        QueryResult(
            document_id="nonexistent1",
            chunk=DocumentChunk(
                chunk_id="chunk1",
                text="test",
                embeddings=[0.1, 0.2],
                metadata=DocumentChunkMetadata(source=Source.OTHER),
            ),
            score=0.9,
            embeddings=[0.1, 0.2],
        ),
        QueryResult(
            document_id="nonexistent2",
            chunk=DocumentChunk(
                chunk_id="chunk2",
                text="test",
                embeddings=[0.1, 0.2],
                metadata=DocumentChunkMetadata(source=Source.OTHER),
            ),
            score=0.9,
            embeddings=[0.1, 0.2],
        ),
    ]

    metadata = search_service._generate_document_metadata(query_results, base_collection.id)
    assert len(metadata) == 0


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
async def test_initialize_pipeline_error(search_service: SearchService, base_collection, mocker):
    """Test pipeline initialization error."""
    mocker.patch.object(
        search_service.pipeline_service, "initialize", side_effect=ConfigurationError("Pipeline initialization failed")
    )

    with pytest.raises(HTTPException) as exc_info:
        await search_service._initialize_pipeline(base_collection.id)
    assert exc_info.value.status_code == 500
    assert "Pipeline initialization failed" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_search_with_context(
    search_service: SearchService,
    base_collection,
    base_file_with_content,  # Use the new fixture to ensure the collection has a file
    base_user,
    test_config,
    indexed_documents,  # ,  # Use the indexed_documents fixture
):
    search_input = SearchInput(
        question="What is the capital of France?",
        collection_id=base_collection.id,
        pipeline_id=test_config["pipeline"].id,
    )

    context = {
        "user_preferences": {"language": "en"},
        "session_data": {"previous_queries": ["What is France known for?"]},
    }

    result = await search_service.search(search_input, base_user.id, context=context)

    assert isinstance(result, SearchOutput)
    assert len(result.documents) > 0
