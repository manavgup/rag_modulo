"""Integration tests for pipeline workflow."""
import pytest
from sqlalchemy.orm import Session
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.schemas.llm_provider_schema import (
    LLMProviderInput,
    LLMProviderModelInput,
    ModelType
)
from rag_solution.schemas.prompt_template_schema import (
    PromptTemplateType,
    PromptTemplateInput
)
from rag_solution.schemas.pipeline_schema import PipelineConfigInput


def test_complete_pipeline_flow(db_session: Session, base_user):
    """Test complete pipeline workflow."""
    # Set up provider
    provider_service = LLMProviderService(db_session)
    provider = provider_service.create_provider(
        LLMProviderInput(
            name="watsonx",
            base_url="https://us-south.ml.cloud.ibm.com",
            api_key="test-api-key",
            project_id="test-project-id"
        )
    )

    # Set up model
    model = provider_service.create_provider_model(
        LLMProviderModelInput(
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
            is_active=True
        )
    )

    # Set up templates
    template_service = PromptTemplateService(db_session)
    
    # Create RAG query template
    rag_template = template_service.create_or_update_template(
        base_user.id,
        PromptTemplateInput(
            name="test-rag-template",
            provider="watsonx",
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt="You are a helpful AI assistant.",
            template_format="{context}\n\n{question}",
            input_variables={
                "context": "Retrieved context for answering the question",
                "question": "User's question to answer"
            },
            example_inputs={
                "context": "Python was created by Guido van Rossum.",
                "question": "Who created Python?"
            },
            is_default=True
        )
    )

    # Create question generation template
    question_template = template_service.create_or_update_template(
        base_user.id,
        PromptTemplateInput(
            name="test-question-template",
            provider="watsonx",
            template_type=PromptTemplateType.QUESTION_GENERATION,
            system_prompt=(
                "You are an AI assistant that generates relevant questions based on "
                "the given context. Generate clear, focused questions that can be "
                "answered using the information provided."
            ),
            template_format=(
                "{context}\n\n"
                "Generate {num_questions} specific questions that can be answered "
                "using only the information provided above."
            ),
            input_variables={
                "context": "Retrieved passages from knowledge base",
                "num_questions": "Number of questions to generate"
            },
            example_inputs={
                "context": "Python supports multiple programming paradigms.",
                "num_questions": 3
            },
            is_default=True
        )
    )

    # Create pipeline
    pipeline_service = PipelineService(db_session)
    pipeline = pipeline_service.create_pipeline(
        PipelineConfigInput(
            name="test-pipeline",
            description="Test pipeline for RAG workflow",
            chunking_strategy="fixed",
            embedding_model="sentence-transformers/all-mpnet-base-v2",
            retriever="vector",
            context_strategy="priority",
            provider_id=provider.id,
            enable_logging=True,
            max_context_length=2048,
            timeout=30.0,
            is_default=True
        )
    )

    assert pipeline.name == "test-pipeline"
    assert pipeline.description == "Test pipeline for RAG workflow"
    assert pipeline.chunking_strategy == "fixed"
    assert pipeline.embedding_model == "sentence-transformers/all-mpnet-base-v2"
    assert pipeline.provider_id == provider.id
    assert pipeline.is_default is True

    # Test pipeline execution
    context = (
        "Python is a high-level programming language created by Guido van Rossum. "
        "It emphasizes code readability and allows programmers to express concepts "
        "in fewer lines of code than would be possible in languages such as C++ or Java."
    )
    question = "Who created Python and what are its main features?"

    response = pipeline_service.execute_pipeline(
        pipeline.id,
        context=context,
        question=question
    )

    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0


def test_pipeline_update_flow(db_session: Session, base_user):
    """Test updating pipeline configuration."""
    # Set up initial pipeline with templates
    provider_service = LLMProviderService(db_session)
    provider = provider_service.create_provider(
        LLMProviderInput(
            name="watsonx",
            base_url="https://us-south.ml.cloud.ibm.com",
            api_key="test-api-key",
            project_id="test-project-id"
        )
    )

    template_service = PromptTemplateService(db_session)
    
    # Create templates
    rag_template = template_service.create_or_update_template(
        base_user.id,
        PromptTemplateInput(
            name="test-rag-template",
            provider="watsonx",
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt="Initial system prompt",
            template_format="{context}\n\n{question}",
            input_variables={
                "context": "Retrieved context",
                "question": "User's question"
            },
            example_inputs={
                "context": "Initial context",
                "question": "Initial question"
            },
            is_default=True
        )
    )

    # Create question generation template
    question_template = template_service.create_or_update_template(
        base_user.id,
        PromptTemplateInput(
            name="test-question-template",
            provider="watsonx",
            template_type=PromptTemplateType.QUESTION_GENERATION,
            system_prompt="Initial question generation prompt",
            template_format="{context}\n\n{num_questions}",
            input_variables={
                "context": "Context",
                "num_questions": "Number of questions"
            },
            example_inputs={
                "context": "Initial context",
                "num_questions": 3
            },
            is_default=True
        )
    )

    # Create initial pipeline
    pipeline_service = PipelineService(db_session)
    pipeline = pipeline_service.create_pipeline(
        PipelineConfigInput(
            name="test-pipeline",
            description="Initial pipeline description",
            chunking_strategy="fixed",
            embedding_model="sentence-transformers/all-mpnet-base-v2",
            retriever="vector",
            context_strategy="priority",
            provider_id=provider.id,
            enable_logging=True,
            max_context_length=2048,
            timeout=30.0,
            is_default=True
        )
    )

    # Update pipeline
    updated_pipeline = pipeline_service.update_pipeline(
        pipeline.id,
        PipelineConfigInput(
            name="updated-pipeline",
            description="Updated pipeline description",
            chunking_strategy="semantic",
            embedding_model="sentence-transformers/all-mpnet-base-v2",
            retriever="vector",
            context_strategy="priority",
            provider_id=provider.id,
            enable_logging=True,
            max_context_length=2048,
            timeout=30.0,
            is_default=True
        )
    )

    assert updated_pipeline.id == pipeline.id
    assert updated_pipeline.name == "updated-pipeline"
    assert updated_pipeline.description == "Updated pipeline description"
    assert updated_pipeline.is_active is True
