"""Integration tests for pipeline service error handling."""

import asyncio
from unittest.mock import patch
from pydantic import UUID4

import pytest
from sqlalchemy.orm import Session

from core.custom_exceptions import ConfigurationError, LLMProviderError, NotFoundError, ValidationError
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.pipeline_schema import PipelineConfigInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.search_service import SearchService


@pytest.fixture
def pipeline_setup(db_session: Session, base_user, test_collection):
    """Set up pipeline with services."""
    pipeline_service = PipelineService(db_session)
    search_service = SearchService(db_session)
    provider_service = LLMProviderService(db_session)
    parameters_service = LLMParametersService(db_session)
    template_service = PromptTemplateService(db_session)

    # Create user's default parameters
    parameters_input = LLMParametersInput(
        name="test-parameters",
        user_id=base_user.id,
        temperature=0.7,
        max_new_tokens=1000,
        top_k=50,
        top_p=0.95,
        is_default=True,
    )
    parameters = parameters_service.create_parameters(parameters_input)

    # Create user's default templates
    templates = {}
    template_base = {
        "provider": "watsonx",
        "template_format": "{context}\n\n{question}",
        "input_variables": {"context": "str", "question": "str"},
        "validation_schema": {
            "model": "PromptVariables",
            "fields": {"context": {"type": "str", "min_length": 1}, "question": {"type": "str", "min_length": 1}},
            "required": ["context", "question"],
        },
        "example_inputs": {"context": "Python was created by Guido van Rossum.", "question": "Who created Python?"},
        "is_default": True,
    }

    for template_type in [PromptTemplateType.RAG_QUERY, PromptTemplateType.RESPONSE_EVALUATION]:
        template_input = PromptTemplateInput(
            name=f"test-{template_type.value}", template_type=template_type, **template_base
        )
        templates[template_type] = template_service.create_template(base_user.id, template_input)

    return {
        "pipeline_service": pipeline_service,
        "search_service": search_service,
        "provider_service": provider_service,
        "parameters_service": parameters_service,
        "template_service": template_service,
        "collection": test_collection,
        "user": base_user,
        "parameters": parameters,
        "templates": templates,
    }


@pytest.mark.asyncio
async def test_provider_initialization_error(pipeline_setup):
    """Test handling provider initialization errors."""
    # Break provider initialization
    with patch("rag_solution.generation.providers.watsonx.WatsonXProvider.initialize") as mock_init:
        mock_init.side_effect = ConfigurationError("Failed to initialize provider")

        # Initialize pipeline
        with pytest.raises(ConfigurationError) as exc_info:
            await pipeline_setup["pipeline_service"].initialize(
                collection_name=pipeline_setup["collection"].vector_db_name,
                config=PipelineConfigInput(
                    name="test-pipeline",
                    description="Test pipeline",
                    chunking_strategy="fixed",
                    embedding_model="sentence-transformers/all-mpnet-base-v2",
                    retriever="vector",
                    context_strategy="priority",
                    provider_id=pipeline_setup["provider_service"].get_default_provider().id,
                    enable_logging=True,
                    max_context_length=2048,
                    timeout=30.0,
                    is_default=False,
                ),
            )

        assert "Failed to initialize provider" in str(exc_info.value)


@pytest.mark.asyncio
async def test_provider_authentication_error(pipeline_setup):
    """Test handling provider authentication errors."""
    # Break provider authentication
    with patch("rag_solution.generation.providers.watsonx.WatsonXProvider.authenticate") as mock_auth:
        mock_auth.side_effect = LLMProviderError("watsonx", "authentication", "Authentication failed")

        search_input = SearchInput(
            question="Test query",
            collection_id=pipeline_setup["collection"].id,
            pipeline_id=UUID4("87654321-4321-8765-4321-876543210987"),
        )

        # Execute pipeline
        result = await pipeline_setup["pipeline_service"].execute_pipeline(search_input, pipeline_setup["user"].id)
        assert result.evaluation is not None
        assert "error" in result.evaluation
        assert "Authentication failed" in str(result.evaluation["error"])


@pytest.mark.asyncio
async def test_template_formatting_error(pipeline_setup):
    """Test handling template formatting errors."""
    # Create invalid template
    template_input = PromptTemplateInput(
        name="invalid-template",
        provider="watsonx",
        template_type=PromptTemplateType.RAG_QUERY,
        template_format="Invalid {missing}",  # Missing required placeholder
        input_variables={"missing": "str"},  # Invalid variables
        validation_schema={
            "model": "PromptVariables",
            "fields": {"missing": {"type": "str", "min_length": 1}},
            "required": ["missing"],
        },
        example_inputs={"missing": "Example value"},
        is_default=True,
    )
    pipeline_setup["template_service"].create_or_update_template(pipeline_setup["user"].id, template_input)

    search_input = SearchInput(
        question="Test query",
        collection_id=pipeline_setup["collection"].id,
        pipeline_id=UUID4("87654321-4321-8765-4321-876543210987"),
    )

    # Execute pipeline
    result = await pipeline_setup["pipeline_service"].execute_pipeline(search_input, pipeline_setup["user"].id)
    assert result.generated_answer != ""  # Should use fallback template
    assert result.evaluation is not None


@pytest.mark.asyncio
async def test_retrieval_error(pipeline_setup):
    """Test handling retrieval errors."""
    # Break vector store connection
    with patch("vectordbs.milvus_store.MilvusStore.search") as mock_search:
        mock_search.side_effect = Exception("Vector store error")

        search_input = SearchInput(
            question="Test query",
            collection_id=pipeline_setup["collection"].id,
            pipeline_id=UUID4("87654321-4321-8765-4321-876543210987"),
        )

        # Execute pipeline
        result = await pipeline_setup["pipeline_service"].execute_pipeline(search_input, pipeline_setup["user"].id)
        assert "couldn't find any relevant documents" in result.generated_answer


@pytest.mark.asyncio
async def test_generation_error(pipeline_setup):
    """Test handling text generation errors."""
    # Break text generation
    with patch("rag_solution.generation.providers.watsonx.WatsonXProvider.generate_text") as mock_generate:
        mock_generate.side_effect = LLMProviderError("watsonx", "generation", "Generation failed")

        search_input = SearchInput(
            question="Test query",
            collection_id=pipeline_setup["collection"].id,
            pipeline_id=UUID4("87654321-4321-8765-4321-876543210987"),
        )

        # Execute pipeline
        result = await pipeline_setup["pipeline_service"].execute_pipeline(search_input, pipeline_setup["user"].id)
        assert result.generated_answer == ""
        assert result.evaluation is not None
        assert "error" in result.evaluation


@pytest.mark.asyncio
async def test_evaluation_error(pipeline_setup):
    """Test handling evaluation errors."""
    # Break evaluation
    with patch("rag_solution.evaluation.evaluator.RAGEvaluator.evaluate") as mock_evaluate:
        mock_evaluate.side_effect = Exception("Evaluation failed")

        search_input = SearchInput(
            question="Test query",
            collection_id=pipeline_setup["collection"].id,
            pipeline_id=UUID4("87654321-4321-8765-4321-876543210987"),
        )

        # Execute pipeline
        result = await pipeline_setup["pipeline_service"].execute_pipeline(search_input, pipeline_setup["user"].id)
        assert result.generated_answer != ""  # Generation should still work
        assert result.evaluation is not None
        assert "error" in result.evaluation


@pytest.mark.asyncio
async def test_invalid_configuration(pipeline_setup):
    """Test handling invalid configuration."""
    # Create invalid parameters
    parameters_input = LLMParametersInput(
        name="invalid-params",
        user_id=pipeline_setup["user"].id,
        temperature=2.0,  # Invalid value
        is_default=True,
    )

    with pytest.raises(ValidationError):
        pipeline_setup["parameters_service"].create_or_update_parameters(pipeline_setup["user"].id, parameters_input)


@pytest.mark.asyncio
async def test_missing_configuration(pipeline_setup):
    """Test handling missing configuration."""
    # Try to execute without initialization
    search_input = SearchInput(
        question="Test query",
        collection_id=pipeline_setup["collection"].id,
        pipeline_id=UUID4("87654321-4321-8765-4321-876543210987"),
    )

    with pytest.raises(ConfigurationError):
        await pipeline_setup["pipeline_service"].execute_pipeline(search_input, pipeline_setup["user"].id)


@pytest.mark.asyncio
async def test_concurrent_error_handling(pipeline_setup):
    """Test handling errors in concurrent operations."""

    # Break provider randomly
    def random_error(*args, **kwargs):
        import random

        if random.choice([True, False]):
            raise LLMProviderError("watsonx", "generation", "Random error")
        return "Generated text"

    with patch("rag_solution.generation.providers.watsonx.WatsonXProvider.generate_text") as mock_generate:
        mock_generate.side_effect = random_error

        # Create multiple search inputs
        search_inputs = [
            SearchInput(
                question=f"Question {i}",
                collection_id=pipeline_setup["collection"].id,
                pipeline_id=UUID4("87654321-4321-8765-4321-876543210987"),
            )
            for i in range(5)
        ]

        # Execute searches concurrently
        results = await asyncio.gather(
            *[
                pipeline_setup["search_service"].search(search_input, pipeline_setup["user"].id)
                for search_input in search_inputs
            ]
        )

        # Verify all operations completed with or without errors
        assert len(results) == 5
        for result in results:
            assert result is not None
            if result.generated_answer == "":
                assert result.evaluation is not None
                assert "error" in result.evaluation


@pytest.mark.asyncio
async def test_missing_user_defaults(pipeline_setup):
    """Test handling missing user defaults."""
    # Remove user's default parameters and templates
    pipeline_setup["parameters_service"].delete_parameters(pipeline_setup["user"].id)
    pipeline_setup["template_service"].delete_template(pipeline_setup["user"].id)

    search_input = SearchInput(
        question="Test query",
        collection_id=pipeline_setup["collection"].id,
        pipeline_id=UUID4("87654321-4321-8765-4321-876543210987"),
    )

    # Execute pipeline - should fail gracefully
    with pytest.raises(NotFoundError) as exc_info:
        await pipeline_setup["pipeline_service"].execute_pipeline(search_input, pipeline_setup["user"].id)
    assert "User's default parameters not found" in str(exc_info.value)
