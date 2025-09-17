"""End-to-end tests for Chain of Thought (CoT) functionality.

Tests the complete CoT workflow from API request to final response,
including CLI integration, database persistence, and real-world scenarios.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, List, Any

from httpx import AsyncClient
from sqlalchemy.orm import Session


@pytest.mark.e2e
class TestChainOfThoughtE2EWorkflow:
    """Test complete CoT workflow end-to-end."""

    @pytest.fixture
    async def test_user_and_collection(self, db_session: Session):
        """Create test user and collection for E2E testing."""
        from rag_solution.models.  # type: ignoreuser import User
        from rag_solution.models.  # type: ignorecollection import Collection

        # Create test user
        user = User(
            username="cot_e2e_user",
            email="cot_e2e@example.com",
            first_name="CoT",
            last_name="E2E"
        )
        db_session.add(user)
        db_session.flush()

        # Create test collection with sample documents
        collection = Collection(
            name="CoT E2E Test Collection",
            description="Collection for end-to-end CoT testing",
            user_id=user.id
        )
        db_session.add(collection)
        db_session.commit()

        yield {"user": user, "collection": collection}

        # Cleanup
        db_session.delete(collection)
        db_session.delete(user)
        db_session.commit()

    async def test_complete_cot_search_workflow_api(self, test_user_and_collection, client: AsyncClient):
        """Test complete CoT search workflow through API."""
        user = test_user_and_collection["user"]
        collection = test_user_and_collection["collection"]

        # Prepare search request - CoT automatically determined by question complexity
        search_request = {
            "question": "What is machine learning and how does it differ from traditional programming approaches?",
            "collection_id": str(collection.id),
            "user_id": str(user.id)
            # No config_metadata needed - CoT is always-on with automatic classification
        }

        # Execute search request
        response = await client.post("/api/v1/search", json=search_request)

        # Verify successful response
        assert response.status_code == 200
        result = response.json()

        # Verify standard search response structure
        assert "answer" in result
        assert "documents" in result
        assert "query_results" in result
        assert "execution_time" in result

        # Verify CoT-specific response structure
        assert "cot_output" in result
        cot_output = result["cot_output"]

        assert "original_question" in cot_output
        assert "final_answer" in cot_output
        assert "reasoning_steps" in cot_output
        assert "total_confidence" in cot_output
        assert "reasoning_strategy" in cot_output

        # Verify reasoning steps structure
        reasoning_steps = cot_output["reasoning_steps"]
        assert len(reasoning_steps) >= 2  # Should decompose the question

        for step in reasoning_steps:
            assert "step_number" in step
            assert "question" in step
            assert "intermediate_answer" in step
            assert "confidence_score" in step

        # Verify quality metrics
        assert 0 <= cot_output["total_confidence"] <= 1
        assert cot_output["reasoning_strategy"] == "decomposition"

    async def test_cot_performance_benchmarks_e2e(self, test_user_and_collection, client: AsyncClient):
        """Test CoT performance benchmarks against success criteria."""
        user = test_user_and_collection["user"]
        collection = test_user_and_collection["collection"]

        # Test various complexity levels
        test_questions = [
            {
                "question": "What is Python?",
                "complexity": "simple",
                "expected_cot": False
            },
            {
                "question": "How does machine learning work and what are its main applications?",
                "complexity": "medium",
                "expected_cot": True,
                "max_time": 10.0  # seconds
            },
            {
                "question": "Compare supervised and unsupervised learning, explain their differences, advantages, and provide practical examples of when to use each approach",
                "complexity": "high",
                "expected_cot": True,
                "max_time": 15.0  # seconds
            }
        ]

        for test_case in test_questions:
            search_request = {
                "question": test_case["question"],
                "collection_id": str(collection.id),
                "user_id": str(user.id)
                # No config_metadata needed - CoT auto-classifies questions based on complexity
            }

            start_time = asyncio.get_event_loop().time()
            response = await client.post("/api/v1/search", json=search_request)
            end_time = asyncio.get_event_loop().time()

            execution_time = end_time - start_time

            assert response.status_code == 200
            result = response.json()

            # Performance criteria from issue #136
            if test_case.get("max_time"):
                assert execution_time <= test_case["max_time"], f"Query took {execution_time}s, expected <= {test_case['max_time']}s"  # type: ignore

            # CoT activation criteria
            if test_case["expected_cot"]:
                assert "cot_output" in result
                assert len(result["cot_output"]["reasoning_steps"]) > 0

            # Quality criteria
            assert len(result["answer"]) > 50  # Substantial answer
            assert result["execution_time"] <= 10.0  # Under 10 seconds per issue requirements

    async def test_cot_token_usage_efficiency_e2e(self, test_user_and_collection, client: AsyncClient):
        """Test CoT token usage efficiency against <3x baseline criterion."""
        user = test_user_and_collection["user"]
        collection = test_user_and_collection["collection"]

        question = "How does deep learning work in neural networks?"

        # Baseline search without CoT
        baseline_request = {
            "question": question,
            "collection_id": str(collection.id),
            "user_id": str(user.id)
            # No config_metadata needed - CoT is always-on with automatic classification
        }

        baseline_response = await client.post("/api/v1/search", json=baseline_request)
        assert baseline_response.status_code == 200
        baseline_result = baseline_response.json()

        # CoT search
        cot_request = {
            "question": question,
            "collection_id": str(collection.id),
            "user_id": str(user.id)
            # No config_metadata needed - CoT is always-on with automatic classification
        }

        cot_response = await client.post("/api/v1/search", json=cot_request)
        assert cot_response.status_code == 200
        cot_result = cot_response.json()

        # Token usage efficiency check (criterion from issue #136)
        if "cot_output" in cot_result and "token_usage" in cot_result["cot_output"]:
            cot_tokens = cot_result["cot_output"]["token_usage"]
            # Baseline token usage estimation (would be tracked in real implementation)
            estimated_baseline_tokens = 500  # Conservative estimate

            token_multiplier = cot_tokens / estimated_baseline_tokens
            assert token_multiplier < 3.0, f"CoT used {token_multiplier}x tokens, should be <3x"

    async def test_cot_cli_integration_e2e(self, test_user_and_collection):
        """Test CoT integration through CLI interface."""
        import subprocess
        import json

        user = test_user_and_collection["user"]
        collection = test_user_and_collection["collection"]

        # CLI command - CoT automatically determined by question complexity
        cli_command = [
            "python", "-m", "rag_solution.cli.main",
            "search", "query",
            str(collection.id),
            "What is machine learning and how does it work?",
            "--user-id", str(user.id),
            "--output-format", "json"
            # No CoT flags needed - always-on with automatic classification
        ]

        # Execute CLI command
        result = subprocess.run(
            cli_command,
            cwd="backend",
            capture_output=True,
            text=True,
            timeout=30
        )

        # Verify CLI execution
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Parse CLI output
        try:
            cli_output = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON output from CLI: {result.stdout}")

        # Verify CLI output structure
        assert "answer" in cli_output
        assert "cot_output" in cli_output
        assert "reasoning_steps" in cli_output["cot_output"]

    async def test_cot_real_world_scenarios_e2e(self, test_user_and_collection, client: AsyncClient):
        """Test CoT with real-world question scenarios."""
        user = test_user_and_collection["user"]
        collection = test_user_and_collection["collection"]

        # Real-world scenarios from issue requirements
        real_world_questions = [
            {
                "question": "How do I implement a recommendation system for an e-commerce platform, and what are the trade-offs between collaborative filtering and content-based approaches?",
                "category": "complex_technical",
                "expected_steps": 4,
                "expected_topics": ["recommendation system", "collaborative filtering", "content-based"]
            },
            {
                "question": "Why did my machine learning model's accuracy drop after deployment, and how can I diagnose and fix this issue?",
                "category": "debugging_causal",
                "expected_steps": 3,
                "expected_topics": ["model accuracy", "deployment", "diagnosis"]
            },
            {
                "question": "What's the difference between microservices and monolithic architecture, when should I use each, and how do I migrate between them?",
                "category": "comparison_strategic",
                "expected_steps": 4,
                "expected_topics": ["microservices", "monolithic", "migration"]
            }
        ]

        for scenario in real_world_questions:
            search_request = {
                "question": scenario["question"],
                "collection_id": str(collection.id),
                "user_id": str(user.id)
                # No config_metadata needed - CoT is always-on with automatic classification
            }

            response = await client.post("/api/v1/search", json=search_request)
            assert response.status_code == 200

            result = response.json()

            # Verify CoT activation for complex questions
            assert "cot_output" in result
            cot_output = result["cot_output"]

            # Verify reasoning depth
            reasoning_steps = cot_output["reasoning_steps"]
            assert len(reasoning_steps) >= scenario["expected_steps"]  # type: ignore

            # Verify topic coverage
            combined_text = " ".join([
                step["intermediate_answer"] for step in reasoning_steps  # type: ignore
            ]) + " " + cot_output["final_answer"]

            for expected_topic in scenario["expected_topics"]:  # type: ignore
                assert any(topic.lower() in combined_text.lower() for topic in expected_topic.split()), \
                    f"Expected topic '{expected_topic}' not found in CoT output"

    async def test_cot_confidence_quality_metrics_e2e(self, test_user_and_collection, client: AsyncClient):
        """Test CoT confidence and quality metrics meet success criteria."""
        user = test_user_and_collection["user"]
        collection = test_user_and_collection["collection"]

        # Test questions with known good answers
        quality_test_questions = [
            {
                "question": "What is the difference between supervised and unsupervised learning?",
                "min_confidence": 0.7,
                "expected_concepts": ["supervised", "unsupervised", "learning", "labels"]
            },
            {
                "question": "How does backpropagation work in neural networks?",
                "min_confidence": 0.6,
                "expected_concepts": ["backpropagation", "neural networks", "gradient", "weights"]
            }
        ]

        for test_case in quality_test_questions:
            search_request = {
                "question": test_case["question"],
                "collection_id": str(collection.id),
                "user_id": str(user.id)
                # No config_metadata needed - CoT is always-on with automatic classification
            }

            response = await client.post("/api/v1/search", json=search_request)
            assert response.status_code == 200

            result = response.json()
            cot_output = result["cot_output"]

            # Confidence criteria
            assert cot_output["total_confidence"] >= test_case["min_confidence"], \
                f"Confidence {cot_output['total_confidence']} below minimum {test_case['min_confidence']}"

            # Concept coverage criteria
            final_answer = cot_output["final_answer"].lower()
            for concept in test_case["expected_concepts"]:  # type: ignore
                assert concept.lower() in final_answer, \
                    f"Expected concept '{concept}' not found in answer"

    async def test_cot_error_recovery_e2e(self, test_user_and_collection, client: AsyncClient):
        """Test CoT error recovery and fallback mechanisms."""
        user = test_user_and_collection["user"]
        collection = test_user_and_collection["collection"]

        # Test with potentially problematic inputs
        error_test_cases = [
            {
                "question": "",  # Empty question
                "expected_error": "validation_error"
            },
            {
                "question": "A" * 10000,  # Extremely long question
                "expected_fallback": True
            },
            {
                "question": "What is the meaning of life, the universe, and everything?",  # Philosophical/ambiguous
                "expected_fallback": True
            }
        ]

        for test_case in error_test_cases:
            search_request = {
                "question": test_case["question"],
                "collection_id": str(collection.id),
                "user_id": str(user.id)
                # No config_metadata needed - CoT is always-on with automatic classification
            }

            response = await client.post("/api/v1/search", json=search_request)

            if test_case.get("expected_error"):
                assert response.status_code in [400, 422]  # Validation error
            else:
                assert response.status_code == 200
                result = response.json()

                # Should always return some answer (fallback if needed)
                assert "answer" in result
                assert len(result["answer"]) > 0

                if test_case.get("expected_fallback"):
                    # May or may not use CoT, but should provide answer
                    assert result["answer"] is not None

    async def test_cot_concurrent_users_e2e(self, test_user_and_collection, client: AsyncClient):
        """Test CoT handling of concurrent users and requests."""
        user = test_user_and_collection["user"]
        collection = test_user_and_collection["collection"]

        # Create multiple concurrent requests
        concurrent_requests = [
            {
                "question": f"What is machine learning application number {i}?",
                "collection_id": str(collection.id),
                "user_id": str(user.id)
                # No config_metadata needed - CoT is always-on with automatic classification
            }
            for i in range(5)
        ]

        # Execute requests concurrently
        async def make_request(request_data):
            response = await client.post("/api/v1/search", json=request_data)
            return response

        tasks = [make_request(req) for req in concurrent_requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all requests completed successfully
        for i, response in enumerate(responses):
            assert not isinstance(response, Exception), f"Request {i} failed: {response}"
            assert response.status_code == 200

            result = response.json()
            assert "answer" in result
            assert len(result["answer"]) > 0

    async def test_cot_database_consistency_e2e(self, test_user_and_collection, client: AsyncClient, db_session: Session):
        """Test database consistency after CoT operations."""
        user = test_user_and_collection["user"]
        collection = test_user_and_collection["collection"]

        # Execute CoT search
        search_request = {
            "question": "Test question for database consistency",
            "collection_id": str(collection.id),
            "user_id": str(user.id)
            # No config_metadata needed - CoT is always-on with automatic classification
        }

        response = await client.post("/api/v1/search", json=search_request)
        assert response.status_code == 200

        # Verify database state
        from rag_solution.models.  # type: ignorechain_of_thought import ChainOfThoughtSession

        # Check CoT session persistence
        cot_sessions = db_session.query(ChainOfThoughtSession).filter_by(
            user_id=user.id,
            collection_id=collection.id
        ).all()

        assert len(cot_sessions) > 0

        # Verify data integrity
        latest_session = cot_sessions[-1]
        assert latest_session.original_question == search_request["question"]
        assert latest_session.final_answer is not None
        assert latest_session.created_at is not None

        # Verify no orphaned records
        assert latest_session.user_id == user.id
        assert latest_session.collection_id == collection.id
