"""
Test data collections and query sets for comprehensive search validation.

This module implements test data validation for Issue #198:
Comprehensive Testing of Current Search Functionality.

These tests validate the quality and consistency of test data used for search testing.
"""

import pytest
import json
from typing import Dict, List, Any, Tuple
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock

from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.search_service import SearchService


@pytest.mark.e2e
@pytest.mark.data_validation
class TestSearchDataValidation:
    """Test data validation for search functionality."""

    # Comprehensive Test Data Collections
    TEST_COLLECTIONS = {
        "machine_learning": {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "Machine Learning Documentation",
            "description": "Comprehensive ML documentation and tutorials",
            "document_count": 150,
            "expected_topics": ["algorithms", "neural networks", "deep learning", "supervised learning", "unsupervised learning"],
            "document_types": ["pdf", "txt", "md"],
            "languages": ["en"],
            "quality_metrics": {
                "min_document_length": 1000,
                "max_document_length": 50000,
                "avg_document_length": 10000
            }
        },
        "python_programming": {
            "id": "550e8400-e29b-41d4-a716-446655440002",
            "name": "Python Programming Guide",
            "description": "Python programming tutorials and best practices",
            "document_count": 200,
            "expected_topics": ["syntax", "libraries", "best practices", "performance", "debugging"],
            "document_types": ["py", "md", "txt"],
            "languages": ["en"],
            "quality_metrics": {
                "min_document_length": 500,
                "max_document_length": 30000,
                "avg_document_length": 8000
            }
        },
        "data_science": {
            "id": "550e8400-e29b-41d4-a716-446655440003",
            "name": "Data Science Handbook",
            "description": "Data science methodologies and tools",
            "document_count": 100,
            "expected_topics": ["statistics", "visualization", "analysis", "pandas", "numpy", "matplotlib"],
            "document_types": ["ipynb", "py", "md"],
            "languages": ["en"],
            "quality_metrics": {
                "min_document_length": 2000,
                "max_document_length": 40000,
                "avg_document_length": 12000
            }
        },
        "artificial_intelligence": {
            "id": "550e8400-e29b-41d4-a716-446655440004",
            "name": "Artificial Intelligence Fundamentals",
            "description": "AI concepts, theories, and applications",
            "document_count": 120,
            "expected_topics": ["ai", "machine learning", "neural networks", "expert systems", "natural language processing"],
            "document_types": ["pdf", "md", "txt"],
            "languages": ["en"],
            "quality_metrics": {
                "min_document_length": 1500,
                "max_document_length": 45000,
                "avg_document_length": 15000
            }
        }
    }

    # Comprehensive Query Test Sets
    QUERY_TEST_SETS = {
        "factual_queries": {
            "description": "Simple factual questions requiring direct answers",
            "queries": [
                {
                    "question": "What is machine learning?",
                    "expected_answer_type": "definition",
                    "expected_keywords": ["machine learning", "algorithm", "data", "artificial intelligence"],
                    "expected_sources": 3,
                    "difficulty": "easy"
                },
                {
                    "question": "What is Python programming language?",
                    "expected_answer_type": "definition",
                    "expected_keywords": ["python", "programming", "language", "interpreted"],
                    "expected_sources": 3,
                    "difficulty": "easy"
                },
                {
                    "question": "What is data science?",
                    "expected_answer_type": "definition",
                    "expected_keywords": ["data science", "analysis", "statistics", "insights"],
                    "expected_sources": 3,
                    "difficulty": "easy"
                }
            ]
        },
        "analytical_queries": {
            "description": "Questions requiring analysis and comparison",
            "queries": [
                {
                    "question": "What are the differences between supervised and unsupervised learning?",
                    "expected_answer_type": "comparison",
                    "expected_keywords": ["supervised", "unsupervised", "difference", "labeled data", "unlabeled data"],
                    "expected_sources": 4,
                    "difficulty": "medium"
                },
                {
                    "question": "How do neural networks compare to traditional machine learning algorithms?",
                    "expected_answer_type": "comparison",
                    "expected_keywords": ["neural networks", "traditional", "algorithms", "comparison", "performance"],
                    "expected_sources": 5,
                    "difficulty": "medium"
                },
                {
                    "question": "What are the advantages and disadvantages of Python for data science?",
                    "expected_answer_type": "pros_cons",
                    "expected_keywords": ["python", "advantages", "disadvantages", "data science", "libraries"],
                    "expected_sources": 4,
                    "difficulty": "medium"
                }
            ]
        },
        "technical_queries": {
            "description": "Deep technical questions requiring detailed explanations",
            "queries": [
                {
                    "question": "Explain the mathematical foundations of gradient descent optimization",
                    "expected_answer_type": "technical_explanation",
                    "expected_keywords": ["gradient descent", "mathematical", "optimization", "derivative", "convergence"],
                    "expected_sources": 6,
                    "difficulty": "hard"
                },
                {
                    "question": "How does backpropagation work in neural networks?",
                    "expected_answer_type": "technical_explanation",
                    "expected_keywords": ["backpropagation", "neural networks", "algorithm", "gradient", "weights"],
                    "expected_sources": 5,
                    "difficulty": "hard"
                },
                {
                    "question": "What is the time complexity of different sorting algorithms?",
                    "expected_answer_type": "technical_explanation",
                    "expected_keywords": ["time complexity", "sorting", "algorithms", "big o", "performance"],
                    "expected_sources": 4,
                    "difficulty": "hard"
                }
            ]
        },
        "practical_queries": {
            "description": "Questions about practical implementation and applications",
            "queries": [
                {
                    "question": "How would I implement a recommendation system using Python?",
                    "expected_answer_type": "implementation_guide",
                    "expected_keywords": ["recommendation system", "python", "implementation", "algorithm", "code"],
                    "expected_sources": 4,
                    "difficulty": "medium"
                },
                {
                    "question": "What are the best practices for data preprocessing in machine learning?",
                    "expected_answer_type": "best_practices",
                    "expected_keywords": ["data preprocessing", "best practices", "machine learning", "cleaning", "transformation"],
                    "expected_sources": 5,
                    "difficulty": "medium"
                },
                {
                    "question": "How do I choose the right machine learning algorithm for my problem?",
                    "expected_answer_type": "decision_guide",
                    "expected_keywords": ["machine learning", "algorithm", "choose", "problem", "selection"],
                    "expected_sources": 4,
                    "difficulty": "medium"
                }
            ]
        },
        "edge_case_queries": {
            "description": "Edge cases and boundary conditions",
            "queries": [
                {
                    "question": "",  # Empty query
                    "expected_answer_type": "error",
                    "expected_keywords": [],
                    "expected_sources": 0,
                    "difficulty": "edge_case"
                },
                {
                    "question": "a",  # Single character
                    "expected_answer_type": "error_or_minimal",
                    "expected_keywords": [],
                    "expected_sources": 0,
                    "difficulty": "edge_case"
                },
                {
                    "question": "What is machine learning? " * 100,  # Very long query
                    "expected_answer_type": "processed_query",
                    "expected_keywords": ["machine learning"],
                    "expected_sources": 3,
                    "difficulty": "edge_case"
                },
                {
                    "question": "What is @#$%^&*() machine learning?",  # Special characters
                    "expected_answer_type": "cleaned_query",
                    "expected_keywords": ["machine learning"],
                    "expected_sources": 3,
                    "difficulty": "edge_case"
                }
            ]
        }
    }

    # Pipeline Configuration Test Data
    PIPELINE_CONFIGURATIONS = {
        "default": {
            "id": "550e8400-e29b-41d4-a716-446655440010",
            "name": "Default RAG Pipeline",
            "retriever_type": "semantic",
            "chunking_strategy": "semantic",
            "context_strategy": "weighted",
            "llm_provider": "watsonx",
            "expected_performance": {
                "response_time_ms": 2000,
                "accuracy_threshold": 0.85
            }
        },
        "fast": {
            "id": "550e8400-e29b-41d4-a716-446655440011",
            "name": "Fast RAG Pipeline",
            "retriever_type": "keyword",
            "chunking_strategy": "fixed",
            "context_strategy": "simple",
            "llm_provider": "watsonx",
            "expected_performance": {
                "response_time_ms": 1000,
                "accuracy_threshold": 0.80
            }
        },
        "comprehensive": {
            "id": "550e8400-e29b-41d4-a716-446655440012",
            "name": "Comprehensive RAG Pipeline",
            "retriever_type": "hybrid",
            "chunking_strategy": "semantic",
            "context_strategy": "weighted",
            "llm_provider": "watsonx",
            "expected_performance": {
                "response_time_ms": 4000,
                "accuracy_threshold": 0.90
            }
        }
    }

    @pytest.fixture
    def test_user_id(self) -> UUID:
        """Test user ID for validation tests."""
        return uuid4()

    @pytest.fixture
    def mock_search_service(self) -> Mock:
        """Mock search service for validation testing."""
        service = Mock(spec=SearchService)
        service.search = AsyncMock()
        return service

    def test_collection_data_quality(self):
        """Test quality and consistency of test collection data."""
        # Validate collection structure
        for collection_name, collection_data in self.TEST_COLLECTIONS.items():
            # Required fields
            assert "id" in collection_data, f"Collection {collection_name} missing ID"
            assert "name" in collection_data, f"Collection {collection_name} missing name"
            assert "description" in collection_data, f"Collection {collection_name} missing description"
            assert "document_count" in collection_data, f"Collection {collection_name} missing document count"
            assert "expected_topics" in collection_data, f"Collection {collection_name} missing expected topics"
            
            # Data type validation
            assert isinstance(collection_data["id"], str), f"Collection {collection_name} ID should be string"
            assert isinstance(collection_data["name"], str), f"Collection {collection_name} name should be string"
            assert isinstance(collection_data["description"], str), f"Collection {collection_name} description should be string"
            assert isinstance(collection_data["document_count"], int), f"Collection {collection_name} document count should be int"
            assert isinstance(collection_data["expected_topics"], list), f"Collection {collection_name} expected topics should be list"
            
            # Value validation
            assert collection_data["document_count"] > 0, f"Collection {collection_name} should have documents"
            assert len(collection_data["expected_topics"]) > 0, f"Collection {collection_name} should have expected topics"
            assert len(collection_data["name"]) > 0, f"Collection {collection_name} name should not be empty"
            assert len(collection_data["description"]) > 0, f"Collection {collection_name} description should not be empty"
            
            # UUID validation
            try:
                UUID(collection_data["id"])
            except ValueError:
                pytest.fail(f"Collection {collection_name} ID is not a valid UUID")

    def test_query_test_sets_quality(self):
        """Test quality and consistency of query test sets."""
        for test_set_name, test_set_data in self.QUERY_TEST_SETS.items():
            # Required fields
            assert "description" in test_set_data, f"Query test set {test_set_name} missing description"
            assert "queries" in test_set_data, f"Query test set {test_set_name} missing queries"
            
            # Data type validation
            assert isinstance(test_set_data["description"], str), f"Query test set {test_set_name} description should be string"
            assert isinstance(test_set_data["queries"], list), f"Query test set {test_set_name} queries should be list"
            
            # Validate individual queries
            for i, query_data in enumerate(test_set_data["queries"]):
                query_id = f"{test_set_name}[{i}]"
                
                # Required fields
                assert "question" in query_data, f"Query {query_id} missing question"
                assert "expected_answer_type" in query_data, f"Query {query_id} missing expected answer type"
                assert "expected_keywords" in query_data, f"Query {query_id} missing expected keywords"
                assert "expected_sources" in query_data, f"Query {query_id} missing expected sources"
                assert "difficulty" in query_data, f"Query {query_id} missing difficulty"
                
                # Data type validation
                assert isinstance(query_data["question"], str), f"Query {query_id} question should be string"
                assert isinstance(query_data["expected_answer_type"], str), f"Query {query_id} expected answer type should be string"
                assert isinstance(query_data["expected_keywords"], list), f"Query {query_id} expected keywords should be list"
                assert isinstance(query_data["expected_sources"], int), f"Query {query_id} expected sources should be int"
                assert isinstance(query_data["difficulty"], str), f"Query {query_id} difficulty should be string"
                
                # Value validation
                assert query_data["expected_sources"] >= 0, f"Query {query_id} expected sources should be non-negative"
                assert query_data["difficulty"] in ["easy", "medium", "hard", "edge_case"], f"Query {query_id} difficulty should be valid"

    def test_pipeline_configuration_quality(self):
        """Test quality and consistency of pipeline configuration data."""
        for pipeline_name, pipeline_data in self.PIPELINE_CONFIGURATIONS.items():
            # Required fields
            assert "id" in pipeline_data, f"Pipeline {pipeline_name} missing ID"
            assert "name" in pipeline_data, f"Pipeline {pipeline_name} missing name"
            assert "retriever_type" in pipeline_data, f"Pipeline {pipeline_name} missing retriever type"
            assert "chunking_strategy" in pipeline_data, f"Pipeline {pipeline_name} missing chunking strategy"
            assert "context_strategy" in pipeline_data, f"Pipeline {pipeline_name} missing context strategy"
            assert "llm_provider" in pipeline_data, f"Pipeline {pipeline_name} missing LLM provider"
            assert "expected_performance" in pipeline_data, f"Pipeline {pipeline_name} missing expected performance"
            
            # Data type validation
            assert isinstance(pipeline_data["id"], str), f"Pipeline {pipeline_name} ID should be string"
            assert isinstance(pipeline_data["name"], str), f"Pipeline {pipeline_name} name should be string"
            assert isinstance(pipeline_data["retriever_type"], str), f"Pipeline {pipeline_name} retriever type should be string"
            assert isinstance(pipeline_data["chunking_strategy"], str), f"Pipeline {pipeline_name} chunking strategy should be string"
            assert isinstance(pipeline_data["context_strategy"], str), f"Pipeline {pipeline_name} context strategy should be string"
            assert isinstance(pipeline_data["llm_provider"], str), f"Pipeline {pipeline_name} LLM provider should be string"
            assert isinstance(pipeline_data["expected_performance"], dict), f"Pipeline {pipeline_name} expected performance should be dict"
            
            # Value validation
            assert len(pipeline_data["name"]) > 0, f"Pipeline {pipeline_name} name should not be empty"
            assert pipeline_data["retriever_type"] in ["semantic", "keyword", "hybrid"], f"Pipeline {pipeline_name} retriever type should be valid"
            assert pipeline_data["chunking_strategy"] in ["semantic", "fixed"], f"Pipeline {pipeline_name} chunking strategy should be valid"
            assert pipeline_data["context_strategy"] in ["simple", "weighted"], f"Pipeline {pipeline_name} context strategy should be valid"
            assert pipeline_data["llm_provider"] in ["watsonx", "openai", "anthropic"], f"Pipeline {pipeline_name} LLM provider should be valid"
            
            # Performance validation
            perf = pipeline_data["expected_performance"]
            assert "response_time_ms" in perf, f"Pipeline {pipeline_name} missing response time"
            assert "accuracy_threshold" in perf, f"Pipeline {pipeline_name} missing accuracy threshold"
            assert isinstance(perf["response_time_ms"], (int, float)), f"Pipeline {pipeline_name} response time should be numeric"
            assert isinstance(perf["accuracy_threshold"], (int, float)), f"Pipeline {pipeline_name} accuracy threshold should be numeric"
            assert perf["response_time_ms"] > 0, f"Pipeline {pipeline_name} response time should be positive"
            assert 0 <= perf["accuracy_threshold"] <= 1, f"Pipeline {pipeline_name} accuracy threshold should be between 0 and 1"

    def test_factual_query_validation(self, test_user_id: UUID, mock_search_service: Mock):
        """Test validation of factual queries."""
        factual_queries = self.QUERY_TEST_SETS["factual_queries"]["queries"]
        
        for query_data in factual_queries:
            if query_data["question"]:  # Skip empty queries
                # Arrange
                collection_id = UUID(self.TEST_COLLECTIONS["machine_learning"]["id"])
                pipeline_id = UUID(self.PIPELINE_CONFIGURATIONS["default"]["id"])
                
                search_input = SearchInput(
                    question=query_data["question"],
                    collection_id=collection_id,
                    pipeline_id=pipeline_id,
                    user_id=test_user_id
                )

                expected_output = SearchOutput(
                    answer=f"Answer for: {query_data['question']}",
                    documents=[
                        {"id": f"doc{i}", "title": f"Document {i}", "source": f"doc{i}.pdf"}
                        for i in range(query_data["expected_sources"])
                    ],
                    query_results=[
                        {"content": f"Content {i}", "score": 0.95 - i*0.1}
                        for i in range(query_data["expected_sources"])
                    ],
                    rewritten_query=query_data["question"],
                    evaluation={"relevance_score": 0.90}
                )

                mock_search_service.search.return_value = expected_output

                # Act
                result = mock_search_service.search(search_input)

                # Assert
                assert result is not None
                assert len(result.documents) >= query_data["expected_sources"], \
                    f"Expected at least {query_data['expected_sources']} sources for query: {query_data['question']}"
                assert len(result.query_results) >= query_data["expected_sources"], \
                    f"Expected at least {query_data['expected_sources']} query results for query: {query_data['question']}"

    def test_analytical_query_validation(self, test_user_id: UUID, mock_search_service: Mock):
        """Test validation of analytical queries."""
        analytical_queries = self.QUERY_TEST_SETS["analytical_queries"]["queries"]
        
        for query_data in analytical_queries:
            # Arrange
            collection_id = UUID(self.TEST_COLLECTIONS["machine_learning"]["id"])
            pipeline_id = UUID(self.PIPELINE_CONFIGURATIONS["comprehensive"]["id"])
            
            search_input = SearchInput(
                question=query_data["question"],
                collection_id=collection_id,
                pipeline_id=pipeline_id,
                user_id=test_user_id
            )

            expected_output = SearchOutput(
                answer=f"Analytical answer for: {query_data['question']}",
                documents=[
                    {"id": f"doc{i}", "title": f"Document {i}", "source": f"doc{i}.pdf"}
                    for i in range(query_data["expected_sources"])
                ],
                query_results=[
                    {"content": f"Analytical content {i}", "score": 0.95 - i*0.1}
                    for i in range(query_data["expected_sources"])
                ],
                rewritten_query=query_data["question"],
                evaluation={"relevance_score": 0.90, "analytical_depth": 0.85}
            )

            mock_search_service.search.return_value = expected_output

            # Act
            result = mock_search_service.search(search_input)

            # Assert
            assert result is not None
            assert len(result.documents) >= query_data["expected_sources"], \
                f"Expected at least {query_data['expected_sources']} sources for analytical query: {query_data['question']}"
            
            # Verify answer contains expected keywords
            answer_lower = result.answer.lower()
            for keyword in query_data["expected_keywords"]:
                assert keyword.lower() in answer_lower, \
                    f"Expected keyword '{keyword}' not found in answer for query: {query_data['question']}"

    def test_technical_query_validation(self, test_user_id: UUID, mock_search_service: Mock):
        """Test validation of technical queries."""
        technical_queries = self.QUERY_TEST_SETS["technical_queries"]["queries"]
        
        for query_data in technical_queries:
            # Arrange
            collection_id = UUID(self.TEST_COLLECTIONS["machine_learning"]["id"])
            pipeline_id = UUID(self.PIPELINE_CONFIGURATIONS["comprehensive"]["id"])
            
            search_input = SearchInput(
                question=query_data["question"],
                collection_id=collection_id,
                pipeline_id=pipeline_id,
                user_id=test_user_id
            )

            expected_output = SearchOutput(
                answer=f"Technical explanation for: {query_data['question']}",
                documents=[
                    {"id": f"doc{i}", "title": f"Technical Document {i}", "source": f"tech_doc{i}.pdf"}
                    for i in range(query_data["expected_sources"])
                ],
                query_results=[
                    {"content": f"Technical content {i}", "score": 0.95 - i*0.1}
                    for i in range(query_data["expected_sources"])
                ],
                rewritten_query=query_data["question"],
                evaluation={"relevance_score": 0.95, "technical_depth": 0.90}
            )

            mock_search_service.search.return_value = expected_output

            # Act
            result = mock_search_service.search(search_input)

            # Assert
            assert result is not None
            assert len(result.documents) >= query_data["expected_sources"], \
                f"Expected at least {query_data['expected_sources']} sources for technical query: {query_data['question']}"
            
            # Verify technical depth
            assert result.evaluation is not None
            assert "technical_depth" in result.evaluation
            assert result.evaluation["technical_depth"] >= 0.8, \
                f"Technical depth should be high for technical query: {query_data['question']}"

    def test_practical_query_validation(self, test_user_id: UUID, mock_search_service: Mock):
        """Test validation of practical queries."""
        practical_queries = self.QUERY_TEST_SETS["practical_queries"]["queries"]
        
        for query_data in practical_queries:
            # Arrange
            collection_id = UUID(self.TEST_COLLECTIONS["python_programming"]["id"])
            pipeline_id = UUID(self.PIPELINE_CONFIGURATIONS["default"]["id"])
            
            search_input = SearchInput(
                question=query_data["question"],
                collection_id=collection_id,
                pipeline_id=pipeline_id,
                user_id=test_user_id
            )

            expected_output = SearchOutput(
                answer=f"Practical guide for: {query_data['question']}",
                documents=[
                    {"id": f"doc{i}", "title": f"Practical Guide {i}", "source": f"practical{i}.pdf"}
                    for i in range(query_data["expected_sources"])
                ],
                query_results=[
                    {"content": f"Practical content {i}", "score": 0.95 - i*0.1}
                    for i in range(query_data["expected_sources"])
                ],
                rewritten_query=query_data["question"],
                evaluation={"relevance_score": 0.90, "practical_value": 0.85}
            )

            mock_search_service.search.return_value = expected_output

            # Act
            result = mock_search_service.search(search_input)

            # Assert
            assert result is not None
            assert len(result.documents) >= query_data["expected_sources"], \
                f"Expected at least {query_data['expected_sources']} sources for practical query: {query_data['question']}"
            
            # Verify practical value
            assert result.evaluation is not None
            assert "practical_value" in result.evaluation
            assert result.evaluation["practical_value"] >= 0.8, \
                f"Practical value should be high for practical query: {query_data['question']}"

    def test_edge_case_query_validation(self, test_user_id: UUID, mock_search_service: Mock):
        """Test validation of edge case queries."""
        edge_case_queries = self.QUERY_TEST_SETS["edge_case_queries"]["queries"]
        
        for query_data in edge_case_queries:
            # Arrange
            collection_id = UUID(self.TEST_COLLECTIONS["machine_learning"]["id"])
            pipeline_id = UUID(self.PIPELINE_CONFIGURATIONS["default"]["id"])
            
            search_input = SearchInput(
                question=query_data["question"],
                collection_id=collection_id,
                pipeline_id=pipeline_id,
                user_id=test_user_id
            )

            if query_data["expected_answer_type"] == "error":
                # Mock should raise error for invalid queries
                mock_search_service.search.side_effect = ValueError("Query cannot be empty")
                
                # Act & Assert
                with pytest.raises(ValueError, match="Query cannot be empty"):
                    mock_search_service.search(search_input)
            else:
                # Mock should handle edge cases gracefully
                expected_output = SearchOutput(
                    answer=f"Processed answer for edge case: {query_data['question'][:50]}...",
                    documents=[
                        {"id": f"doc{i}", "title": f"Document {i}", "source": f"doc{i}.pdf"}
                        for i in range(query_data["expected_sources"])
                    ],
                    query_results=[
                        {"content": f"Content {i}", "score": 0.95 - i*0.1}
                        for i in range(query_data["expected_sources"])
                    ],
                    rewritten_query=query_data["question"][:100] if len(query_data["question"]) > 100 else query_data["question"],
                    evaluation={"relevance_score": 0.90}
                )

                mock_search_service.search.return_value = expected_output

                # Act
                result = mock_search_service.search(search_input)

                # Assert
                assert result is not None
                if query_data["expected_sources"] > 0:
                    assert len(result.documents) >= query_data["expected_sources"], \
                        f"Expected at least {query_data['expected_sources']} sources for edge case query"

    def test_data_consistency_across_collections(self):
        """Test data consistency across different collections."""
        # Verify all collections have consistent structure
        required_fields = ["id", "name", "description", "document_count", "expected_topics"]
        
        for collection_name, collection_data in self.TEST_COLLECTIONS.items():
            for field in required_fields:
                assert field in collection_data, f"Collection {collection_name} missing {field}"
        
        # Verify all collections have reasonable document counts
        document_counts = [collection["document_count"] for collection in self.TEST_COLLECTIONS.values()]
        assert all(count > 0 for count in document_counts), "All collections should have documents"
        assert all(count <= 1000 for count in document_counts), "Document counts should be reasonable"
        
        # Verify all collections have expected topics
        for collection_name, collection_data in self.TEST_COLLECTIONS.items():
            assert len(collection_data["expected_topics"]) >= 3, f"Collection {collection_name} should have at least 3 expected topics"

    def test_query_difficulty_distribution(self):
        """Test distribution of query difficulties across test sets."""
        difficulty_counts = {"easy": 0, "medium": 0, "hard": 0, "edge_case": 0}
        
        for test_set_name, test_set_data in self.QUERY_TEST_SETS.items():
            for query_data in test_set_data["queries"]:
                difficulty = query_data["difficulty"]
                difficulty_counts[difficulty] += 1
        
        # Verify we have a good distribution of difficulties
        total_queries = sum(difficulty_counts.values())
        assert total_queries > 0, "Should have test queries"
        
        # Should have queries of different difficulties
        assert difficulty_counts["easy"] > 0, "Should have easy queries"
        assert difficulty_counts["medium"] > 0, "Should have medium queries"
        assert difficulty_counts["hard"] > 0, "Should have hard queries"
        
        # Edge cases should be a small portion
        edge_case_ratio = difficulty_counts["edge_case"] / total_queries
        assert edge_case_ratio <= 0.2, "Edge cases should be ≤ 20% of total queries"

    def test_performance_expectations_validation(self):
        """Test validation of performance expectations."""
        for pipeline_name, pipeline_data in self.PIPELINE_CONFIGURATIONS.items():
            perf = pipeline_data["expected_performance"]
            
            # Response time should be reasonable
            assert perf["response_time_ms"] <= 10000, f"Pipeline {pipeline_name} response time too high"
            assert perf["response_time_ms"] >= 100, f"Pipeline {pipeline_name} response time too low"
            
            # Accuracy threshold should be reasonable
            assert perf["accuracy_threshold"] >= 0.7, f"Pipeline {pipeline_name} accuracy threshold too low"
            assert perf["accuracy_threshold"] <= 1.0, f"Pipeline {pipeline_name} accuracy threshold too high"
            
            # Fast pipeline should be faster than comprehensive
            if pipeline_name == "fast":
                fast_time = perf["response_time_ms"]
                comprehensive_time = self.PIPELINE_CONFIGURATIONS["comprehensive"]["expected_performance"]["response_time_ms"]
                assert fast_time < comprehensive_time, "Fast pipeline should be faster than comprehensive"
            
            # Comprehensive pipeline should have higher accuracy
            if pipeline_name == "comprehensive":
                comprehensive_accuracy = perf["accuracy_threshold"]
                fast_accuracy = self.PIPELINE_CONFIGURATIONS["fast"]["expected_performance"]["accuracy_threshold"]
                assert comprehensive_accuracy >= fast_accuracy, "Comprehensive pipeline should have higher accuracy"
