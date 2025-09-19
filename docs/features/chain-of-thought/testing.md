# CoT Testing Guide

This guide covers testing strategies, patterns, and examples for the Chain of Thought system, including unit tests, integration tests, and performance testing.

## Overview

The CoT system requires comprehensive testing due to its:

- **Complex reasoning logic**: Multi-step processes with dependencies
- **External dependencies**: LLM services, vector databases, search systems
- **Performance characteristics**: Token usage, execution time, memory consumption
- **Source attribution accuracy**: Correct tracking and aggregation of sources
- **Configuration variability**: Multiple strategies and parameters

## Testing Architecture

### Test Categories

1. **Unit Tests**: Individual component testing with mocks
2. **Integration Tests**: End-to-end workflow testing
3. **Performance Tests**: Benchmarking and resource usage
4. **Regression Tests**: Ensuring stability across changes
5. **Property-Based Tests**: Testing with generated data

### Test Structure

```
tests/
├── unit/
│   ├── test_chain_of_thought_service_tdd.py      # Main service tests
│   ├── test_question_decomposer.py               # Decomposition logic
│   ├── test_answer_synthesizer.py                # Answer synthesis
│   └── test_source_attribution_service.py       # Source tracking
├── integration/
│   ├── test_cot_integration.py                   # End-to-end tests
│   ├── test_cot_with_real_llm.py                # Real LLM integration
│   └── test_cot_performance.py                  # Performance testing
├── fixtures/
│   ├── cot_test_data.py                         # Test data fixtures
│   └── mock_services.py                         # Mock service setup
└── conftest.py                                  # Pytest configuration
```

## Unit Testing

### Testing ChainOfThoughtService

```python
import pytest
from unittest.mock import Mock, AsyncMock
from uuid import UUID, uuid4

from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.schemas.chain_of_thought_schema import (
    ChainOfThoughtInput,
    ChainOfThoughtConfig,
    QuestionClassification
)

@pytest.fixture
def mock_settings():
    settings = Mock()
    settings.cot_max_reasoning_depth = 3
    settings.cot_reasoning_strategy = "decomposition"
    settings.cot_token_budget_multiplier = 2.0
    return settings

@pytest.fixture
def mock_llm_service():
    llm = AsyncMock()
    llm.generate_response = AsyncMock(return_value="Mock LLM response")
    return llm

@pytest.fixture
def cot_service(mock_settings, mock_llm_service):
    return ChainOfThoughtService(
        settings=mock_settings,
        llm_service=mock_llm_service
    )

@pytest.mark.asyncio
class TestChainOfThoughtService:
    """Test suite for ChainOfThoughtService."""

    async def test_question_classification_simple(self, cot_service):
        """Test classification of simple questions."""
        question = "What is machine learning?"
        classification = await cot_service.classify_question(question)

        assert classification.question_type == "simple"
        assert classification.complexity_level == "low"
        assert not classification.requires_cot
        assert classification.estimated_steps == 1
        assert classification.confidence > 0.8

    async def test_question_classification_comparison(self, cot_service):
        """Test classification of comparison questions."""
        question = "Compare supervised and unsupervised learning approaches"
        classification = await cot_service.classify_question(question)

        assert classification.question_type == "comparison"
        assert classification.complexity_level in ["medium", "high"]
        assert classification.requires_cot
        assert classification.estimated_steps >= 3

    async def test_question_classification_causal(self, cot_service):
        """Test classification of causal questions."""
        question = "Why do neural networks sometimes overfit to training data?"
        classification = await cot_service.classify_question(question)

        assert classification.question_type == "causal"
        assert classification.requires_cot
        assert "why" in classification.reasoning.lower()

    async def test_cot_execution_full_pipeline(self, cot_service):
        """Test complete CoT execution pipeline."""
        cot_input = ChainOfThoughtInput(
            question="Compare machine learning and deep learning",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={
                "enabled": True,
                "max_reasoning_depth": 3,
                "reasoning_strategy": "decomposition"
            }
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        # Verify output structure
        assert result.original_question == cot_input.question
        assert result.final_answer is not None
        assert len(result.reasoning_steps) > 0
        assert result.total_confidence > 0
        assert result.total_execution_time > 0
        assert result.reasoning_strategy == "decomposition"

    async def test_cot_disabled_fallback(self, cot_service):
        """Test fallback behavior when CoT is disabled."""
        cot_input = ChainOfThoughtInput(
            question="Test question",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={"enabled": False}
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        assert result.final_answer == "Regular search result"
        assert len(result.reasoning_steps) == 0
        assert result.reasoning_strategy == "disabled"

    async def test_reasoning_step_execution(self, cot_service):
        """Test individual reasoning step execution."""
        step = await cot_service.execute_reasoning_step(
            step_number=1,
            question="What is supervised learning?",
            context=["Machine learning context..."],
            previous_answers=[]
        )

        assert step.step_number == 1
        assert step.question == "What is supervised learning?"
        assert step.intermediate_answer is not None
        assert step.confidence_score >= 0.6  # Meets evaluation threshold
        assert step.execution_time > 0
        assert len(step.source_attributions) > 0  # Source attribution added

    async def test_error_handling_llm_failure(self, cot_service):
        """Test error handling when LLM service fails."""
        from core.custom_exceptions import LLMProviderError

        # Mock LLM service to raise error
        cot_service.llm_service.generate_response.side_effect = LLMProviderError(
            provider="test",
            error_type="api_error",
            message="Mock LLM failure"
        )

        with pytest.raises(LLMProviderError) as exc_info:
            await cot_service.execute_reasoning_step(
                step_number=1,
                question="Test question",
                context=[],
                previous_answers=[]
            )

        assert "Mock LLM failure" in str(exc_info.value)

    async def test_configuration_validation(self, cot_service):
        """Test configuration validation."""
        from core.custom_exceptions import ValidationError

        # Test invalid configuration
        cot_input = ChainOfThoughtInput(
            question="Test question",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={
                "max_reasoning_depth": -1,  # Invalid
                "reasoning_strategy": "invalid_strategy"  # Invalid
            }
        )

        with pytest.raises(ValidationError):
            await cot_service.execute_chain_of_thought(cot_input)

    async def test_token_budget_management(self, cot_service):
        """Test token budget calculation and management."""
        cot_input = ChainOfThoughtInput(
            question="This is a test question with multiple words",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={
                "token_budget_multiplier": 2.5
            }
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        assert result.token_usage > 0
        # Token usage should reflect the multiplier and complexity
        expected_minimum = len(cot_input.question.split()) * 10
        assert result.token_usage >= expected_minimum
```

### Testing SourceAttributionService

```python
import pytest
from rag_solution.services.source_attribution_service import SourceAttributionService
from rag_solution.schemas.chain_of_thought_schema import SourceAttribution, ReasoningStep

class TestSourceAttributionService:
    """Test suite for SourceAttributionService."""

    @pytest.fixture
    def service(self):
        return SourceAttributionService()

    def test_create_source_attribution(self, service):
        """Test creating source attribution objects."""
        attribution = service.create_source_attribution(
            document_id="test_doc",
            relevance_score=0.85,
            document_title="Test Document",
            excerpt="This is a test excerpt",
            retrieval_rank=1
        )

        assert attribution.document_id == "test_doc"
        assert attribution.relevance_score == 0.85
        assert attribution.document_title == "Test Document"
        assert attribution.excerpt == "This is a test excerpt"
        assert attribution.retrieval_rank == 1

    def test_extract_sources_from_structured_results(self, service):
        """Test source extraction from structured search results."""
        search_results = [
            {
                "document_id": "doc_1",
                "title": "AI Guide",
                "score": 0.92,
                "content": "Artificial intelligence involves...",
                "chunk_index": 0
            },
            {
                "document_id": "doc_2",
                "score": 0.78,
                "content": "Machine learning is a subset..."
            }
        ]

        attributions = service.extract_sources_from_context([], search_results)

        assert len(attributions) == 2
        assert attributions[0].document_id == "doc_1"
        assert attributions[0].relevance_score == 0.92
        assert attributions[0].document_title == "AI Guide"
        assert attributions[0].retrieval_rank == 1

        assert attributions[1].document_id == "doc_2"
        assert attributions[1].relevance_score == 0.78
        assert attributions[1].retrieval_rank == 2

    def test_extract_sources_from_context_strings(self, service):
        """Test source extraction from raw context strings."""
        context_docs = [
            "id:doc_123 Machine learning algorithms can be categorized...",
            "Deep learning is a subset of machine learning that uses neural networks...",
            ""  # Empty context should be ignored
        ]

        attributions = service.extract_sources_from_context(context_docs)

        assert len(attributions) == 2  # Empty context ignored
        assert attributions[0].document_id == "doc_123"
        assert attributions[0].relevance_score == 1.0  # Highest for first result
        assert attributions[1].document_id == "context_doc_1"
        assert attributions[1].relevance_score == 0.9  # Decreasing by rank

    def test_source_aggregation_across_steps(self, service):
        """Test aggregating sources across multiple reasoning steps."""
        # Create test reasoning steps with source attributions
        step1 = ReasoningStep(
            step_number=1,
            question="What is AI?",
            source_attributions=[
                SourceAttribution(document_id="doc_1", relevance_score=0.9),
                SourceAttribution(document_id="doc_2", relevance_score=0.8)
            ]
        )

        step2 = ReasoningStep(
            step_number=2,
            question="What is ML?",
            source_attributions=[
                SourceAttribution(document_id="doc_1", relevance_score=0.85),  # Duplicate with lower score
                SourceAttribution(document_id="doc_3", relevance_score=0.75)
            ]
        )

        summary = service.aggregate_sources_across_steps([step1, step2])

        # Should have 3 unique sources
        assert len(summary.all_sources) == 3

        # doc_1 should have the higher relevance score (0.9, not 0.85)
        doc_1_source = next(s for s in summary.all_sources if s.document_id == "doc_1")
        assert doc_1_source.relevance_score == 0.9

        # Primary sources should include high-relevance sources
        primary_ids = [s.document_id for s in summary.primary_sources]
        assert "doc_1" in primary_ids  # relevance 0.9 > 0.7

        # Step breakdown should track usage
        assert 1 in summary.source_usage_by_step
        assert 2 in summary.source_usage_by_step
        assert "doc_1" in summary.source_usage_by_step[1]
        assert "doc_1" in summary.source_usage_by_step[2]

    def test_source_enhancement_for_reasoning_step(self, service):
        """Test enhancing reasoning steps with source attributions."""
        original_step = ReasoningStep(
            step_number=1,
            question="Test question",
            context_used=["id:doc_1 Some content...", "More content..."]
        )

        enhanced_step = service.enhance_reasoning_step_with_sources(original_step)

        assert len(enhanced_step.source_attributions) == 2
        assert enhanced_step.source_attributions[0].document_id == "doc_1"
        assert enhanced_step.source_attributions[1].document_id == "context_doc_1"

    def test_source_display_formatting(self, service):
        """Test formatting sources for UI display."""
        # Create sample source summary
        summary = service.aggregate_sources_across_steps([
            ReasoningStep(
                step_number=1,
                question="Test",
                source_attributions=[
                    SourceAttribution(
                        document_id="doc_1",
                        document_title="AI Guide",
                        relevance_score=0.95,
                        excerpt="Artificial intelligence is..."
                    )
                ]
            )
        ])

        formatted = service.format_sources_for_display(summary, include_excerpts=True)

        assert formatted["total_sources"] == 1
        assert len(formatted["primary_sources"]) == 1
        assert formatted["primary_sources"][0]["title"] == "AI Guide"
        assert formatted["primary_sources"][0]["relevance"] == 0.95
        assert "excerpt" in formatted["primary_sources"][0]
        assert "step_1" in formatted["step_breakdown"]
```

## Integration Testing

### End-to-End CoT Testing

```python
import pytest
from uuid import uuid4
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput

@pytest.mark.integration
class TestCotIntegration:
    """Integration tests for complete CoT workflows."""

    @pytest.fixture
    def integration_service(self, integration_settings, real_llm_service):
        """Service setup with real dependencies for integration testing."""
        return ChainOfThoughtService(
            settings=integration_settings,
            llm_service=real_llm_service
        )

    @pytest.mark.asyncio
    async def test_complete_workflow_comparison_question(self, integration_service):
        """Test complete workflow for comparison questions."""
        cot_input = ChainOfThoughtInput(
            question="Compare supervised learning and unsupervised learning for image classification tasks",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={
                "reasoning_strategy": "decomposition",
                "max_reasoning_depth": 3
            }
        )

        result = await integration_service.execute_chain_of_thought(cot_input)

        # Verify result quality
        assert result.final_answer is not None
        assert len(result.final_answer.split()) >= 50  # Substantial answer
        assert len(result.reasoning_steps) == 3  # Expected decomposition steps
        assert result.total_confidence > 0.6
        assert result.source_summary is not None

        # Verify reasoning progression
        steps = result.reasoning_steps
        assert "supervised" in steps[0].question.lower()
        assert "unsupervised" in steps[1].question.lower()
        assert any(word in steps[2].question.lower() for word in ["compare", "differ", "classification"])

    @pytest.mark.asyncio
    async def test_complete_workflow_causal_question(self, integration_service):
        """Test complete workflow for causal questions."""
        cot_input = ChainOfThoughtInput(
            question="Why do deep neural networks suffer from vanishing gradients during backpropagation?",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={
                "reasoning_strategy": "causal",
                "max_reasoning_depth": 4
            }
        )

        result = await integration_service.execute_chain_of_thought(cot_input)

        # Verify causal reasoning structure
        assert result.reasoning_strategy == "causal"
        assert len(result.reasoning_steps) >= 3

        # Should show progression from concept to mechanism to consequences
        step_questions = [step.question.lower() for step in result.reasoning_steps]
        has_concept_step = any("gradient" in q for q in step_questions)
        has_mechanism_step = any(any(word in q for word in ["how", "propagate", "backpropagation"]) for q in step_questions)

        assert has_concept_step
        assert has_mechanism_step

    @pytest.mark.asyncio
    async def test_source_attribution_accuracy(self, integration_service):
        """Test accuracy of source attribution in real scenarios."""
        # Provide context documents
        context_docs = [
            "Machine learning algorithms require training data to learn patterns and make predictions.",
            "Deep learning uses neural networks with multiple layers to process complex data.",
            "Supervised learning uses labeled examples to train predictive models."
        ]

        cot_input = ChainOfThoughtInput(
            question="How does machine learning differ from deep learning?",
            collection_id=uuid4(),
            user_id=uuid4()
        )

        result = await integration_service.execute_chain_of_thought(
            cot_input,
            context_documents=context_docs
        )

        # Verify source attribution
        assert result.source_summary is not None
        assert len(result.source_summary.all_sources) > 0

        # Each reasoning step should have source attributions
        for step in result.reasoning_steps:
            assert len(step.source_attributions) > 0
            for attribution in step.source_attributions:
                assert attribution.document_id is not None
                assert 0 <= attribution.relevance_score <= 1
```

## Performance Testing

### Benchmarking CoT Performance

```python
import pytest
import time
import asyncio
from typing import List, Dict, Any
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput

@pytest.mark.performance
class TestCotPerformance:
    """Performance benchmarks for CoT system."""

    @pytest.fixture
    def performance_service(self, test_settings):
        return ChainOfThoughtService(settings=test_settings)

    def generate_test_questions(self) -> List[Dict[str, Any]]:
        """Generate test questions of varying complexity."""
        return [
            {
                "question": "What is machine learning?",
                "expected_complexity": "simple",
                "expected_steps": 1
            },
            {
                "question": "Compare supervised and unsupervised learning approaches",
                "expected_complexity": "comparison",
                "expected_steps": 3
            },
            {
                "question": "Why do neural networks sometimes fail to converge during training, and how can regularization techniques like dropout and batch normalization help address these issues?",
                "expected_complexity": "causal",
                "expected_steps": 4
            },
            {
                "question": "Analyze the trade-offs between accuracy, interpretability, computational efficiency, and scalability across different machine learning paradigms including traditional statistical methods, ensemble methods, deep learning approaches, and reinforcement learning systems.",
                "expected_complexity": "complex_analytical",
                "expected_steps": 5
            }
        ]

    @pytest.mark.asyncio
    async def test_classification_performance(self, performance_service):
        """Test question classification performance."""
        questions = self.generate_test_questions()

        # Warm up
        await performance_service.classify_question("Warm up question")

        # Benchmark classification speed
        start_time = time.time()
        classifications = []

        for test_case in questions:
            classification = await performance_service.classify_question(test_case["question"])
            classifications.append(classification)

        classification_time = time.time() - start_time

        # Performance assertions
        assert classification_time < 1.0  # Should be very fast
        avg_time_per_classification = classification_time / len(questions)
        assert avg_time_per_classification < 0.1  # < 100ms per classification

        # Accuracy assertions
        for i, classification in enumerate(classifications):
            expected = questions[i]
            if expected["expected_complexity"] != "simple":
                assert classification.requires_cot
            assert classification.estimated_steps >= expected["expected_steps"] or classification.estimated_steps == 1

    @pytest.mark.asyncio
    async def test_concurrent_cot_execution(self, performance_service):
        """Test performance under concurrent load."""
        questions = [
            "Compare A and B",
            "Why does X cause Y?",
            "What is the relationship between P and Q?",
            "How do systems M and N differ in their approach to problem Z?"
        ]

        # Create concurrent CoT inputs
        cot_inputs = [
            ChainOfThoughtInput(
                question=q,
                collection_id=uuid4(),
                user_id=uuid4(),
                cot_config={"max_reasoning_depth": 2}  # Keep it fast for performance testing
            )
            for q in questions
        ]

        # Execute concurrently
        start_time = time.time()
        results = await asyncio.gather(*[
            performance_service.execute_chain_of_thought(cot_input)
            for cot_input in cot_inputs
        ])
        total_time = time.time() - start_time

        # Performance assertions
        assert total_time < 30.0  # Should complete within 30 seconds
        assert len(results) == len(questions)

        # Quality assertions
        for result in results:
            assert result.final_answer is not None
            assert result.total_confidence > 0.3
            assert len(result.reasoning_steps) > 0

    @pytest.mark.asyncio
    async def test_memory_usage_during_cot(self, performance_service):
        """Test memory usage patterns during CoT execution."""
        import psutil
        import os

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Execute memory-intensive CoT
        large_context = ["Large context document " * 100] * 50  # ~50KB of context

        cot_input = ChainOfThoughtInput(
            question="Analyze this complex scenario with multiple factors and interdependencies",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={"max_reasoning_depth": 5}
        )

        result = await performance_service.execute_chain_of_thought(
            cot_input,
            context_documents=large_context
        )

        # Check peak memory usage
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        # Memory usage should be reasonable
        assert memory_increase < 500  # Less than 500MB increase
        assert result.final_answer is not None

    def test_token_usage_estimation_accuracy(self, performance_service):
        """Test accuracy of token usage estimation."""
        # This would require integration with real LLM services
        # to compare estimated vs actual token usage
        pass

@pytest.mark.benchmark
class TestCotBenchmarks:
    """Benchmark tests for CoT system optimization."""

    def test_reasoning_step_execution_benchmark(self, benchmark, performance_service):
        """Benchmark single reasoning step execution."""
        async def execute_step():
            return await performance_service.execute_reasoning_step(
                step_number=1,
                question="What is machine learning?",
                context=["Machine learning context"],
                previous_answers=[]
            )

        # Run benchmark
        result = benchmark(asyncio.run, execute_step())

        assert result.step_number == 1
        assert result.confidence_score > 0
```

## Test Data and Fixtures

### Test Data Management

```python
# tests/fixtures/cot_test_data.py
from uuid import uuid4
from typing import Dict, Any, List
from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput

class CotTestDataFactory:
    """Factory for creating test data for CoT system."""

    @staticmethod
    def create_simple_question_input(**kwargs) -> ChainOfThoughtInput:
        """Create input for simple questions."""
        defaults = {
            "question": "What is artificial intelligence?",
            "collection_id": uuid4(),
            "user_id": uuid4()
        }
        defaults.update(kwargs)
        return ChainOfThoughtInput(**defaults)

    @staticmethod
    def create_comparison_question_input(**kwargs) -> ChainOfThoughtInput:
        """Create input for comparison questions."""
        defaults = {
            "question": "Compare supervised and unsupervised learning",
            "collection_id": uuid4(),
            "user_id": uuid4(),
            "cot_config": {
                "reasoning_strategy": "decomposition",
                "max_reasoning_depth": 3
            }
        }
        defaults.update(kwargs)
        return ChainOfThoughtInput(**defaults)

    @staticmethod
    def create_causal_question_input(**kwargs) -> ChainOfThoughtInput:
        """Create input for causal questions."""
        defaults = {
            "question": "Why do neural networks overfit?",
            "collection_id": uuid4(),
            "user_id": uuid4(),
            "cot_config": {
                "reasoning_strategy": "causal",
                "max_reasoning_depth": 4
            }
        }
        defaults.update(kwargs)
        return ChainOfThoughtInput(**defaults)

    @staticmethod
    def create_test_context_documents() -> List[str]:
        """Create sample context documents for testing."""
        return [
            "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.",
            "Supervised learning uses labeled training data to learn a mapping from inputs to outputs.",
            "Unsupervised learning finds hidden patterns in data without labeled examples.",
            "Deep learning uses neural networks with multiple layers to learn complex representations.",
            "Overfitting occurs when a model learns the training data too well and fails to generalize."
        ]

# tests/fixtures/mock_services.py
from unittest.mock import AsyncMock, Mock
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService

class MockLLMService:
    """Mock LLM service for testing."""

    def __init__(self, responses=None, should_fail=False):
        self.responses = responses or ["Mock LLM response"]
        self.should_fail = should_fail
        self.call_count = 0

    async def generate_response(self, question, context):
        if self.should_fail:
            from core.custom_exceptions import LLMProviderError
            raise LLMProviderError(
                provider="mock",
                error_type="api_error",
                message="Mock LLM failure"
            )

        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response

def create_mock_cot_service(**kwargs):
    """Create a mock CoT service for testing."""
    mock_settings = Mock()
    mock_settings.cot_max_reasoning_depth = kwargs.get('max_depth', 3)
    mock_settings.cot_reasoning_strategy = kwargs.get('strategy', 'decomposition')
    mock_settings.cot_token_budget_multiplier = kwargs.get('token_multiplier', 2.0)

    mock_llm = MockLLMService(
        responses=kwargs.get('llm_responses'),
        should_fail=kwargs.get('llm_should_fail', False)
    )

    return ChainOfThoughtService(
        settings=mock_settings,
        llm_service=mock_llm
    )
```

### Pytest Configuration

```python
# tests/conftest.py
import pytest
import asyncio
from typing import Generator
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from tests.fixtures.cot_test_data import CotTestDataFactory
from tests.fixtures.mock_services import create_mock_cot_service

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def cot_test_data_factory():
    """Provide test data factory."""
    return CotTestDataFactory()

@pytest.fixture
def mock_cot_service():
    """Provide mock CoT service."""
    return create_mock_cot_service()

@pytest.fixture
def mock_cot_service_with_failures():
    """Provide mock CoT service that simulates failures."""
    return create_mock_cot_service(llm_should_fail=True)

@pytest.fixture
def sample_context_documents():
    """Provide sample context documents."""
    return CotTestDataFactory.create_test_context_documents()

# Markers for different test types
pytest_plugins = ["pytest_asyncio"]

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "benchmark: Benchmark tests")
```

## Running Tests

### Test Execution Commands

```bash
# Run all CoT tests
poetry run pytest tests/ -k "cot" -v

# Run unit tests only
poetry run pytest tests/unit/ -m unit -v

# Run integration tests (requires real services)
poetry run pytest tests/integration/ -m integration -v

# Run performance tests
poetry run pytest tests/ -m performance -v --tb=short

# Run with coverage
poetry run pytest tests/ --cov=rag_solution.services.chain_of_thought_service --cov-report=html

# Run benchmarks
poetry run pytest tests/ -m benchmark --benchmark-only

# Parallel test execution
poetry run pytest tests/ -n auto  # Requires pytest-xdist
```

### Continuous Integration

```yaml
# .github/workflows/cot-tests.yml
name: CoT Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        cd backend
        pip install poetry
        poetry install --with dev,test

    - name: Run unit tests
      run: |
        cd backend
        poetry run pytest tests/unit/ -m unit --cov=rag_solution

    - name: Run integration tests
      run: |
        cd backend
        poetry run pytest tests/integration/ -m integration
      env:
        TEST_MODE: true
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
```

This comprehensive testing strategy ensures the CoT system is robust, performant, and reliable across different scenarios and configurations.