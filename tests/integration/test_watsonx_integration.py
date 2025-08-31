"""Integration tests for WatsonX provider."""
import pytest
from sqlalchemy.orm import Session
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.schemas.llm_provider_schema import LLMProviderInput
from rag_solution.schemas.llm_model_schema import LLMModelInput, ModelType
from rag_solution.schemas.prompt_template_schema import (
    PromptTemplateType,
    PromptTemplateInput
)


def test_watsonx_provider_setup(db_session: Session, base_user):
    """Test setting up WatsonX provider with templates."""
    # Create provider service
    provider_service = LLMProviderService(db_session)

    # Create provider
    provider_input = LLMProviderInput(
        name="watsonx",
        base_url="https://us-south.ml.cloud.ibm.com",
        api_key="test-api-key",
        project_id="test-project-id"
    )
    provider = provider_service.create_provider(provider_input)

    # Create model
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
        is_active=True
    )
    model = provider_service.create_provider_model(model_input)

    assert model.provider_id == provider.id
    assert model.model_id == "google/flan-ul2"
    assert model.is_default is True
    assert model.is_active is True

    # Create template service
    template_service = PromptTemplateService(db_session)

    # Create RAG query template
    rag_template = template_service.create_template(
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

    assert rag_template.name == "test-rag-template"
    assert rag_template.provider == "watsonx"
    assert rag_template.template_type == PromptTemplateType.RAG_QUERY
    assert rag_template.is_default is True

    # Create question generation template
    question_template = template_service.create_template(
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

    assert question_template.name == "test-question-template"
    assert question_template.provider == "watsonx"
    assert question_template.template_type == PromptTemplateType.QUESTION_GENERATION
    assert question_template.is_default is True


def test_watsonx_provider_invalid_setup(db_session: Session, base_user):
    """Test invalid WatsonX provider setup."""
    provider_service = LLMProviderService(db_session)
    template_service = PromptTemplateService(db_session)

    # Create provider with invalid URL
    provider_input = LLMProviderInput(
        name="watsonx",
        base_url="invalid-url",
        api_key="test-api-key",
        project_id="test-project-id"
    )
    provider_service.create_provider(provider_input)

    # Test creating template with missing variables
    with pytest.raises(ValueError, match="Template variables missing"):
        template_service.create_template(
            base_user.id,
            PromptTemplateInput(
                name="test-template",
                provider="watsonx",
                template_type=PromptTemplateType.RAG_QUERY,
                template_format="{context}\n\n{question}",
                input_variables={"context": "Retrieved context"}  # Missing question
            )
        )

    # Test creating template with invalid provider
    with pytest.raises(ValueError, match="Invalid provider"):
        template_service.create_template(
            base_user.id,
            PromptTemplateInput(
                name="test-template",
                provider="invalid",  # Invalid provider name
                template_type=PromptTemplateType.RAG_QUERY,
                template_format="{context}\n\n{question}",
                input_variables={
                    "context": "Retrieved context",
                    "question": "User's question"
                }
            )
        )
