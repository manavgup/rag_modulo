"""Performance tests for pipeline service."""

import pytest
import asyncio
import time
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import statistics
import psutil
import os

from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.search_service import SearchService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.collection_service import CollectionService
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.schemas.collection_schema import CollectionInput
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from core.config import settings

@pytest.fixture
def pipeline_setup(db_session: Session, test_user, test_collection):
    """Set up pipeline with services."""
    pipeline_service = PipelineService(db_session)
    search_service = SearchService(db_session)
    provider_service = LLMProviderService(db_session)
    parameters_service = LLMParametersService(db_session)
    template_service = PromptTemplateService(db_session)
    
    # Create user's default parameters
    parameters_input = LLMParametersInput(
        name="test-parameters",
        user_id=test_user.id,
        temperature=0.7,
        max_new_tokens=1000,
        top_k=50,
        top_p=0.95,
        is_default=True
    )
    parameters = parameters_service.create_or_update_parameters(test_user.id, parameters_input)
    
    # Create user's default templates
    templates = {}
    template_base = {
        "provider": "watsonx",
        "template_format": "{context}\n\n{question}",
        "input_variables": {"context": "str", "question": "str"},
        "validation_schema": {
            "model": "PromptVariables",
            "fields": {
                "context": {"type": "str", "min_length": 1},
                "question": {"type": "str", "min_length": 1}
            },
            "required": ["context", "question"]
        },
        "example_inputs": {
            "context": "Python was created by Guido van Rossum.",
            "question": "Who created Python?"
        },
        "is_default": True
    }

    for template_type in [PromptTemplateType.RAG_QUERY, PromptTemplateType.RESPONSE_EVALUATION]:
        template_input = PromptTemplateInput(
            name=f"test-{template_type.value}",
            description=f"Test template for {template_type.value}",
            template_type=template_type,
            **template_base
        )
        templates[template_type] = template_service.create_or_update_template(
            test_user.id,
            template_input
        )
    
    return {
        'pipeline_service': pipeline_service,
        'search_service': search_service,
        'provider_service': provider_service,
        'parameters_service': parameters_service,
        'template_service': template_service,
        'collection': test_collection,
        'user': test_user,
        'parameters': parameters,
        'templates': templates
    }

async def execute_search(search_service: SearchService, search_input: SearchInput, user_id: UUID) -> float:
    """Execute search and return execution time."""
    start_time = time.time()
    result = await search_service.search(search_input, user_id)
    execution_time = time.time() - start_time
    assert result is not None
    return execution_time

@pytest.mark.performance
@pytest.mark.asyncio
async def test_pipeline_throughput(pipeline_setup):
    """Test pipeline throughput under load."""
    # Configure test parameters
    num_requests = 50
    concurrent_requests = 10
    
    # Create search inputs
    search_inputs = [
        SearchInput(
            question=f"Test query {i}",
            collection_id=pipeline_setup['collection'].id,
            pipeline_id=UUID("87654321-4321-8765-4321-876543210987")
        )
        for i in range(num_requests)
    ]
    
    # Execute searches in batches
    execution_times = []
    for i in range(0, num_requests, concurrent_requests):
        batch = search_inputs[i:i + concurrent_requests]
        batch_times = await asyncio.gather(*[
            execute_search(
                pipeline_setup['search_service'],
                search_input,
                pipeline_setup['user'].id
            )
            for search_input in batch
        ])
        execution_times.extend(batch_times)
    
    # Calculate metrics
    avg_time = statistics.mean(execution_times)
    p95_time = statistics.quantiles(execution_times, n=20)[18]  # 95th percentile
    throughput = num_requests / sum(execution_times)
    
    # Log results
    print(f"\nPipeline Performance Metrics:")
    print(f"Total Requests: {num_requests}")
    print(f"Concurrent Requests: {concurrent_requests}")
    print(f"Average Response Time: {avg_time:.2f}s")
    print(f"95th Percentile Response Time: {p95_time:.2f}s")
    print(f"Throughput: {throughput:.2f} requests/second")
    
    # Assert performance requirements
    assert avg_time < 5.0, f"Average response time {avg_time:.2f}s exceeds 5.0s limit"
    assert p95_time < 10.0, f"95th percentile response time {p95_time:.2f}s exceeds 10.0s limit"
    assert throughput > 1.0, f"Throughput {throughput:.2f} req/s below 1.0 req/s minimum"

@pytest.mark.performance
@pytest.mark.asyncio
async def test_pipeline_latency(pipeline_setup):
    """Test pipeline latency under different loads."""
    # Test scenarios
    scenarios = [
        {"name": "Light Load", "concurrent": 1, "requests": 10},
        {"name": "Medium Load", "concurrent": 5, "requests": 20},
        {"name": "Heavy Load", "concurrent": 10, "requests": 30}
    ]
    
    for scenario in scenarios:
        # Create search inputs
        search_inputs = [
            SearchInput(
                question=f"Test query {i}",
                collection_id=pipeline_setup['collection'].id,
                pipeline_id=UUID("87654321-4321-8765-4321-876543210987")
            )
            for i in range(scenario['requests'])
        ]
        
        # Execute searches
        execution_times = []
        for i in range(0, scenario['requests'], scenario['concurrent']):
            batch = search_inputs[i:i + scenario['concurrent']]
            batch_times = await asyncio.gather(*[
                execute_search(
                    pipeline_setup['search_service'],
                    search_input,
                    pipeline_setup['user'].id
                )
                for search_input in batch
            ])
            execution_times.extend(batch_times)
        
        # Calculate metrics
        avg_time = statistics.mean(execution_times)
        p95_time = statistics.quantiles(execution_times, n=20)[18]
        
        # Log results
        print(f"\n{scenario['name']} Performance Metrics:")
        print(f"Concurrent Requests: {scenario['concurrent']}")
        print(f"Total Requests: {scenario['requests']}")
        print(f"Average Response Time: {avg_time:.2f}s")
        print(f"95th Percentile Response Time: {p95_time:.2f}s")
        
        # Assert latency requirements
        max_avg_time = 3.0 if scenario['name'] == "Light Load" else 5.0
        assert avg_time < max_avg_time, f"{scenario['name']}: Average response time {avg_time:.2f}s exceeds {max_avg_time}s limit"

@pytest.mark.performance
@pytest.mark.asyncio
async def test_pipeline_resource_usage(pipeline_setup):
    """Test pipeline resource usage under load."""
    def get_process_metrics():
        process = psutil.Process(os.getpid())
        return {
            'cpu_percent': process.cpu_percent(),
            'memory_percent': process.memory_percent(),
            'num_threads': process.num_threads()
        }
    
    # Configure test
    num_requests = 30
    concurrent_requests = 5
    
    # Create search inputs
    search_inputs = [
        SearchInput(
            question=f"Test query {i}",
            collection_id=pipeline_setup['collection'].id,
            pipeline_id=UUID("87654321-4321-8765-4321-876543210987")
        )
        for i in range(num_requests)
    ]
    
    # Measure baseline
    baseline_metrics = get_process_metrics()
    
    # Execute searches and monitor resources
    metrics_samples = []
    for i in range(0, num_requests, concurrent_requests):
        batch = search_inputs[i:i + concurrent_requests]
        
        # Start monitoring
        start_metrics = get_process_metrics()
        metrics_samples.append(start_metrics)
        
        # Execute batch
        await asyncio.gather(*[
            execute_search(
                pipeline_setup['search_service'],
                search_input,
                pipeline_setup['user'].id
            )
            for search_input in batch
        ])
        
        # Record metrics
        end_metrics = get_process_metrics()
        metrics_samples.append(end_metrics)
    
    # Calculate average resource usage
    avg_cpu = statistics.mean(sample['cpu_percent'] for sample in metrics_samples)
    avg_memory = statistics.mean(sample['memory_percent'] for sample in metrics_samples)
    max_threads = max(sample['num_threads'] for sample in metrics_samples)
    
    # Log results
    print(f"\nResource Usage Metrics:")
    print(f"Average CPU Usage: {avg_cpu:.1f}%")
    print(f"Average Memory Usage: {avg_memory:.1f}%")
    print(f"Maximum Thread Count: {max_threads}")
    
    # Assert resource limits
    assert avg_cpu < 80.0, f"Average CPU usage {avg_cpu:.1f}% exceeds 80% limit"
    assert avg_memory < 80.0, f"Average memory usage {avg_memory:.1f}% exceeds 80% limit"
    assert max_threads < 100, f"Maximum thread count {max_threads} exceeds 100 limit"

@pytest.mark.performance
@pytest.mark.asyncio
async def test_pipeline_stability(pipeline_setup):
    """Test pipeline stability over extended period."""
    # Configure test
    duration_seconds = 300  # 5 minutes
    request_interval = 1.0  # 1 request per second
    
    start_time = time.time()
    success_count = 0
    error_count = 0
    response_times = []
    
    while time.time() - start_time < duration_seconds:
        try:
            # Execute search
            search_input = SearchInput(
                question="Stability test query",
                collection_id=pipeline_setup['collection'].id,
                pipeline_id=UUID("87654321-4321-8765-4321-876543210987")
            )
            
            execution_time = await execute_search(
                pipeline_setup['search_service'],
                search_input,
                pipeline_setup['user'].id
            )
            
            success_count += 1
            response_times.append(execution_time)
            
        except Exception as e:
            error_count += 1
            print(f"Error during stability test: {str(e)}")
        
        # Wait for next interval
        await asyncio.sleep(request_interval)
    
    # Calculate metrics
    total_requests = success_count + error_count
    success_rate = (success_count / total_requests) * 100
    avg_time = statistics.mean(response_times)
    
    # Log results
    print(f"\nStability Test Results:")
    print(f"Duration: {duration_seconds} seconds")
    print(f"Total Requests: {total_requests}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Average Response Time: {avg_time:.2f}s")
    
    # Assert stability requirements
    assert success_rate > 99.0, f"Success rate {success_rate:.1f}% below 99% requirement"
    assert avg_time < 5.0, f"Average response time {avg_time:.2f}s exceeds 5.0s limit"

@pytest.mark.performance
@pytest.mark.asyncio
async def test_user_parameter_switching(pipeline_setup):
    """Test performance impact of switching user parameters."""
    # Create alternate parameters
    alt_params = pipeline_setup['parameters_service'].create_or_update_parameters(
        pipeline_setup['user'].id,
        LLMParametersInput(
            name="alternate-parameters",
            user_id=pipeline_setup['user'].id,
            temperature=0.9,
            max_new_tokens=500,
            top_k=30,
            top_p=0.8,
            is_default=False
        )
    )
    
    # Test search with parameter switching
    search_input = SearchInput(
        question="Parameter switching test",
        collection_id=pipeline_setup['collection'].id,
        pipeline_id=UUID("87654321-4321-8765-4321-876543210987")
    )
    
    execution_times = []
    for _ in range(10):
        # Switch default parameters
        pipeline_setup['parameters_service'].create_or_update_parameters(
            pipeline_setup['user'].id,
            LLMParametersInput(
                name=alt_params.name,
                user_id=pipeline_setup['user'].id,
                temperature=alt_params.temperature,
                max_new_tokens=alt_params.max_new_tokens,
                top_k=alt_params.top_k,
                top_p=alt_params.top_p,
                is_default=True
            )
        )
        
        # Execute search
        execution_time = await execute_search(
            pipeline_setup['search_service'],
            search_input,
            pipeline_setup['user'].id
        )
        execution_times.append(execution_time)
    
    # Calculate metrics
    avg_time = statistics.mean(execution_times)
    max_time = max(execution_times)
    
    # Log results
    print(f"\nParameter Switching Performance:")
    print(f"Average Response Time: {avg_time:.2f}s")
    print(f"Maximum Response Time: {max_time:.2f}s")
    
    # Assert performance requirements
    assert avg_time < 5.0, f"Average response time {avg_time:.2f}s exceeds 5.0s limit"
    assert max_time < 10.0, f"Maximum response time {max_time:.2f}s exceeds 10.0s limit"
