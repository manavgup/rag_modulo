"""Performance benchmarks for WatsonX provider."""

import pytest
import time
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from uuid import UUID

from rag_solution.generation.providers.watsonx import WatsonXLLM
from rag_solution.services.user_service import UserService
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from rag_solution.schemas.user_schema import UserInput
from core.config import settings

# Skip benchmarks if WatsonX credentials are not configured
pytestmark = pytest.mark.skipif(
    not settings.wx_api_key or not settings.wx_url or not settings.wx_project_id,
    reason="WatsonX credentials not configured"
)

# Benchmark configuration
BENCHMARK_CONFIG = {
    "iterations": 5,  # Number of times to run each benchmark
    "text_sizes": {
        "small": 100,
        "medium": 500,
        "large": 1000
    },
    "batch_sizes": [1, 5, 10],
    "results_file": "benchmark_results.json"
}

@pytest.fixture
def test_user(db_session):
    """Create test user."""
    user_service = UserService(db_session)
    user = user_service.create_user(UserInput(
        ibm_id="test_ibm_id",
        email="test@example.com",
        name="Test User"
    ))
    return user

@pytest.fixture
def watsonx_provider(provider_config_service):
    """Fixture to initialize WatsonXProvider with actual settings."""
    provider = WatsonXLLM(provider_config_service)
    provider.initialize_client()
    yield provider
    provider.close()

@pytest.fixture
def test_parameters(test_user):
    """Fixture for test model parameters."""
    return LLMParametersInput(
        name="test_params",
        user_id=test_user.id,
        provider="watsonx",
        max_new_tokens=100,
        min_new_tokens=1,
        temperature=0.7,
        top_k=50,
        top_p=0.95,
        is_default=True
    )

@pytest.fixture
def test_template():
    """Fixture for test prompt template."""
    return PromptTemplateInput(
        name="test_template",
        provider="watsonx",
        description="Test RAG template for benchmarking",
        template_type=PromptTemplateType.RAG_QUERY,
        system_prompt="You are a helpful AI assistant.",
        template_format="{context}\n\n{question}",
        input_variables={"context": "str", "question": "str"},
        validation_schema={
            "model": "PromptVariables",
            "fields": {
                "context": {"type": "str", "min_length": 1},
                "question": {"type": "str", "min_length": 1}
            },
            "required": ["context", "question"]
        },
        example_inputs={
            "context": "Python was created by Guido van Rossum.",
            "question": "Who created Python?"
        },
        is_default=True
    )

class BenchmarkResults:
    """Class to manage benchmark results and historical data."""

    def __init__(self, results_file: str):
        self.results_file = Path(results_file)
        self.current_results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": {}
        }
        self.historical_results: List[Dict[str, Any]] = self._load_historical_results()

    def _load_historical_results(self) -> List[Dict[str, Any]]:
        """Load historical benchmark results."""
        if self.results_file.exists():
            with open(self.results_file) as f:
                return json.load(f)
        return []

    def add_result(self, benchmark_name: str, metrics: Dict[str, Any], user_id: UUID = None) -> None:
        """Add a benchmark result."""
        result = {
            "metrics": metrics,
            "user_id": str(user_id) if user_id else None
        }
        self.current_results["benchmarks"][benchmark_name] = result

    def save_results(self) -> None:
        """Save current results and update historical data."""
        self.historical_results.append(self.current_results)
        with open(self.results_file, 'w') as f:
            json.dump(self.historical_results, f, indent=2)

    def get_historical_metrics(self, benchmark_name: str, metric: str, user_id: UUID = None) -> List[float]:
        """Get historical values for a specific metric."""
        return [
            result["benchmarks"][benchmark_name]["metrics"][metric]
            for result in self.historical_results
            if benchmark_name in result["benchmarks"]
            and (user_id is None or result["benchmarks"][benchmark_name].get("user_id") == str(user_id))
        ]

class PerformanceMetrics:
    """Class to calculate and store performance metrics."""

    def __init__(self):
        self.latencies: List[float] = []
        self.throughputs: List[float] = []
        self.error_rates: List[float] = []
        self.token_rates: List[float] = []

    def add_measurement(
        self,
        latency: float,
        throughput: float,
        error_rate: float,
        token_rate: float
    ) -> None:
        """Add a performance measurement."""
        self.latencies.append(latency)
        self.throughputs.append(throughput)
        self.error_rates.append(error_rate)
        self.token_rates.append(token_rate)

    def get_metrics(self) -> Dict[str, Any]:
        """Calculate aggregate metrics."""
        return {
            "latency": {
                "mean": statistics.mean(self.latencies),
                "median": statistics.median(self.latencies),
                "std_dev": statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0,
                "p95": self._percentile(self.latencies, 95),
                "p99": self._percentile(self.latencies, 99)
            },
            "throughput": {
                "mean": statistics.mean(self.throughputs),
                "peak": max(self.throughputs)
            },
            "error_rate": {
                "mean": statistics.mean(self.error_rates),
                "max": max(self.error_rates)
            },
            "token_rate": {
                "mean": statistics.mean(self.token_rates),
                "peak": max(self.token_rates)
            }
        }

    @staticmethod
    def _percentile(values: List[float], p: float) -> float:
        """Calculate percentile value."""
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (p / 100)
        f = int(k)
        c = k - f
        if f + 1 < len(sorted_values):
            return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c
        return sorted_values[f]

def generate_test_text(size: int) -> str:
    """Generate test text of specified size."""
    base_text = "The quick brown fox jumps over the lazy dog. "
    return (base_text * (size // len(base_text) + 1))[:size]

@pytest.mark.benchmark
def test_text_generation_performance(
    watsonx_provider,
    test_parameters,
    test_template,
    test_user
):
    """Benchmark text generation performance."""
    results = BenchmarkResults(BENCHMARK_CONFIG["results_file"])
    metrics = PerformanceMetrics()

    for _ in range(BENCHMARK_CONFIG["iterations"]):
        for size_name, size in BENCHMARK_CONFIG["text_sizes"].items():
            prompt = generate_test_text(size)
            
            start_time = time.time()
            errors = 0
            tokens = 0
            
            try:
                response = watsonx_provider.generate_text(
                    prompt=prompt,
                    model_parameters=test_parameters,
                    template=test_template,
                    variables={
                        "context": prompt,
                        "question": "What is this text about?"
                    }
                )
                tokens = len(response.split())
            except Exception:
                errors += 1

            end_time = time.time()
            duration = end_time - start_time
            
            metrics.add_measurement(
                latency=duration,
                throughput=size / duration,
                error_rate=errors,
                token_rate=tokens / duration if tokens > 0 else 0
            )

    results.add_result(
        f"text_generation_{size_name}",
        metrics.get_metrics(),
        test_user.id
    )
    results.save_results()

@pytest.mark.benchmark
def test_multiple_users_performance(
    watsonx_provider,
    test_parameters,
    test_template,
    test_user,
    db_session
):
    """Benchmark performance across multiple users."""
    # Create second user with different parameters
    user_service = UserService(db_session)
    user2 = user_service.create_user(UserInput(
        ibm_id="test_ibm_id_2",
        email="test2@example.com",
        name="Test User 2"
    ))

    # Create parameters for second user
    params2 = LLMParametersInput(
        name="test_params_2",
        user_id=user2.id,
        provider="watsonx",
        max_new_tokens=50,  # Different from first user
        temperature=0.9,    # Different from first user
        top_k=50,
        top_p=0.95,
        is_default=True
    )

    # Create template for second user
    template2 = PromptTemplateInput(
        name="test_template_2",
        provider="watsonx",
        description="Test RAG template for second user",
        template_type=PromptTemplateType.RAG_QUERY,
        system_prompt="You are a concise AI assistant.",  # Different from first user
        template_format="{context}\n\nQ: {question}",  # Different format
        input_variables={"context": "str", "question": "str"},
        validation_schema={
            "model": "PromptVariables",
            "fields": {
                "context": {"type": "str", "min_length": 1},
                "question": {"type": "str", "min_length": 1}
            },
            "required": ["context", "question"]
        },
        example_inputs={
            "context": "Python supports multiple programming paradigms.",
            "question": "What programming paradigms does Python support?"
        },
        is_default=True
    )

    results = BenchmarkResults(BENCHMARK_CONFIG["results_file"])
    metrics1 = PerformanceMetrics()
    metrics2 = PerformanceMetrics()

    for _ in range(BENCHMARK_CONFIG["iterations"]):
        prompt = generate_test_text(BENCHMARK_CONFIG["text_sizes"]["medium"])

        # Test first user
        start_time = time.time()
        errors = 0
        tokens = 0

        try:
            response = watsonx_provider.generate_text(
                prompt=prompt,
                model_parameters=test_parameters,
                template=test_template,
                variables={
                    "context": prompt,
                    "question": "What is this text about?"
                }
            )
            tokens = len(response.split())
        except Exception:
            errors += 1

        end_time = time.time()
        duration = end_time - start_time

        metrics1.add_measurement(
            latency=duration,
            throughput=len(prompt) / duration,
            error_rate=errors,
            token_rate=tokens / duration if tokens > 0 else 0
        )

        # Test second user
        start_time = time.time()
        errors = 0
        tokens = 0

        try:
            response = watsonx_provider.generate_text(
                prompt=prompt,
                model_parameters=params2,
                template=template2,
                variables={
                    "context": prompt,
                    "question": "What is this text about?"
                }
            )
            tokens = len(response.split())
        except Exception:
            errors += 1

        end_time = time.time()
        duration = end_time - start_time

        metrics2.add_measurement(
            latency=duration,
            throughput=len(prompt) / duration,
            error_rate=errors,
            token_rate=tokens / duration if tokens > 0 else 0
        )

    results.add_result("user1_performance", metrics1.get_metrics(), test_user.id)
    results.add_result("user2_performance", metrics2.get_metrics(), user2.id)
    results.save_results()

@pytest.mark.benchmark
def test_streaming_performance(
    watsonx_provider,
    test_parameters,
    test_template,
    test_user
):
    """Benchmark streaming performance."""
    results = BenchmarkResults(BENCHMARK_CONFIG["results_file"])
    metrics = PerformanceMetrics()

    for _ in range(BENCHMARK_CONFIG["iterations"]):
        prompt = generate_test_text(BENCHMARK_CONFIG["text_sizes"]["medium"])
        
        start_time = time.time()
        chunk_count = 0
        total_tokens = 0
        errors = 0
        
        try:
            for chunk in watsonx_provider.generate_text_stream(
                prompt=prompt,
                model_parameters=test_parameters,
                template=test_template,
                variables={
                    "context": prompt,
                    "question": "What is this text about?"
                }
            ):
                chunk_count += 1
                total_tokens += len(chunk.split())
        except Exception:
            errors += 1

        end_time = time.time()
        duration = end_time - start_time
        
        metrics.add_measurement(
            latency=duration / chunk_count if chunk_count > 0 else duration,
            throughput=chunk_count / duration if chunk_count > 0 else 0,
            error_rate=errors,
            token_rate=total_tokens / duration if total_tokens > 0 else 0
        )

    results.add_result("streaming", metrics.get_metrics(), test_user.id)
    results.save_results()

@pytest.mark.benchmark
def test_embedding_performance(watsonx_provider, test_user):
    """Benchmark embedding generation performance."""
    results = BenchmarkResults(BENCHMARK_CONFIG["results_file"])
    
    for size_name, size in BENCHMARK_CONFIG["text_sizes"].items():
        metrics = PerformanceMetrics()
        
        for _ in range(BENCHMARK_CONFIG["iterations"]):
            text = generate_test_text(size)
            
            start_time = time.time()
            errors = 0
            embedding_size = 0
            
            try:
                embeddings = watsonx_provider.get_embeddings(text)
                embedding_size = len(embeddings[0])
            except Exception:
                errors += 1

            end_time = time.time()
            duration = end_time - start_time
            
            metrics.add_measurement(
                latency=duration,
                throughput=size / duration,
                error_rate=errors,
                token_rate=embedding_size / duration if embedding_size > 0 else 0
            )

        results.add_result(
            f"embedding_{size_name}",
            metrics.get_metrics(),
            test_user.id
        )
        results.save_results()

@pytest.mark.benchmark
def test_concurrent_performance(
    watsonx_provider,
    test_parameters,
    test_template,
    test_user
):
    """Benchmark concurrent request performance."""
    import asyncio
    results = BenchmarkResults(BENCHMARK_CONFIG["results_file"])
    metrics = PerformanceMetrics()

    async def generate_text(prompt: str) -> str:
        return watsonx_provider.generate_text(
            prompt=prompt,
            model_parameters=test_parameters,
            template=test_template,
            variables={
                "context": prompt,
                "question": "What is this text about?"
            }
        )

    for _ in range(BENCHMARK_CONFIG["iterations"]):
        for concurrency in [2, 4, 8]:
            prompts = [
                generate_test_text(BENCHMARK_CONFIG["text_sizes"]["small"])
                for _ in range(concurrency)
            ]
            
            start_time = time.time()
            errors = 0
            total_tokens = 0
            
            async def run_concurrent():
                tasks = [generate_text(prompt) for prompt in prompts]
                return await asyncio.gather(*tasks, return_exceptions=True)
            
            try:
                responses = asyncio.run(run_concurrent())
                total_tokens = sum(
                    len(r.split()) for r in responses 
                    if isinstance(r, str)
                )
                errors = sum(1 for r in responses if isinstance(r, Exception))
            except Exception:
                errors += 1

            end_time = time.time()
            duration = end_time - start_time
            
            metrics.add_measurement(
                latency=duration / concurrency,
                throughput=concurrency / duration,
                error_rate=errors / concurrency,
                token_rate=total_tokens / duration if total_tokens > 0 else 0
            )

        results.add_result(
            f"concurrent_{concurrency}",
            metrics.get_metrics(),
            test_user.id
        )
        results.save_results()

def test_analyze_performance_trends(test_user):
    """Analyze performance trends from historical benchmark data."""
    results = BenchmarkResults(BENCHMARK_CONFIG["results_file"])
    
    # Analyze trends for each benchmark
    for benchmark in results.current_results["benchmarks"]:
        latencies = results.get_historical_metrics(
            benchmark,
            "latency",
            test_user.id
        )
        throughputs = results.get_historical_metrics(
            benchmark,
            "throughput",
            test_user.id
        )
        
        if len(latencies) > 1:
            # Calculate trend indicators
            latency_trend = (latencies[-1]["mean"] - latencies[0]["mean"]) / latencies[0]["mean"]
            throughput_trend = (throughputs[-1]["mean"] - throughputs[0]["mean"]) / throughputs[0]["mean"]
            
            # Report significant changes
            if abs(latency_trend) > 0.1:  # More than 10% change
                print(f"Performance change detected in {benchmark}:")
                print(f"  Latency: {latency_trend:+.1%} change")
            
            if abs(throughput_trend) > 0.1:
                print(f"  Throughput: {throughput_trend:+.1%} change")
