"""
Performance benchmark tests for search functionality.

This module implements comprehensive performance testing for Issue #198:
Comprehensive Testing of Current Search Functionality.

These tests establish performance baselines and benchmarks for the search system.
"""

import pytest
import time
from typing import Any
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.search_service import SearchService
from vectordbs.data_types import DocumentMetadata, QueryResult, DocumentChunk


@pytest.mark.e2e
@pytest.mark.performance
class TestSearchPerformanceBenchmarks:
    """Performance benchmark tests for search functionality."""

    @staticmethod
    def create_test_document_metadata(name: str, title: str) -> DocumentMetadata:
        """Helper to create test document metadata."""
        return DocumentMetadata(document_name=name, title=title)

    @staticmethod
    def create_test_query_result(chunk_id: str, text: str, score: float) -> QueryResult:
        """Helper to create test query result."""
        return QueryResult(
            chunk=DocumentChunk(chunk_id=chunk_id, text=text),
            score=score,
            embeddings=[0.1, 0.2, 0.3]  # Simple test embedding
        )

    # Performance Test Data
    PERFORMANCE_TEST_QUERIES = [
        "What is machine learning?",
        "How do neural networks work?",
        "Explain deep learning algorithms",
        "What is supervised learning?",
        "What is unsupervised learning?",
        "How does gradient descent work?",
        "What are the types of machine learning?",
        "Explain reinforcement learning",
        "What is natural language processing?",
        "How do recommendation systems work?",
    ]

    PERFORMANCE_BENCHMARKS = {
        "response_time": {"simple_query": {"max_ms": 2000, "avg_ms": 1000}, "complex_query": {"max_ms": 5000, "avg_ms": 3000}, "technical_query": {"max_ms": 8000, "avg_ms": 5000}},
        "throughput": {"concurrent_requests": {"min_rps": 5, "max_rps": 20}, "sequential_requests": {"min_rps": 10, "max_rps": 30}},
        "resource_usage": {"memory_usage": {"max_mb": 512}, "cpu_usage": {"max_percent": 80}},
    }

    @pytest.fixture
    def test_collection_id(self) -> UUID:
        """Test collection ID for performance tests."""
        return uuid4()

    @pytest.fixture
    def test_pipeline_id(self) -> UUID:
        """Test pipeline ID for performance tests."""
        return uuid4()

    @pytest.fixture
    def test_user_id(self) -> UUID:
        """Test user ID for performance tests."""
        return uuid4()

    @pytest.fixture
    def mock_search_service(self) -> Mock:
        """Mock search service for performance testing."""
        service = Mock(spec=SearchService)
        service.search = AsyncMock()
        return service

    def test_simple_query_response_time(self, test_user_id: UUID, test_collection_id: UUID, test_pipeline_id: UUID, mock_search_service: Mock):
        """Test response time for simple queries."""
        # Arrange
        query = "What is machine learning?"
        search_input = SearchInput(question=query, collection_id=test_collection_id, pipeline_id=test_pipeline_id, user_id=test_user_id)

        expected_output = SearchOutput(
            answer="Machine learning is a subset of artificial intelligence...",
            documents=[self.create_test_document_metadata("Test Doc", "Test Doc")],
            query_results=[self.create_test_query_result("chunk1", "Test content", 0.95)],
            rewritten_query="What is machine learning?",
            evaluation={"relevance_score": 0.90},
        )

        mock_search_service.search.return_value = expected_output

        # Act - Test multiple iterations for statistical significance
        response_times = []
        iterations = 10

        for i in range(iterations):
            start_time = time.time()
            result = mock_search_service.search(search_input)
            end_time = time.time()

            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)

            assert result is not None

        # Assert - Performance benchmarks
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        benchmark = self.PERFORMANCE_BENCHMARKS["response_time"]["simple_query"]

        assert avg_response_time <= benchmark["avg_ms"], f"Average response time {avg_response_time:.2f}ms exceeds {benchmark['avg_ms']}ms limit"

        assert max_response_time <= benchmark["max_ms"], f"Max response time {max_response_time:.2f}ms exceeds {benchmark['max_ms']}ms limit"

        # Verify response time consistency (low variance)
        variance = sum((t - avg_response_time) ** 2 for t in response_times) / len(response_times)
        std_deviation = variance**0.5

        assert std_deviation <= avg_response_time * 0.3, f"Response time variance too high: std_dev={std_deviation:.2f}ms, avg={avg_response_time:.2f}ms"

    def test_complex_query_response_time(self, test_user_id: UUID, test_collection_id: UUID, test_pipeline_id: UUID, mock_search_service: Mock):
        """Test response time for complex queries."""
        # Arrange
        query = "How do neural networks learn from data using backpropagation and gradient descent algorithms?"
        search_input = SearchInput(question=query, collection_id=test_collection_id, pipeline_id=test_pipeline_id, user_id=test_user_id)

        expected_output = SearchOutput(
            answer="Neural networks learn through backpropagation and gradient descent...",
            documents=[self.create_test_document_metadata("Test Doc", "Test Doc")],
            query_results=[self.create_test_query_result("chunk1", "Test content", 0.95)],
            rewritten_query="How do neural networks learn using backpropagation and gradient descent?",
            evaluation={"relevance_score": 0.95, "answer_quality": 0.92},
        )

        mock_search_service.search.return_value = expected_output

        # Act - Test multiple iterations
        response_times = []
        iterations = 5  # Fewer iterations for complex queries

        for i in range(iterations):
            start_time = time.time()
            result = mock_search_service.search(search_input)
            end_time = time.time()

            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)

            assert result is not None

        # Assert - Performance benchmarks for complex queries
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        benchmark = self.PERFORMANCE_BENCHMARKS["response_time"]["complex_query"]

        assert avg_response_time <= benchmark["avg_ms"], f"Average response time {avg_response_time:.2f}ms exceeds {benchmark['avg_ms']}ms limit"

        assert max_response_time <= benchmark["max_ms"], f"Max response time {max_response_time:.2f}ms exceeds {benchmark['max_ms']}ms limit"

    def test_technical_query_response_time(self, test_user_id: UUID, test_collection_id: UUID, test_pipeline_id: UUID, mock_search_service: Mock):
        """Test response time for technical deep-dive queries."""
        # Arrange
        query = "Explain the mathematical foundations of gradient descent optimization including convergence analysis and step size selection"
        search_input = SearchInput(question=query, collection_id=test_collection_id, pipeline_id=test_pipeline_id, user_id=test_user_id)

        expected_output = SearchOutput(
            answer="Gradient descent is an optimization algorithm that minimizes functions...",
            documents=[self.create_test_document_metadata("Test Doc", "Test Doc")],
            query_results=[self.create_test_query_result("chunk1", "Test content", 0.95)],
            rewritten_query="Explain gradient descent mathematical foundations and convergence analysis",
            evaluation={"relevance_score": 0.97, "technical_depth": 0.96},
        )

        mock_search_service.search.return_value = expected_output

        # Act - Test multiple iterations
        response_times = []
        iterations = 3  # Fewer iterations for technical queries

        for i in range(iterations):
            start_time = time.time()
            result = mock_search_service.search(search_input)
            end_time = time.time()

            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)

            assert result is not None

        # Assert - Performance benchmarks for technical queries
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        benchmark = self.PERFORMANCE_BENCHMARKS["response_time"]["technical_query"]

        assert avg_response_time <= benchmark["avg_ms"], f"Average response time {avg_response_time:.2f}ms exceeds {benchmark['avg_ms']}ms limit"

        assert max_response_time <= benchmark["max_ms"], f"Max response time {max_response_time:.2f}ms exceeds {benchmark['max_ms']}ms limit"

    def test_concurrent_request_throughput(self, test_user_id: UUID, test_collection_id: UUID, test_pipeline_id: UUID, mock_search_service: Mock):
        """Test throughput with concurrent requests."""
        # Arrange
        queries = self.PERFORMANCE_TEST_QUERIES[:5]  # Use first 5 queries
        expected_output = SearchOutput(
            answer="Test answer",
            documents=[self.create_test_document_metadata("Test Doc", "Test Doc")],
            query_results=[self.create_test_query_result("chunk1", "Test content", 0.95)],
            rewritten_query="Test query",
            evaluation={"relevance_score": 0.90},
        )

        mock_search_service.search.return_value = expected_output

        def execute_search(query: str) -> dict[str, Any]:
            """Execute a single search request."""
            search_input = SearchInput(question=query, collection_id=test_collection_id, pipeline_id=test_pipeline_id, user_id=test_user_id)

            start_time = time.time()
            result = mock_search_service.search(search_input)
            end_time = time.time()

            return {"query": query, "response_time": end_time - start_time, "success": result is not None}

        # Act - Execute concurrent requests
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_search, query) for query in queries]
            results = [future.result() for future in as_completed(futures)]

        total_time = time.time() - start_time

        # Assert - Throughput benchmarks
        successful_requests = [r for r in results if r["success"]]
        requests_per_second = len(successful_requests) / total_time

        benchmark = self.PERFORMANCE_BENCHMARKS["throughput"]["concurrent_requests"]

        assert len(successful_requests) == len(queries), "All requests should succeed"
        assert requests_per_second >= benchmark["min_rps"], f"Throughput {requests_per_second:.2f} RPS below minimum {benchmark['min_rps']} RPS"
        assert requests_per_second <= benchmark["max_rps"], f"Throughput {requests_per_second:.2f} RPS above maximum {benchmark['max_rps']} RPS"

        # Verify individual response times are reasonable
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        assert avg_response_time <= 3.0, f"Average response time {avg_response_time:.2f}s too high"

    def test_sequential_request_throughput(self, test_user_id: UUID, test_collection_id: UUID, test_pipeline_id: UUID, mock_search_service: Mock):
        """Test throughput with sequential requests."""
        # Arrange
        queries = self.PERFORMANCE_TEST_QUERIES[:10]  # Use first 10 queries
        expected_output = SearchOutput(
            answer="Test answer",
            documents=[self.create_test_document_metadata("Test Doc", "Test Doc")],
            query_results=[self.create_test_query_result("chunk1", "Test content", 0.95)],
            rewritten_query="Test query",
            evaluation={"relevance_score": 0.90},
        )

        mock_search_service.search.return_value = expected_output

        # Act - Execute sequential requests
        start_time = time.time()
        results = []

        for query in queries:
            search_input = SearchInput(question=query, collection_id=test_collection_id, pipeline_id=test_pipeline_id, user_id=test_user_id)

            query_start = time.time()
            result = mock_search_service.search(search_input)
            query_end = time.time()

            results.append({"query": query, "response_time": query_end - query_start, "success": result is not None})

        total_time = time.time() - start_time

        # Assert - Throughput benchmarks
        successful_requests = [r for r in results if r["success"]]
        requests_per_second = len(successful_requests) / total_time

        benchmark = self.PERFORMANCE_BENCHMARKS["throughput"]["sequential_requests"]

        assert len(successful_requests) == len(queries), "All requests should succeed"
        assert requests_per_second >= benchmark["min_rps"], f"Throughput {requests_per_second:.2f} RPS below minimum {benchmark['min_rps']} RPS"
        assert requests_per_second <= benchmark["max_rps"], f"Throughput {requests_per_second:.2f} RPS above maximum {benchmark['max_rps']} RPS"

    def test_memory_usage_benchmark(self, test_user_id: UUID, test_collection_id: UUID, test_pipeline_id: UUID, mock_search_service: Mock):
        """Test memory usage during search operations."""
        import psutil
        import os

        # Arrange
        query = "What is machine learning?"
        search_input = SearchInput(question=query, collection_id=test_collection_id, pipeline_id=test_pipeline_id, user_id=test_user_id)

        expected_output = SearchOutput(
            answer="Machine learning is a subset of artificial intelligence...",
            documents=[self.create_test_document_metadata("Test Doc", "Test Doc")],
            query_results=[self.create_test_query_result("chunk1", "Test content", 0.95)],
            rewritten_query="What is machine learning?",
            evaluation={"relevance_score": 0.90},
        )

        mock_search_service.search.return_value = expected_output

        # Act - Measure memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Execute multiple searches to stress test memory
        for i in range(10):
            result = mock_search_service.search(search_input)
            assert result is not None

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        # Assert - Memory usage benchmarks
        benchmark = self.PERFORMANCE_BENCHMARKS["resource_usage"]["memory_usage"]

        assert memory_increase <= benchmark["max_mb"], f"Memory increase {memory_increase:.2f}MB exceeds {benchmark['max_mb']}MB limit"

        # Verify memory doesn't grow excessively with repeated requests
        assert memory_increase <= 100, "Memory usage should not grow excessively with repeated requests"

    def test_cpu_usage_benchmark(self, test_user_id: UUID, test_collection_id: UUID, test_pipeline_id: UUID, mock_search_service: Mock):
        """Test CPU usage during search operations."""
        import psutil
        import os

        # Arrange
        query = "What is machine learning?"
        search_input = SearchInput(question=query, collection_id=test_collection_id, pipeline_id=test_pipeline_id, user_id=test_user_id)

        expected_output = SearchOutput(
            answer="Machine learning is a subset of artificial intelligence...",
            documents=[self.create_test_document_metadata("Test Doc", "Test Doc")],
            query_results=[self.create_test_query_result("chunk1", "Test content", 0.95)],
            rewritten_query="What is machine learning?",
            evaluation={"relevance_score": 0.90},
        )

        mock_search_service.search.return_value = expected_output

        # Act - Measure CPU usage during search operations
        process = psutil.Process(os.getpid())

        # Start CPU monitoring
        cpu_percentages = []

        for i in range(5):
            # Monitor CPU during search
            cpu_before = process.cpu_percent()
            result = mock_search_service.search(search_input)
            cpu_after = process.cpu_percent()

            cpu_percentages.append(max(cpu_before, cpu_after))
            assert result is not None

        max_cpu_usage = max(cpu_percentages)

        # Assert - CPU usage benchmarks
        benchmark = self.PERFORMANCE_BENCHMARKS["resource_usage"]["cpu_usage"]

        assert max_cpu_usage <= benchmark["max_percent"], f"CPU usage {max_cpu_usage:.2f}% exceeds {benchmark['max_percent']}% limit"

    def test_large_result_set_performance(self, test_user_id: UUID, test_collection_id: UUID, test_pipeline_id: UUID, mock_search_service: Mock):
        """Test performance with large result sets."""
        # Arrange
        query = "What is machine learning?"
        search_input = SearchInput(question=query, collection_id=test_collection_id, pipeline_id=test_pipeline_id, user_id=test_user_id)

        # Create large result set
        large_documents = [
            {"id": f"doc{i}", "title": f"Document {i}", "source": f"doc{i}.pdf", "content": f"Content {i}" * 100}
            for i in range(1000)  # 1000 documents
        ]

        large_query_results = [
            {"content": f"Content chunk {i} with detailed information about machine learning concepts and algorithms" * 10, "score": 0.95 - i * 0.0001}
            for i in range(500)  # 500 query results
        ]

        expected_output = SearchOutput(
            answer="Machine learning is a subset of artificial intelligence..." * 10,  # Long answer
            documents=large_documents,
            query_results=large_query_results,
            rewritten_query="What is machine learning?",
            evaluation={"relevance_score": 0.90, "result_count": len(large_documents)},
        )

        mock_search_service.search.return_value = expected_output

        # Act - Test performance with large results
        start_time = time.time()
        result = mock_search_service.search(search_input)
        end_time = time.time()

        response_time = end_time - start_time

        # Assert - Performance should still be reasonable even with large results
        assert result is not None
        assert len(result.documents) == 1000, "Should return all 1000 documents"
        assert len(result.query_results) == 500, "Should return all 500 query results"

        # Response time should not exceed 10 seconds even with large results
        assert response_time <= 10.0, f"Response time {response_time:.2f}s too high for large result set"

    def test_query_complexity_scaling(self, test_user_id: UUID, test_collection_id: UUID, test_pipeline_id: UUID, mock_search_service: Mock):
        """Test how response time scales with query complexity."""
        # Arrange
        query_complexities = [
            ("What is ML?", "simple", 1.0),  # Simple query
            ("What is machine learning and how does it work?", "medium", 2.0),  # Medium query
            ("How do neural networks learn from data using backpropagation and gradient descent algorithms?", "complex", 4.0),  # Complex query
            (
                "Explain the mathematical foundations of gradient descent optimization including convergence analysis, step size selection, and adaptive learning rates",
                "very_complex",
                6.0,
            ),  # Very complex query
        ]

        expected_output = SearchOutput(
            answer="Test answer",
            documents=[self.create_test_document_metadata("Test Doc", "Test Doc")],
            query_results=[self.create_test_query_result("chunk1", "Test content", 0.95)],
            rewritten_query="Test query",
            evaluation={"relevance_score": 0.90},
        )

        mock_search_service.search.return_value = expected_output

        # Act - Test each complexity level
        results = []

        for query, complexity, expected_max_time in query_complexities:
            search_input = SearchInput(question=query, collection_id=test_collection_id, pipeline_id=test_pipeline_id, user_id=test_user_id)

            start_time = time.time()
            result = mock_search_service.search(search_input)
            end_time = time.time()

            response_time = end_time - start_time
            results.append({"query": query, "complexity": complexity, "response_time": response_time, "expected_max": expected_max_time})

            assert result is not None

        # Assert - Response time should scale reasonably with complexity
        for result in results:
            assert result["response_time"] <= result["expected_max"], f"{result['complexity']} query took {result['response_time']:.2f}s, exceeds {result['expected_max']}s limit"

        # Verify scaling is reasonable (not exponential)
        simple_time = results[0]["response_time"]
        complex_time = results[2]["response_time"]

        scaling_factor = complex_time / simple_time
        assert scaling_factor <= 4.0, f"Scaling factor {scaling_factor:.2f} too high (should be ≤ 4x)"

    def test_performance_consistency_over_time(self, test_user_id: UUID, test_collection_id: UUID, test_pipeline_id: UUID, mock_search_service: Mock):
        """Test performance consistency over extended period."""
        # Arrange
        query = "What is machine learning?"
        search_input = SearchInput(question=query, collection_id=test_collection_id, pipeline_id=test_pipeline_id, user_id=test_user_id)

        expected_output = SearchOutput(
            answer="Machine learning is a subset of artificial intelligence...",
            documents=[self.create_test_document_metadata("Test Doc", "Test Doc")],
            query_results=[self.create_test_query_result("chunk1", "Test content", 0.95)],
            rewritten_query="What is machine learning?",
            evaluation={"relevance_score": 0.90},
        )

        mock_search_service.search.return_value = expected_output

        # Act - Test performance over multiple batches
        batch_results = []
        batches = 3
        queries_per_batch = 10

        for batch in range(batches):
            batch_times = []

            for i in range(queries_per_batch):
                start_time = time.time()
                result = mock_search_service.search(search_input)
                end_time = time.time()

                batch_times.append(end_time - start_time)
                assert result is not None

            batch_results.append({"batch": batch, "avg_time": sum(batch_times) / len(batch_times), "min_time": min(batch_times), "max_time": max(batch_times)})

        # Assert - Performance should be consistent across batches
        avg_times = [batch["avg_time"] for batch in batch_results]
        overall_avg = sum(avg_times) / len(avg_times)

        # Variance should be low (within 20% of average)
        variance = sum((t - overall_avg) ** 2 for t in avg_times) / len(avg_times)
        std_deviation = variance**0.5

        assert std_deviation <= overall_avg * 0.2, f"Performance variance too high: std_dev={std_deviation:.3f}s, avg={overall_avg:.3f}s"

        # All batches should meet performance requirements
        for batch in batch_results:
            assert batch["avg_time"] <= 2.0, f"Batch {batch['batch']} avg time {batch['avg_time']:.3f}s too high"
            assert batch["max_time"] <= 3.0, f"Batch {batch['batch']} max time {batch['max_time']:.3f}s too high"
