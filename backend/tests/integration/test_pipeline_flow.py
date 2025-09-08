"""Integration tests for pipeline workflow."""

import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session

from rag_solution.schemas.llm_model_schema import LLMModelInput, ModelType
from rag_solution.schemas.llm_provider_schema import LLMProviderInput
from rag_solution.schemas.pipeline_schema import ChunkingStrategy, ContextStrategy, PipelineConfigInput, RetrieverType
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.prompt_template_service import PromptTemplateService


@pytest.mark.integration
def test_complete_pipeline_flow(db_session: Session, base_user: UserOutput) -> None:
    """Test complete pipeline workflow."""
    # Set up provider
    provider_service = LLMProviderService(db_session)
    provider = provider_service.create_provider(
        LLMProviderInput(
            name="watsonx",
            base_url="https://us-south.ml.cloud.ibm.com",
            api_key=SecretStr("test-api-key"),
            org_id="test-org-id",
            project_id="test-project-id",
            is_active=True,
            is_default=False,
            user_id=base_user.id,
        )
    )

    # Set up model
    model_input = LLMModelInput(
        provider_id=provider.id,
        model_id="google/flan-ul2",
        default_model_id="google/flan-ul2",
        model_type=ModelType.GENERATION,
        timeout=30,
        max_retries=3,
        batch_size=10,
        retry_delay=1.0,
        concurrency_limit=10,
        stream=False,
        rate_limit=10,
        is_default=True,
        is_active=True,
    )
    model_data = model_input.model_dump()
    provider_service.create_provider_model(provider.id, model_data)

    # Set up templates
    template_service = PromptTemplateService(db_session)

    # Create RAG query template
    template_service.create_template(
        PromptTemplateInput(
            name="test-rag-template",
            user_id=base_user.id,
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt="You are a helpful AI assistant.",
            template_format="{context}\n\n{question}",
            input_variables={
                "context": "Retrieved context for answering the question",
                "question": "User's question to answer",
            },
            example_inputs={"context": "Python was created by Guido van Rossum.", "question": "Who created Python?"},
            max_context_length=2048,
            is_default=True,
        ),
    )

    # Create question generation template
    template_service.create_template(
        PromptTemplateInput(
            name="test-question-template",
            user_id=base_user.id,
            template_type=PromptTemplateType.QUESTION_GENERATION,
            system_prompt=(
                "You are an AI assistant that generates relevant questions based on " "the given context. Generate clear, focused questions that can be " "answered using the information provided."
            ),
            template_format=("{context}\n\n" "Generate {num_questions} specific questions that can be answered " "using only the information provided above."),
            input_variables={
                "context": "Retrieved passages from knowledge base",
                "num_questions": "Number of questions to generate",
            },
            example_inputs={"context": "Python supports multiple programming paradigms.", "num_questions": 3},
            max_context_length=2048,
            is_default=True,
        ),
    )

    # Create pipeline
    pipeline_service = PipelineService(db_session)
    pipeline = pipeline_service.create_pipeline(
        PipelineConfigInput(
            name="test-pipeline",
            description="Test pipeline for RAG workflow",
            user_id=base_user.id,
            collection_id=None,
            chunking_strategy=ChunkingStrategy.FIXED,
            embedding_model="sentence-transformers/all-mpnet-base-v2",
            retriever=RetrieverType.VECTOR,
            context_strategy=ContextStrategy.PRIORITY,
            provider_id=provider.id,
            enable_logging=True,
            max_context_length=2048,
            timeout=30.0,
            is_default=True,
        )
    )

    assert pipeline.name == "test-pipeline"
    assert pipeline.description == "Test pipeline for RAG workflow"
    assert pipeline.chunking_strategy == "fixed"
    assert pipeline.embedding_model == "sentence-transformers/all-mpnet-base-v2"
    assert pipeline.provider_id == provider.id
    assert pipeline.is_default is True

    # Test pipeline execution
    context = (  # noqa: F841
        "Python is a high-level programming language created by Guido van Rossum. "
        "It emphasizes code readability and allows programmers to express concepts "
        "in fewer lines of code than would be possible in languages such as C++ or Java."
    )
    question = "Who created Python and what are its main features?"

    search_input = SearchInput(
        question=question,
        collection_id=base_user.id,  # Using user_id as collection_id for test
        pipeline_id=pipeline.id,
        user_id=base_user.id,
    )
    response = pipeline_service.execute_pipeline(search_input, collection_name="test-collection")

    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0


def test_pipeline_update_flow(db_session: Session, base_user: UserOutput) -> None:
    """Test updating pipeline configuration."""
    # Set up initial pipeline with templates
    provider_service = LLMProviderService(db_session)
    provider = provider_service.create_provider(
        LLMProviderInput(
            name="watsonx",
            base_url="https://us-south.ml.cloud.ibm.com",
            api_key=SecretStr("test-api-key"),
            org_id="test-org-id",
            project_id="test-project-id",
            is_active=True,
            is_default=False,
            user_id=base_user.id,
        )
    )

    template_service = PromptTemplateService(db_session)

    # Create templates
    template_service.create_template(
        PromptTemplateInput(
            name="test-rag-template",
            user_id=base_user.id,
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt="Initial system prompt",
            template_format="{context}\n\n{question}",
            input_variables={"context": "Retrieved context", "question": "User's question"},
            example_inputs={"context": "Initial context", "question": "Initial question"},
            max_context_length=2048,
            is_default=True,
        ),
    )

    # Create question generation template
    template_service.create_template(
        PromptTemplateInput(
            name="test-question-template",
            user_id=base_user.id,
            template_type=PromptTemplateType.QUESTION_GENERATION,
            system_prompt="Initial question generation prompt",
            template_format="{context}\n\n{num_questions}",
            input_variables={"context": "Context", "num_questions": "Number of questions"},
            example_inputs={"context": "Initial context", "num_questions": 3},
            max_context_length=2048,
            is_default=True,
        ),
    )

    # Create initial pipeline
    pipeline_service = PipelineService(db_session)
    pipeline = pipeline_service.create_pipeline(
        PipelineConfigInput(
            name="test-pipeline",
            description="Initial pipeline description",
            user_id=base_user.id,
            collection_id=None,
            chunking_strategy=ChunkingStrategy.FIXED,
            embedding_model="sentence-transformers/all-mpnet-base-v2",
            retriever=RetrieverType.VECTOR,
            context_strategy=ContextStrategy.PRIORITY,
            provider_id=provider.id,
            enable_logging=True,
            max_context_length=2048,
            timeout=30.0,
            is_default=True,
        )
    )

    # Update pipeline
    updated_pipeline = pipeline_service.update_pipeline(
        pipeline.id,
        PipelineConfigInput(
            name="updated-pipeline",
            description="Updated pipeline description",
            user_id=base_user.id,
            collection_id=None,
            chunking_strategy=ChunkingStrategy.SEMANTIC,
            embedding_model="sentence-transformers/all-mpnet-base-v2",
            retriever=RetrieverType.VECTOR,
            context_strategy=ContextStrategy.PRIORITY,
            provider_id=provider.id,
            enable_logging=True,
            max_context_length=2048,
            timeout=30.0,
            is_default=True,
        ),
    )

    assert updated_pipeline.id == pipeline.id
    assert updated_pipeline.name == "updated-pipeline"
    assert updated_pipeline.description == "Updated pipeline description"
