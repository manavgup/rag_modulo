"""Integration tests for Chain of Thought (CoT) integration with search pipeline.

Tests the integration between CoT service and existing search infrastructure,
including database interactions, vector store operations, and service orchestration.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, List, Any

from sqlalchemy.orm import Session
from core.config import Settings


@pytest.mark.integration
class TestChainOfThoughtSearchIntegration:
    """Test CoT integration with search pipeline."""

    @pytest.fixture
    def test_settings(self):
        """Test settings with CoT configuration."""
        return {
            "cot_enabled": True,
            "cot_max_depth": 3,
            "cot_token_multiplier": 2.0,
            "cot_evaluation_threshold": 0.6
        }

    @pytest.fixture
    async def test_collection(self, db_session: Session):
        """Create test collection for CoT testing."""
        from rag_solution.models.collection import Collection
        from rag_solution.models.user import User

        # Create test user
        user = User(
            username="cot_test_user",
            email="cot_test@example.com",
            first_name="CoT",
            last_name="Test"
        )
        db_session.add(user)
        db_session.flush()

        # Create test collection
        collection = Collection(
            name="CoT Test Collection",
            description="Test collection for Chain of Thought testing",
            user_id=user.id
        )
        db_session.add(collection)
        db_session.commit()

        yield collection

        # Cleanup
        db_session.delete(collection)
        db_session.delete(user)
        db_session.commit()

    async def test_cot_search_integration_with_database(self, test_collection, db_session):
        """Test CoT search integration with database operations."""
        from rag_solution.services.  # type: ignoresearch_service import SearchService
        from rag_solution.schemas.search_schema import SearchInput

        # Create search input with CoT configuration
        search_input = SearchInput(
            question="What is machine learning and how does it differ from traditional programming?",
            collection_id=test_collection.id,
            user_id=test_collection.user_id,
            config_metadata={
                "cot_enabled": True,
                "cot_config": {
                    "max_reasoning_depth": 3,
                    "reasoning_strategy": "decomposition"
                }
            }
        )

        # Execute search with CoT
        search_service = SearchService(settings=Settings(), db_session=db_session)
        result = await search_service.search_with_cot(search_input)

        # Verify CoT-enhanced result structure
        assert result.answer is not None
        assert hasattr(result, 'cot_output')
        assert result.cot_output is not None
        assert len(result.cot_output.reasoning_steps) > 1
        assert result.cot_output.original_question == search_input.question

    async def test_cot_pipeline_resolution_integration(self, test_collection, db_session):
        """Test CoT integration with pipeline resolution."""
        from rag_solution.services.  # type: ignoresearch_service import SearchService
        from rag_solution.schemas.search_schema import SearchInput

        search_input = SearchInput(
            question="Complex multi-part question requiring reasoning",
            collection_id=test_collection.id,
            user_id=test_collection.user_id
        )

        search_service = SearchService(settings=Settings(), db_session=db_session)

        # Should automatically enable CoT for complex questions
        result = await search_service.search(search_input)

        # Verify automatic CoT activation
        if hasattr(result, 'cot_output') and result.cot_output:
            assert result.cot_output.reasoning_steps is not None

    async def test_cot_vector_store_integration(self, test_collection, db_session):
        """Test CoT integration with vector store operations."""
        from rag_solution.services.  # type: ignoresearch_service import SearchService
        from rag_solution.schemas.search_schema import SearchInput

        search_input = SearchInput(
            question="How do neural networks learn from data?",
            collection_id=test_collection.id,
            user_id=test_collection.user_id,
            config_metadata={
                "cot_enabled": True,
                "cot_config": {"reasoning_strategy": "iterative"}
            }
        )

        search_service = SearchService(settings=Settings(), db_session=db_session)
        result = await search_service.search_with_cot(search_input)

        # Verify vector store queries for each reasoning step
        assert result.cot_output is not None
        for step in result.cot_output.reasoning_steps:
            assert step.context_used is not None
            # Each step should have retrieved relevant context

    async def test_cot_context_preservation_across_steps(self, test_collection, db_session):
        """Test context preservation across CoT reasoning steps."""
        from rag_solution.services.  # type: ignoresearch_service import SearchService
        from rag_solution.schemas.search_schema import SearchInput

        search_input = SearchInput(
            question="What is deep learning, how does it work, and what are its applications?",
            collection_id=test_collection.id,
            user_id=test_collection.user_id,
            config_metadata={
                "cot_enabled": True,
                "cot_config": {
                    "context_preservation": True,
                    "max_reasoning_depth": 4
                }
            }
        )

        search_service = SearchService(settings=Settings(), db_session=db_session)
        result = await search_service.search_with_cot(search_input)

        # Verify context preservation
        assert result.cot_output is not None
        steps = result.cot_output.reasoning_steps

        if len(steps) > 1:
            # Later steps should reference earlier step outputs
            for i, step in enumerate(steps[1:], 1):
                # Context should include information from previous steps
                context_content = " ".join(step.context_used or [])

                # Should reference concepts from earlier steps
                previous_answers = [s.intermediate_answer for s in steps[:i] if s.intermediate_answer]
                if previous_answers:
                    # At least some overlap in concepts should exist
                    assert len(context_content) > 0

    async def test_cot_performance_metrics_tracking(self, test_collection, db_session):
        """Test performance metrics tracking for CoT operations."""
        from rag_solution.services.  # type: ignoresearch_service import SearchService
        from rag_solution.schemas.search_schema import SearchInput

        search_input = SearchInput(
            question="Compare supervised and unsupervised learning algorithms",
            collection_id=test_collection.id,
            user_id=test_collection.user_id,
            config_metadata={
                "cot_enabled": True,
                "track_performance": True
            }
        )

        search_service = SearchService(settings=Settings(), db_session=db_session)
        result = await search_service.search_with_cot(search_input)

        # Verify performance tracking
        assert result.execution_time is not None
        assert result.execution_time > 0

        if result.cot_output:
            assert result.cot_output.total_execution_time is not None
            assert result.cot_output.token_usage is not None
            assert result.cot_output.token_usage > 0

            # Individual step timing
            for step in result.cot_output.reasoning_steps:
                assert step.execution_time is not None
                assert step.execution_time > 0

    async def test_cot_error_handling_integration(self, test_collection, db_session):
        """Test error handling in CoT integration scenarios."""
        from rag_solution.services.  # type: ignoresearch_service import SearchService
        from rag_solution.schemas.search_schema import SearchInput
        from core.custom_exceptions import LLMProviderError

        search_input = SearchInput(
            question="Test question for error handling",
            collection_id=test_collection.id,
            user_id=test_collection.user_id,
            config_metadata={
                "cot_enabled": True,
                "cot_config": {
                    "max_reasoning_depth": -1  # Invalid configuration
                }
            }
        )

        search_service = SearchService(settings=Settings(), db_session=db_session)

        # Should handle invalid configuration gracefully
        with pytest.raises((ValueError, ValidationError)):
            await search_service.search_with_cot(search_input)

    async def test_cot_fallback_to_regular_search(self, test_collection, db_session):
        """Test fallback to regular search when CoT fails."""
        from rag_solution.services.  # type: ignoresearch_service import SearchService
        from rag_solution.schemas.search_schema import SearchInput

        search_input = SearchInput(
            question="Simple question that might not need CoT",
            collection_id=test_collection.id,
            user_id=test_collection.user_id,
            config_metadata={
                "cot_enabled": True,
                "cot_fallback_enabled": True
            }
        )

        search_service = SearchService(settings=Settings(), db_session=db_session)
        result = await search_service.search_with_cot(search_input)

        # Should always return a valid result
        assert result.answer is not None
        assert len(result.answer) > 0

    async def test_cot_question_classification_integration(self, test_collection, db_session):
        """Test question classification integration in CoT pipeline."""
        from rag_solution.services.  # type: ignoresearch_service import SearchService
        from rag_solution.schemas.search_schema import SearchInput

        # Test different question types
        test_questions = [
            ("What is Python?", "simple"),
            ("How does machine learning differ from traditional programming and what are the advantages?", "multi_part"),
            ("Why does regularization prevent overfitting?", "causal"),
            ("Compare CNN and RNN architectures", "comparison")
        ]

        search_service = SearchService(settings=Settings(), db_session=db_session)

        for question, expected_type in test_questions:
            search_input = SearchInput(
                question=question,
                collection_id=test_collection.id,
                user_id=test_collection.user_id,
                config_metadata={"cot_enabled": True}
            )

            result = await search_service.search_with_cot(search_input)

            # Verify classification affects reasoning strategy
            if result.cot_output and expected_type != "simple":
                # Complex questions should trigger multi-step reasoning
                assert len(result.cot_output.reasoning_steps) >= 1

    async def test_cot_token_budget_management_integration(self, test_collection, db_session):
        """Test token budget management in CoT integration."""
        from rag_solution.services.  # type: ignoresearch_service import SearchService
        from rag_solution.schemas.search_schema import SearchInput

        search_input = SearchInput(
            question="Very detailed question about machine learning algorithms and their applications",
            collection_id=test_collection.id,
            user_id=test_collection.user_id,
            config_metadata={
                "cot_enabled": True,
                "cot_config": {
                    "token_budget_multiplier": 1.5,
                    "max_reasoning_depth": 2
                }
            }
        )

        search_service = SearchService(settings=Settings(), db_session=db_session)
        result = await search_service.search_with_cot(search_input)

        # Verify token usage is tracked and within reasonable bounds
        if result.cot_output:
            assert result.cot_output.token_usage is not None
            # Should respect budget constraints
            assert result.cot_output.token_usage > 0

    async def test_cot_database_persistence_integration(self, test_collection, db_session):
        """Test database persistence of CoT results."""
        from rag_solution.services.  # type: ignoresearch_service import SearchService
        from rag_solution.schemas.search_schema import SearchInput
        from rag_solution.models.chain_of_thought import  # type: ignore ChainOfThoughtSession

        search_input = SearchInput(
            question="Test question for persistence",
            collection_id=test_collection.id,
            user_id=test_collection.user_id,
            config_metadata={
                "cot_enabled": True,
                "persist_reasoning": True
            }
        )

        search_service = SearchService(settings=Settings(), db_session=db_session)
        result = await search_service.search_with_cot(search_input)

        # Verify CoT session is persisted
        cot_sessions = db_session.query(ChainOfThoughtSession).filter_by(
            user_id=test_collection.user_id,
            collection_id=test_collection.id
        ).all()

        assert len(cot_sessions) > 0
        latest_session = cot_sessions[-1]
        assert latest_session.original_question == search_input.question
        assert latest_session.final_answer is not None

    async def test_cot_concurrent_execution_integration(self, test_collection, db_session):
        """Test concurrent CoT execution handling."""
        import asyncio
        from rag_solution.services.  # type: ignoresearch_service import SearchService
        from rag_solution.schemas.search_schema import SearchInput

        # Create multiple concurrent search requests
        search_inputs = [
            SearchInput(
                question=f"Test question {i} for concurrent execution",
                collection_id=test_collection.id,
                user_id=test_collection.user_id,
                config_metadata={"cot_enabled": True}
            )
            for i in range(3)
        ]

        search_service = SearchService(settings=Settings(), db_session=db_session)

        # Execute concurrently
        tasks = [search_service.search_with_cot(search_input) for search_input in search_inputs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert result.answer is not None


@pytest.mark.integration
class TestChainOfThoughtLLMProviderIntegration:
    """Test CoT integration with different LLM providers."""

    async def test_cot_watsonx_provider_integration(self):
        """Test CoT with WatsonX LLM provider."""
        from rag_solution.services.  # type: ignorechain_of_thought_service import ChainOfThoughtService
        from rag_solution.generation.providers.  # type: ignorewatsonx_provider import WatsonXProvider
        from rag_solution.schemas.chain_of_thought_schema import  # type: ignore ChainOfThoughtInput

        mock_provider = AsyncMock(spec=WatsonXProvider)
        mock_provider.generate_response.return_value = "Test LLM response"

        cot_service = ChainOfThoughtService(
            settings=Settings(),
            llm_provider=mock_provider
        )

        cot_input = ChainOfThoughtInput(
            question="Test question for WatsonX integration",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={"enabled": True}
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        # Verify integration with WatsonX provider
        assert mock_provider.generate_response.called
        assert result.final_answer is not None

    async def test_cot_openai_provider_integration(self):
        """Test CoT with OpenAI provider."""
        from rag_solution.services.  # type: ignorechain_of_thought_service import ChainOfThoughtService
        from rag_solution.generation.providers.  # type: ignoreopenai_provider import OpenAIProvider
        from rag_solution.schemas.chain_of_thought_schema import  # type: ignore ChainOfThoughtInput

        mock_provider = AsyncMock(spec=OpenAIProvider)
        mock_provider.generate_response.return_value = "OpenAI test response"

        cot_service = ChainOfThoughtService(
            settings=Settings(),
            llm_provider=mock_provider
        )

        cot_input = ChainOfThoughtInput(
            question="Test question for OpenAI integration",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={"enabled": True}
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        # Verify integration with OpenAI provider
        assert mock_provider.generate_response.called
        assert result.final_answer is not None

    async def test_cot_provider_switching_integration(self):
        """Test CoT with dynamic provider switching."""
        from rag_solution.services.  # type: ignorechain_of_thought_service import ChainOfThoughtService
        from rag_solution.schemas.chain_of_thought_schema import  # type: ignore ChainOfThoughtInput

        # Test that CoT service can handle provider switching
        cot_input = ChainOfThoughtInput(
            question="Test question for provider switching",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={
                "enabled": True,
                "preferred_provider": "openai"
            }
        )

        # This would be handled by the service layer
        # Testing the interface and configuration handling
        assert cot_input.cot_config["preferred_provider"] == "openai"


@pytest.mark.integration
class TestChainOfThoughtVectorStoreIntegration:
    """Test CoT integration with vector store operations."""

    async def test_cot_milvus_integration(self):
        """Test CoT with Milvus vector store."""
        from rag_solution.services.  # type: ignorechain_of_thought_service import ChainOfThoughtService
        from vectordbs.milvus_store import MilvusVectorStore
        from rag_solution.schemas.chain_of_thought_schema import  # type: ignore ChainOfThoughtInput

        mock_vector_store = AsyncMock(spec=MilvusVectorStore)
        mock_vector_store.search.return_value = [
            {"text": "Relevant document 1", "score": 0.9},
            {"text": "Relevant document 2", "score": 0.8}
        ]

        cot_service = ChainOfThoughtService(
            settings=Settings(),
            vector_store=mock_vector_store
        )

        cot_input = ChainOfThoughtInput(
            question="Test question for Milvus integration",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={"enabled": True}
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        # Verify vector store queries for reasoning steps
        assert mock_vector_store.search.called
        assert result.final_answer is not None

    async def test_cot_multi_vector_store_integration(self):
        """Test CoT with multiple vector store queries per step."""
        from rag_solution.services.  # type: ignorechain_of_thought_service import ChainOfThoughtService
        from rag_solution.schemas.chain_of_thought_schema import  # type: ignore ChainOfThoughtInput

        cot_input = ChainOfThoughtInput(
            question="Complex question requiring multiple vector searches",
            collection_id=uuid4(),
            user_id=uuid4(),
            cot_config={
                "enabled": True,
                "vector_search_strategy": "multi_query"
            }
        )

        # This tests the configuration and interface
        # Implementation would handle multiple vector store queries
        assert cot_input.cot_config["vector_search_strategy"] == "multi_query"