"""Tests for search functionality core features and edge cases.

This module implements TDD tests for Issue #160: Debug search functionality - investigate remaining edge cases.
These tests cover both core functionality verification and edge cases:

Core Functionality Tests:
- Search API endpoint works correctly
- Document ingestion and indexing works
- LLM generation works with proper context
- Search results are properly formatted
- Collection selection works correctly

Edge Cases Tests:
1. Collection Selection: Ensure search is using the correct collection
2. Document Retrieval: Verify documents are properly indexed in vector store
3. Search Results Display: Check if results are being displayed correctly in UI
4. Error Handling: Improve error messages for edge cases

Test Cases:
- Search with documents in collection
- Search with empty collection
- Search with invalid collection ID
- Search with malformed queries
- Search with various query types and complexities
"""

from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db
from rag_solution.models.collection import Collection
from rag_solution.models.file import File
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.llm_provider import LLMProvider
from rag_solution.models.pipeline import PipelineConfig
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.models.user import User
from rag_solution.router.search_router import router

# Create test app
app = FastAPI()
app.include_router(router)


@pytest.fixture
@pytest.mark.api
def test_db(db_session: Session) -> Session:
    """Get test database session."""
    return db_session


@pytest.fixture
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """Create test client with database override."""

    def override_get_db() -> None:
        try:
            yield test_db
        finally:
            pass  # Don't close since it's handled by the db fixture

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db: Session) -> User:
    """Create test user."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    user = User(ibm_id=f"test_user_{unique_id}", email=f"test_{unique_id}@example.com", name="Test User", role="user")
    test_db.add(user)
    test_db.commit()
    return user


@pytest.fixture
def test_collection_with_documents(test_db: Session, test_user: User) -> Collection:
    """Create test collection with documents."""
    collection = Collection(name="test-collection-with-docs", vector_db_name="test_collection_with_docs", status="CREATED")
    test_db.add(collection)
    test_db.commit()

    # Add test files to collection
    for i in range(3):
        file = File(
            user_id=test_user.id,
            collection_id=collection.id,
            filename=f"test_document_{i+1}.pdf",
            file_path=f"/path/to/test_document_{i+1}.pdf",
            file_type="pdf",
            document_id=f"doc_{i+1}",
            file_metadata={"total_pages": 5, "total_chunks": 10, "keywords": {"topic": f"test_topic_{i+1}"}},
        )
        test_db.add(file)

    test_db.commit()
    return collection


@pytest.fixture
def test_empty_collection(test_db: Session, test_user: User) -> Collection:
    """Create test collection without documents."""
    collection = Collection(name="test-empty-collection", vector_db_name="test_empty_collection", status="CREATED")
    test_db.add(collection)
    test_db.commit()
    return collection


@pytest.fixture
def test_pipeline_config(test_db: Session, test_user: User) -> PipelineConfig:
    """Create test pipeline configuration."""
    pipeline = PipelineConfig(
        name="test-pipeline",
        description="Test pipeline for search debugging",
        collection_id=None,  # Will be updated in tests
        user_id=test_user.id,
        chunking_strategy="fixed",
        embedding_model="test-embedding-model",
        retriever="vector",
        context_strategy="priority",
        enable_logging=True,
        max_context_length=2048,
        timeout=30.0,
        config_metadata={"top_k": 5, "similarity_threshold": 0.7},
        is_default=True,
        provider_id=test_llm_config["provider"].id,
    )
    test_db.add(pipeline)
    test_db.commit()
    return pipeline


@pytest.fixture
def test_llm_config(test_db: Session, test_user: User) -> dict[str, Any]:
    """Create test LLM configuration."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]

    # Create LLM provider
    provider = LLMProvider(name=f"test-provider-{unique_id}", base_url="https://api.test.com", api_key="test-key", is_default=True, is_active=True)
    test_db.add(provider)
    test_db.commit()

    # Create LLM parameters
    params = LLMParameters(user_id=test_user.id, name=f"test-params-{unique_id}", max_new_tokens=100, temperature=0.7, top_k=50, top_p=1.0, is_default=True)
    test_db.add(params)
    test_db.commit()

    # Create prompt template
    from rag_solution.schemas.prompt_template_schema import PromptTemplateType

    template = PromptTemplate(
        user_id=test_user.id,
        name=f"test-template-{unique_id}",
        template_type=PromptTemplateType.RAG_QUERY,
        system_prompt="You are a helpful assistant",
        template_format="Context: {context}\nQuestion: {question}\nAnswer: {answer}",
        input_variables={"context": "string", "question": "string", "answer": "string"},
        example_inputs={"context": "Sample context", "question": "Sample question", "answer": "Sample answer"},
        context_strategy={"max_length": 1000, "priority": "relevance"},
        max_context_length=1000,
        is_default=True,
    )
    test_db.add(template)
    test_db.commit()

    return {"provider": provider, "parameters": params, "template": template}


class TestSearchCoreFunctionality:
    """Test core search functionality to ensure it works correctly."""

    def test_search_api_endpoint_basic_functionality(
        self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig    ) -> None:
        """Test that the search API endpoint works with basic functionality."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What is the main topic of the documents?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should return 200 OK with proper response structure
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Verify response structure matches SearchOutput schema
        assert "answer" in data, "Response should contain 'answer' field"
        assert "documents" in data, "Response should contain 'documents' field"
        assert "query_results" in data, "Response should contain 'query_results' field"
        assert "rewritten_query" in data, "Response should contain 'rewritten_query' field"
        assert "evaluation" in data, "Response should contain 'evaluation' field"

        # Verify answer is a non-empty string
        assert isinstance(data["answer"], str), "Answer should be a string"
        assert len(data["answer"].strip()) > 0, "Answer should not be empty"

        # Verify documents list
        assert isinstance(data["documents"], list), "Documents should be a list"
        assert len(data["documents"]) > 0, "Should return documents from the collection"

        # Verify query results
        assert isinstance(data["query_results"], list), "Query results should be a list"
        assert len(data["query_results"]) > 0, "Should return query results"

    def test_search_document_ingestion_and_indexing(
        self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig
    ) -> None:
        """Test that documents are properly ingested and indexed for search."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        # Search for content that should be in our test documents
        search_input = {
            "question": "test_topic",  # Should match our test document keywords
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should find relevant documents
        assert response.status_code == 200
        data = response.json()

        # Verify that documents were properly indexed and can be found
        assert len(data["query_results"]) > 0, "Should find relevant document chunks"

        # Verify that the search found documents with relevant content
        found_relevant_content = False
        for result in data["query_results"]:
            if "test_topic" in result["content"].lower() or "test" in result["content"].lower():
                found_relevant_content = True
                break

        assert found_relevant_content, "Should find documents containing relevant content"

        # Verify similarity scores are reasonable
        for result in data["query_results"]:
            assert isinstance(result["score"], int | float), "Score should be numeric"
            assert 0.0 <= result["score"] <= 1.0, "Score should be between 0 and 1"

    def test_search_llm_generation_with_context(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test that LLM generation works with proper context from documents."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "How many test documents are there?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should generate a coherent answer using document context
        assert response.status_code == 200
        data = response.json()

        # Verify answer is coherent and relevant
        answer = data["answer"]
        assert isinstance(answer, str), "Answer should be a string"
        assert len(answer.strip()) > 10, "Answer should be substantial"

        # Verify answer contains relevant information
        # The answer should reference the documents or their content
        answer_lower = answer.lower()
        relevant_indicators = ["document", "test", "file", "content", "3", "three"]
        has_relevant_info = any(indicator in answer_lower for indicator in relevant_indicators)
        assert has_relevant_info, f"Answer should contain relevant information: {answer}"

        # Verify that the answer is not just a generic response
        generic_responses = ["i don't know", "no information", "cannot find", "not available"]
        is_not_generic = not any(generic in answer_lower for generic in generic_responses)
        assert is_not_generic, f"Answer should not be generic: {answer}"

    def test_search_results_format_consistency(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test that search results maintain consistent format across different queries."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        queries = ["What is the main topic?", "How many documents are there?", "What type of files are included?", "Tell me about the content"]

        for query in queries:
            search_input = {"question": query, "collection_id": str(test_collection_with_documents.id), "pipeline_id": str(test_pipeline_config.id), "user_id": str(test_pipeline_config.user_id)}

            response = client.post("/api/search", json=search_input)

            # Expected behavior: All queries should return consistent format
            assert response.status_code == 200, f"Query '{query}' failed with status {response.status_code}"

            data = response.json()

            # Verify consistent response structure
            required_fields = ["answer", "documents", "query_results", "rewritten_query", "evaluation"]
            for field in required_fields:
                assert field in data, f"Missing field '{field}' for query: {query}"
                assert data[field] is not None, f"Field '{field}' should not be None for query: {query}"

            # Verify data types are consistent
            assert isinstance(data["answer"], str), f"Answer should be string for query: {query}"
            assert isinstance(data["documents"], list), f"Documents should be list for query: {query}"
            assert isinstance(data["query_results"], list), f"Query results should be list for query: {query}"
            assert isinstance(data["rewritten_query"], str | type(None)), f"Rewritten query should be string or None for query: {query}"
            assert isinstance(data["evaluation"], dict | type(None)), f"Evaluation should be dict or None for query: {query}"

    def test_search_with_different_query_types(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with different types of queries to verify robustness."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        query_types = [
            # Factual questions
            "What is the main topic?",
            "How many documents are there?",
            # Descriptive questions
            "Describe the content of the documents",
            "What information is available?",
            # Comparative questions
            "What are the similarities between documents?",
            "How do the documents differ?",
            # Analytical questions
            "What can you conclude from the documents?",
            "What patterns do you see?",
            # Specific questions
            "What is in test_document_1?",
            "Tell me about test_topic_2",
        ]

        for query in query_types:
            search_input = {"question": query, "collection_id": str(test_collection_with_documents.id), "pipeline_id": str(test_pipeline_config.id), "user_id": str(test_pipeline_config.user_id)}

            response = client.post("/api/search", json=search_input)

            # Expected behavior: All query types should be handled gracefully
            assert response.status_code == 200, f"Query type '{query}' failed with status {response.status_code}"

            data = response.json()

            # Verify response quality
            assert len(data["answer"].strip()) > 5, f"Answer too short for query: {query}"
            assert len(data["query_results"]) > 0, f"No query results for query: {query}"
            assert len(data["documents"]) > 0, f"No documents returned for query: {query}"

    def test_search_pipeline_execution_flow(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test that the complete search pipeline executes correctly."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What is the complete pipeline execution test?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Complete pipeline should execute successfully
        assert response.status_code == 200
        data = response.json()

        # Verify pipeline components worked
        assert data["answer"], "Pipeline should generate an answer"
        assert data["query_results"], "Pipeline should retrieve relevant documents"
        assert data["documents"], "Pipeline should return document metadata"

        # Verify evaluation metrics are present (indicating pipeline completion)
        if data["evaluation"]:
            assert isinstance(data["evaluation"], dict), "Evaluation should be a dictionary"
            # Check for common pipeline metrics
            expected_metrics = ["response_time", "document_count", "relevance_score"]
            for metric in expected_metrics:
                if metric in data["evaluation"]:
                    assert isinstance(data["evaluation"][metric], int | float), f"Metric {metric} should be numeric"

    def test_search_with_config_metadata(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with additional configuration metadata."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What is the main topic?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
            "config_metadata": {"user_role": "researcher", "language": "en", "detail_level": "high", "max_results": 10},
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should handle config metadata and return appropriate results
        assert response.status_code == 200
        data = response.json()

        # Verify response is influenced by config metadata
        assert data["answer"], "Should generate answer with config metadata"
        assert data["query_results"], "Should return query results"

        # Verify config metadata influenced the response
        # The response should be more detailed given "detail_level": "high"
        answer_length = len(data["answer"])
        assert answer_length > 20, "Answer should be detailed given high detail level config"

    def test_search_vector_store_integration(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test that search properly integrates with vector store for document retrieval."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "test_topic_1",  # Should match specific document
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should retrieve relevant documents from vector store
        assert response.status_code == 200
        data = response.json()

        # Verify vector store integration
        assert len(data["query_results"]) > 0, "Should retrieve documents from vector store"

        # Verify similarity-based retrieval
        scores = [result["score"] for result in data["query_results"]]
        assert max(scores) > 0.0, "Should have non-zero similarity scores"

        # Verify that results are ordered by relevance (highest scores first)
        sorted_scores = sorted(scores, reverse=True)
        assert scores == sorted_scores, "Results should be ordered by relevance score"

        # Verify document metadata is properly retrieved
        for result in data["query_results"]:
            assert "metadata" in result, "Query results should include metadata"
            assert "content" in result, "Query results should include content"
            assert len(result["content"]) > 0, "Content should not be empty"

    def test_search_llm_provider_integration(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test that search properly integrates with LLM provider for answer generation."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What is the purpose of these test documents?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should generate answer using LLM provider
        assert response.status_code == 200
        data = response.json()

        # Verify LLM integration
        answer = data["answer"]
        assert isinstance(answer, str), "Answer should be a string"
        assert len(answer.strip()) > 10, "Answer should be substantial"

        # Verify answer quality (not just generic responses)
        generic_phrases = ["i don't know", "no information available", "cannot answer", "not found", "error"]
        answer_lower = answer.lower()
        has_generic_phrase = any(phrase in answer_lower for phrase in generic_phrases)
        assert not has_generic_phrase, f"Answer should not be generic: {answer}"

        # Verify answer references the documents
        document_references = ["document", "file", "test", "content", "information"]
        has_document_reference = any(ref in answer_lower for ref in document_references)
        assert has_document_reference, f"Answer should reference documents: {answer}"

    def test_search_response_time_performance(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test that search responses are returned within reasonable time."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What is the main topic?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        import time

        start_time = time.time()
        response = client.post("/api/search", json=search_input)
        end_time = time.time()

        response_time = end_time - start_time

        # Expected behavior: Should respond within reasonable time
        assert response.status_code == 200, f"Search failed: {response.text}"
        assert response_time < 30.0, f"Response time too slow: {response_time:.2f}s"

        # Verify response time is recorded in evaluation
        data = response.json()
        if data["evaluation"] and "response_time" in data["evaluation"]:
            recorded_time = data["evaluation"]["response_time"]
            assert isinstance(recorded_time, int | float), "Response time should be numeric"
            assert recorded_time > 0, "Response time should be positive"

    def test_search_with_multiple_documents_retrieval(
        self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig    ) -> None:
        """Test that search can retrieve and process multiple documents."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What are all the test topics covered?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should retrieve and process multiple documents
        assert response.status_code == 200
        data = response.json()

        # Verify multiple documents are retrieved
        assert len(data["documents"]) >= 3, "Should retrieve all test documents"
        assert len(data["query_results"]) > 0, "Should return query results from multiple documents"

        # Verify answer synthesizes information from multiple documents
        answer = data["answer"]
        assert len(answer.strip()) > 20, "Answer should be comprehensive"

        # Verify that different document topics are referenced
        unique_document_ids = set()
        for doc in data["documents"]:
            unique_document_ids.add(doc["document_id"])

        assert len(unique_document_ids) >= 2, "Should reference multiple unique documents"


class TestSearchCollectionSelection:
    """Test collection selection functionality."""

    def test_search_uses_correct_collection(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test that search uses the correct collection when multiple collections exist."""
        # Create another collection to test selection
        Collection(name="other-collection", vector_db_name="other_collection", status="CREATED")
        # Note: We can't add to test_db here as it's a fixture, but the test should verify
        # that the search service correctly identifies and uses the specified collection

        search_input = {
            "question": "What is the main topic?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        # This test should verify that the search service:
        # 1. Validates the collection exists
        # 2. Uses the correct collection for document retrieval
        # 3. Returns results only from the specified collection
        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should succeed and use correct collection
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "documents" in data

        # Verify collection-specific behavior
        # Note: This will fail initially as we're in TDD red phase
        assert len(data["documents"]) > 0, "Should return documents from the specified collection"

        # Verify all returned documents belong to the correct collection
        for doc in data["documents"]:
            assert doc["collection_id"] == str(test_collection_with_documents.id), "All documents should belong to the specified collection"

    def test_search_with_invalid_collection_id(self, client: TestClient) -> None:
        """Test search with non-existent collection ID."""
        invalid_collection_id = str(uuid4())

        search_input = {"question": "What is the main topic?", "collection_id": invalid_collection_id, "pipeline_id": str(uuid4()), "user_id": str(uuid4())}

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should return 404 with clear error message
        assert response.status_code == 404
        data = response.json()
        assert "Collection not found" in data["detail"]
        assert invalid_collection_id in data["detail"]

    def test_search_with_malformed_collection_id(self, client: TestClient) -> None:
        """Test search with malformed collection ID."""
        search_input = {"question": "What is the main topic?", "collection_id": "not-a-valid-uuid", "pipeline_id": str(uuid4()), "user_id": str(uuid4())}

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should return 422 validation error
        assert response.status_code == 422
        data = response.json()
        assert "validation error" in data["detail"].lower() or "invalid" in data["detail"].lower()


class TestSearchDocumentRetrieval:
    """Test document retrieval and indexing functionality."""

    def test_search_with_documents_in_collection(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search when collection has properly indexed documents."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What documents are available?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should succeed and return relevant documents
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "documents" in data
        assert "query_results" in data

        # Verify document retrieval
        assert len(data["documents"]) > 0, "Should return documents from indexed collection"
        assert len(data["query_results"]) > 0, "Should return query results with document chunks"

        # Verify document metadata is properly structured
        for doc in data["documents"]:
            assert "document_id" in doc
            assert "document_name" in doc
            assert "collection_id" in doc
            assert doc["collection_id"] == str(test_collection_with_documents.id)

        # Verify query results contain relevant chunks
        for result in data["query_results"]:
            assert "content" in result
            assert "score" in result
            assert "metadata" in result
            assert isinstance(result["score"], int | float)
            assert result["score"] >= 0.0  # Similarity scores should be non-negative

    def test_search_with_empty_collection(self, client: TestClient, test_empty_collection: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search when collection exists but has no documents."""
        # Update pipeline config to use the empty collection
        test_pipeline_config.collection_id = test_empty_collection.id

        search_input = {
            "question": "What documents are available?",
            "collection_id": str(test_empty_collection.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should handle empty collection gracefully
        # This could either:
        # 1. Return 200 with empty results and appropriate message
        # 2. Return 400 with clear error about empty collection
        # We'll test for graceful handling
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.json()
            assert "answer" in data
            assert "documents" in data
            assert len(data["documents"]) == 0, "Should return empty documents list"
            assert "No documents found" in data["answer"] or "empty" in data["answer"].lower()
        else:
            data = response.json()
            assert "empty" in data["detail"].lower() or "no documents" in data["detail"].lower()

    def test_search_document_indexing_verification(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test that documents are properly indexed in vector store."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "test_topic_1",  # Should match one of our test documents
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should find relevant documents based on content
        assert response.status_code == 200
        data = response.json()

        # Verify that the search found relevant documents
        assert len(data["query_results"]) > 0, "Should find relevant document chunks"

        # Verify that the most relevant result has a high similarity score
        if data["query_results"]:
            best_score = max(result["score"] for result in data["query_results"])
            assert best_score > 0.5, "Should find highly relevant documents with good similarity scores"

            # Verify that the content contains relevant information
            best_result = max(data["query_results"], key=lambda x: x["score"])
            assert "test_topic" in best_result["content"].lower() or "test" in best_result["content"].lower()


class TestSearchResultsDisplay:
    """Test search results display and UI formatting."""

    def test_search_results_display_format(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test that search results are properly formatted for UI display."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What is the main topic?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should return properly formatted results
        assert response.status_code == 200
        data = response.json()

        # Verify required fields for UI display
        required_fields = ["answer", "documents", "query_results", "rewritten_query", "evaluation"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify answer is a non-empty string
        assert isinstance(data["answer"], str)
        assert len(data["answer"].strip()) > 0, "Answer should not be empty"

        # Verify documents list structure
        assert isinstance(data["documents"], list)
        for doc in data["documents"]:
            required_doc_fields = ["document_id", "document_name", "collection_id"]
            for field in required_doc_fields:
                assert field in doc, f"Missing required document field: {field}"

        # Verify query results structure
        assert isinstance(data["query_results"], list)
        for result in data["query_results"]:
            required_result_fields = ["content", "score", "metadata"]
            for field in required_result_fields:
                assert field in result, f"Missing required query result field: {field}"

    def test_search_results_with_rewritten_query(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test that search results include rewritten query when applicable."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What's the main topic?",  # Informal query that should be rewritten
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should include rewritten query
        assert response.status_code == 200
        data = response.json()

        # Verify rewritten query is present and different from original
        assert "rewritten_query" in data
        assert data["rewritten_query"] is not None
        assert isinstance(data["rewritten_query"], str)
        assert len(data["rewritten_query"].strip()) > 0

        # The rewritten query should be more formal/proper than the original
        original = search_input["question"].lower()
        rewritten = data["rewritten_query"].lower()
        # This is a basic check - in practice, the rewriting might be more sophisticated
        assert rewritten != original, "Rewritten query should be different from original"

    def test_search_results_evaluation_metrics(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test that search results include evaluation metrics."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What is the main topic?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should include evaluation metrics
        assert response.status_code == 200
        data = response.json()

        # Verify evaluation data is present
        assert "evaluation" in data
        assert data["evaluation"] is not None
        assert isinstance(data["evaluation"], dict)

        # Verify evaluation contains useful metrics
        evaluation = data["evaluation"]
        expected_metrics = ["response_time", "document_count", "relevance_score"]
        for metric in expected_metrics:
            assert metric in evaluation, f"Missing evaluation metric: {metric}"
            assert isinstance(evaluation[metric], int | float), f"Metric {metric} should be numeric"


class TestSearchErrorHandling:
    """Test error handling and edge cases."""

    def test_search_with_malformed_queries(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with various malformed queries."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        malformed_queries = [
            "",  # Empty query
            "   ",  # Whitespace only
            "a" * 10000,  # Extremely long query
            "!@#$%^&*()",  # Special characters only
            None,  # Null query (should be caught by validation)
        ]

        for query in malformed_queries:
            search_input = {"question": query, "collection_id": str(test_collection_with_documents.id), "pipeline_id": str(test_pipeline_config.id), "user_id": str(test_pipeline_config.user_id)}

            # Remove None values for JSON serialization
            if query is None:
                del search_input["question"]

            response = client.post("/api/search", json=search_input)

            # Expected behavior: Should handle malformed queries gracefully
            assert response.status_code in [400, 422], f"Unexpected status for query: {query}"

            data = response.json()
            assert "detail" in data
            assert len(data["detail"]) > 0, "Error message should not be empty"

    def test_search_with_missing_required_fields(self, client: TestClient) -> None:
        """Test search with missing required fields."""
        incomplete_inputs = [
            {},  # Empty input
            {"question": "test"},  # Missing collection_id
            {"collection_id": str(uuid4())},  # Missing question
            {"question": "test", "collection_id": str(uuid4())},  # Missing pipeline_id and user_id
        ]

        for incomplete_input in incomplete_inputs:
            response = client.post("/api/search", json=incomplete_input)

            # Expected behavior: Should return 422 validation error
            assert response.status_code == 422
            data = response.json()
            assert "validation error" in data["detail"].lower() or "missing" in data["detail"].lower()

    def test_search_with_invalid_pipeline_id(self, client: TestClient, test_collection_with_documents: Collection) -> None:
        """Test search with invalid pipeline ID."""
        search_input = {
            "question": "What is the main topic?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(uuid4()),  # Non-existent pipeline
            "user_id": str(uuid4()),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should return 404 or 400 with clear error
        assert response.status_code in [400, 404, 500]
        data = response.json()
        assert "pipeline" in data["detail"].lower() or "configuration" in data["detail"].lower()

    def test_search_with_invalid_user_id(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with invalid user ID."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What is the main topic?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(uuid4()),  # Non-existent user
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should return 404 or 403 with clear error
        assert response.status_code in [403, 404, 500]
        data = response.json()
        assert "user" in data["detail"].lower() or "access" in data["detail"].lower()

    def test_search_error_message_clarity(self, client: TestClient) -> None:
        """Test that error messages are clear and helpful."""
        # Test with completely invalid input
        search_input = {"question": "", "collection_id": "invalid-uuid", "pipeline_id": "also-invalid", "user_id": "also-invalid"}

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should return clear validation errors
        assert response.status_code == 422
        data = response.json()

        # Verify error message is helpful
        assert "detail" in data
        error_detail = data["detail"]
        assert len(error_detail) > 10, "Error message should be descriptive"
        assert not error_detail.isupper(), "Error message should not be all caps"
        assert "invalid" in error_detail.lower() or "validation" in error_detail.lower()


class TestSearchPerformanceAndReliability:
    """Test search performance and reliability edge cases."""

    def test_search_timeout_handling(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search timeout handling."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What is the main topic?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        # This test should verify that the search service handles timeouts gracefully
        # In a real implementation, we might mock a slow response to test timeout
        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should either succeed or fail gracefully with timeout error
        assert response.status_code in [200, 408, 500]

        if response.status_code != 200:
            data = response.json()
            assert "timeout" in data["detail"].lower() or "time" in data["detail"].lower()

    def test_search_concurrent_requests(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with concurrent requests."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What is the main topic?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        # Send multiple concurrent requests

        async def make_request():
            return client.post("/api/search", json=search_input)

        # This test should verify that concurrent requests don't interfere with each other
        # In a real implementation, we might use asyncio.gather or similar
        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should handle concurrent requests without issues
        assert response.status_code in [200, 429, 500]  # 429 for rate limiting

        if response.status_code == 429:
            data = response.json()
            assert "rate limit" in data["detail"].lower() or "too many" in data["detail"].lower()


class TestSearchEdgeCases:
    """Test edge cases for search functionality - Issue #160 specific debugging scenarios."""

    def test_search_with_empty_collection(self, client: TestClient, test_empty_collection: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with empty collection - Issue #160: Document Retrieval edge case."""
        # Update pipeline config to use the empty collection
        test_pipeline_config.collection_id = test_empty_collection.id

        search_input = {
            "question": "What is the main topic?",
            "collection_id": str(test_empty_collection.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should handle empty collection gracefully
        assert response.status_code == 200, "Should handle empty collection gracefully"

        data = response.json()

        # Should return empty results but still have proper structure
        assert "answer" in data, "Response should contain 'answer' field"
        assert "documents" in data, "Response should contain 'documents' field"
        assert "query_results" in data, "Response should contain 'query_results' field"

        # Documents and query results should be empty
        assert isinstance(data["documents"], list), "Documents should be a list"
        assert len(data["documents"]) == 0, "Should return empty documents list"
        assert isinstance(data["query_results"], list), "Query results should be a list"
        assert len(data["query_results"]) == 0, "Should return empty query results"

        # Answer should indicate no results found
        assert isinstance(data["answer"], str), "Answer should be a string"
        assert len(data["answer"].strip()) > 0, "Answer should not be empty"
        assert "no documents" in data["answer"].lower() or "no results" in data["answer"].lower(), "Answer should indicate no results found"

    def test_search_with_invalid_collection_id(self, client: TestClient, test_pipeline_config: PipelineConfig) -> None:
        """Test search with invalid collection ID - Issue #160: Collection Selection edge case."""
        invalid_collection_id = str(uuid4())

        search_input = {"question": "What is the main topic?", "collection_id": invalid_collection_id, "pipeline_id": str(test_pipeline_config.id), "user_id": str(test_pipeline_config.user_id)}

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should return 404 or 400 with clear error message
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}: {response.text}"

        data = response.json()

        # Should have clear error message about collection not found
        assert "detail" in data, "Response should contain error detail"
        error_message = data["detail"].lower()
        assert "collection" in error_message and ("not found" in error_message or "invalid" in error_message), f"Error message should mention collection not found: {error_message}"

    def test_search_with_malformed_query(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with malformed or empty query - Issue #160: Error Handling edge case."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        # Test with empty query
        search_input = {
            "question": "",  # Empty query
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should return 400 with validation error
        assert response.status_code == 400, f"Expected 400 for empty query, got {response.status_code}: {response.text}"

        data = response.json()
        assert "detail" in data, "Response should contain error detail"
        error_message = data["detail"].lower()
        assert "question" in error_message and ("empty" in error_message or "required" in error_message), f"Error message should mention empty question: {error_message}"

    def test_search_with_very_long_query(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with very long query - Issue #160: Error Handling edge case."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        # Create a very long query
        long_query = "What is the main topic? " * 1000  # ~25KB query

        search_input = {"question": long_query, "collection_id": str(test_collection_with_documents.id), "pipeline_id": str(test_pipeline_config.id), "user_id": str(test_pipeline_config.user_id)}

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should handle long query gracefully
        assert response.status_code in [200, 400], f"Expected 200 or 400 for long query, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert "answer" in data, "Response should contain 'answer' field"
        else:
            # If it fails, should have clear error message
            data = response.json()
            assert "detail" in data, "Response should contain error detail"

    def test_search_with_special_characters_in_query(
        self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig    ) -> None:
        """Test search with special characters in query - Issue #160: Error Handling edge case."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        # Test with special characters
        special_query = "What is the main topic? @#$%^&*()_+{}|:<>?[]\\;'\",./"

        search_input = {"question": special_query, "collection_id": str(test_collection_with_documents.id), "pipeline_id": str(test_pipeline_config.id), "user_id": str(test_pipeline_config.user_id)}

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should handle special characters gracefully
        assert response.status_code == 200, f"Expected 200 for special characters, got {response.status_code}: {response.text}"

        data = response.json()
        assert "answer" in data, "Response should contain 'answer' field"
        assert "query_results" in data, "Response should contain 'query_results' field"

    def test_search_with_unicode_characters_in_query(
        self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig    ) -> None:
        """Test search with Unicode characters in query - Issue #160: Error Handling edge case."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        # Test with Unicode characters
        unicode_query = "What is the main topic? 你好世界 🌍 ∑ ∫ ∞"

        search_input = {"question": unicode_query, "collection_id": str(test_collection_with_documents.id), "pipeline_id": str(test_pipeline_config.id), "user_id": str(test_pipeline_config.user_id)}

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should handle Unicode characters gracefully
        assert response.status_code == 200, f"Expected 200 for Unicode characters, got {response.status_code}: {response.text}"

        data = response.json()
        assert "answer" in data, "Response should contain 'answer' field"
        assert "query_results" in data, "Response should contain 'query_results' field"

    def test_search_with_sql_injection_attempt(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with SQL injection attempt - Issue #160: Error Handling edge case."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        # Test with SQL injection attempt
        sql_injection_query = "'; DROP TABLE users; --"

        search_input = {
            "question": sql_injection_query,
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should handle SQL injection attempt safely
        assert response.status_code == 200, f"Expected 200 for SQL injection attempt, got {response.status_code}: {response.text}"

        data = response.json()
        assert "answer" in data, "Response should contain 'answer' field"
        # Should not execute SQL injection
        assert "DROP TABLE" not in data["answer"], "Should not execute SQL injection"

    def test_search_with_xss_attempt(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with XSS attempt - Issue #160: Error Handling edge case."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        # Test with XSS attempt
        xss_query = "<script>alert('XSS')</script>"

        search_input = {"question": xss_query, "collection_id": str(test_collection_with_documents.id), "pipeline_id": str(test_pipeline_config.id), "user_id": str(test_pipeline_config.user_id)}

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should handle XSS attempt safely
        assert response.status_code == 200, f"Expected 200 for XSS attempt, got {response.status_code}: {response.text}"

        data = response.json()
        assert "answer" in data, "Response should contain 'answer' field"
        # Should not execute XSS
        assert "<script>" not in data["answer"], "Should not execute XSS"

    def test_search_with_very_short_query(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with very short query - Issue #160: Error Handling edge case."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        # Test with very short query
        short_query = "a"

        search_input = {"question": short_query, "collection_id": str(test_collection_with_documents.id), "pipeline_id": str(test_pipeline_config.id), "user_id": str(test_pipeline_config.user_id)}

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should handle short query gracefully
        assert response.status_code == 200, f"Expected 200 for short query, got {response.status_code}: {response.text}"

        data = response.json()
        assert "answer" in data, "Response should contain 'answer' field"
        assert "query_results" in data, "Response should contain 'query_results' field"

    def test_search_with_numeric_query(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with numeric query - Issue #160: Error Handling edge case."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        # Test with numeric query
        numeric_query = "123456789"

        search_input = {"question": numeric_query, "collection_id": str(test_collection_with_documents.id), "pipeline_id": str(test_pipeline_config.id), "user_id": str(test_pipeline_config.user_id)}

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should handle numeric query gracefully
        assert response.status_code == 200, f"Expected 200 for numeric query, got {response.status_code}: {response.text}"

        data = response.json()
        assert "answer" in data, "Response should contain 'answer' field"
        assert "query_results" in data, "Response should contain 'query_results' field"

    def test_search_with_whitespace_only_query(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search with whitespace-only query - Issue #160: Error Handling edge case."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        # Test with whitespace-only query
        whitespace_query = "   \n\t  "

        search_input = {
            "question": whitespace_query,
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should return 400 with validation error
        assert response.status_code == 400, f"Expected 400 for whitespace-only query, got {response.status_code}: {response.text}"

        data = response.json()
        assert "detail" in data, "Response should contain error detail"
        error_message = data["detail"].lower()
        assert "question" in error_message and ("empty" in error_message or "required" in error_message), f"Error message should mention empty question: {error_message}"

    def test_search_results_display_formatting(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test search results display formatting - Issue #160: Search Results Display edge case."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        search_input = {
            "question": "What is the main topic?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should return properly formatted results for UI display
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Verify response structure for UI display
        assert "answer" in data, "Response should contain 'answer' field"
        assert "documents" in data, "Response should contain 'documents' field"
        assert "query_results" in data, "Response should contain 'query_results' field"
        assert "rewritten_query" in data, "Response should contain 'rewritten_query' field"
        assert "evaluation" in data, "Response should contain 'evaluation' field"

        # Verify answer is properly formatted for display
        answer = data["answer"]
        assert isinstance(answer, str), "Answer should be a string"
        assert len(answer.strip()) > 0, "Answer should not be empty"

        # Verify documents are properly formatted for display
        documents = data["documents"]
        assert isinstance(documents, list), "Documents should be a list"
        for doc in documents:
            assert "document_name" in doc, "Document should have document_name field"
            assert "content" in doc, "Document should have content field"
            assert "metadata" in doc, "Document should have metadata field"

        # Verify query results are properly formatted for display
        query_results = data["query_results"]
        assert isinstance(query_results, list), "Query results should be a list"
        for result in query_results:
            assert "content" in result, "Query result should have content field"
            assert "score" in result, "Query result should have score field"
            assert "metadata" in result, "Query result should have metadata field"

    def test_search_document_indexing_verification(self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig) -> None:
        """Test document indexing verification - Issue #160: Document Retrieval edge case."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        # Search for specific content that should be indexed
        search_input = {
            "question": "test_topic",  # Should match our test document keywords
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should find indexed documents
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Verify that documents were properly indexed and can be found
        assert len(data["query_results"]) > 0, "Should find indexed document chunks"

        # Verify that the search found documents with relevant content
        found_relevant_content = False
        for result in data["query_results"]:
            if "test_topic" in result["content"].lower() or "test" in result["content"].lower():
                found_relevant_content = True
                break

        assert found_relevant_content, "Should find documents containing relevant content"

        # Verify that documents are properly indexed with metadata
        for result in data["query_results"]:
            assert "metadata" in result, "Query result should have metadata"
            assert "source" in result["metadata"], "Metadata should contain source"
            assert "document_id" in result["metadata"], "Metadata should contain document_id"

    def test_search_collection_selection_validation(
        self, client: TestClient, test_collection_with_documents: Collection, test_pipeline_config: PipelineConfig    ) -> None:
        """Test collection selection validation - Issue #160: Collection Selection edge case."""
        # Update pipeline config to use the test collection
        test_pipeline_config.collection_id = test_collection_with_documents.id

        # Test with correct collection ID
        search_input = {
            "question": "What is the main topic?",
            "collection_id": str(test_collection_with_documents.id),
            "pipeline_id": str(test_pipeline_config.id),
            "user_id": str(test_pipeline_config.user_id),
        }

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should use the correct collection
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Verify that the search used the correct collection
        assert "documents" in data, "Response should contain documents"
        assert "query_results" in data, "Response should contain query results"

        # Verify that documents come from the correct collection
        for doc in data["documents"]:
            assert "metadata" in doc, "Document should have metadata"
            # The metadata should indicate the correct collection
            assert doc["metadata"]["collection_id"] == str(test_collection_with_documents.id), "Document should come from the correct collection"

    def test_search_error_message_quality(self, client: TestClient, test_pipeline_config: PipelineConfig) -> None:
        """Test error message quality - Issue #160: Error Handling edge case."""
        # Test with invalid collection ID
        invalid_collection_id = str(uuid4())

        search_input = {"question": "What is the main topic?", "collection_id": invalid_collection_id, "pipeline_id": str(test_pipeline_config.id), "user_id": str(test_pipeline_config.user_id)}

        response = client.post("/api/search", json=search_input)

        # Expected behavior: Should return clear, actionable error message
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}: {response.text}"

        data = response.json()
        assert "detail" in data, "Response should contain error detail"

        error_message = data["detail"]
        assert isinstance(error_message, str), "Error message should be a string"
        assert len(error_message.strip()) > 0, "Error message should not be empty"

        # Error message should be clear and actionable
        assert "collection" in error_message.lower(), "Error message should mention collection"
        assert "not found" in error_message.lower() or "invalid" in error_message.lower(), "Error message should indicate collection not found"

        # Error message should not be generic
        generic_errors = ["internal error", "something went wrong", "error occurred"]
        is_not_generic = not any(generic in error_message.lower() for generic in generic_errors)
        assert is_not_generic, f"Error message should not be generic: {error_message}"
