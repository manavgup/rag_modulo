"""Integration tests for configuration workflow."""
from sqlalchemy.orm import Session
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.schemas.llm_provider_schema import LLMProviderInput
from rag_solution.schemas.llm_model_schema import ModelType, LLMModelInput
from rag_solution.schemas.prompt_template_schema import (
    PromptTemplateType,
    PromptTemplateInput
)


def test_complete_configuration_flow(db_session: Session, base_user):
    """Test complete configuration workflow."""
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

    assert provider.name == "watsonx"
    assert provider.base_url == "https://us-south.ml.cloud.ibm.com"
    assert provider.api_key == "test-api-key"
    assert provider.project_id == "test-project-id"

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
    assert rag_template.input_variables is not None
    assert "context" in rag_template.input_variables
    assert "question" in rag_template.input_variables

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
    assert question_template.input_variables is not None
    assert "context" in question_template.input_variables
    assert "num_questions" in question_template.input_variables


def test_update_template_flow(db_session: Session, base_user):
    """Test updating an existing template."""
    # Create provider service
    provider_service = LLMProviderService(db_session)

    # Create provider
    provider_input = LLMProviderInput(
        name="watsonx",
        base_url="https://us-south.ml.cloud.ibm.com",
        api_key="test-api-key",
        project_id="test-project-id"
    )
    provider_service.create_provider(provider_input)

    # Create template service
    template_service = PromptTemplateService(db_session)

    # Create initial template
    template = template_service.create_template(
        base_user.id,
        PromptTemplateInput(
            name="test-template",
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

    # Update template
    updated_template = template_service.create_template(
        base_user.id,
        PromptTemplateInput(
            name="test-template",  # Same name to update
            provider="watsonx",
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt="Updated system prompt",
            template_format="{context}\n\n{question}",
            input_variables={
                "context": "Updated context description",
                "question": "Updated question description"
            },
            example_inputs={
                "context": "Updated context",
                "question": "Updated question"
            },
            is_default=True
        )
    )

    assert updated_template.id == template.id  # Same ID means it was updated
    assert updated_template.system_prompt == "Updated system prompt"
    assert updated_template.input_variables["context"] == "Updated context description"
    assert updated_template.example_inputs["context"] == "Updated context"
