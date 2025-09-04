"""Integration tests for configuration error handling."""

import pytest
from sqlalchemy.orm import Session

from rag_solution.schemas.llm_model_schema import LLMModelInput, ModelType
from rag_solution.schemas.llm_provider_schema import LLMProviderInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService


@pytest.mark.integration
def test_invalid_template_variables(db_session: Session, base_user):
    """Test error handling for invalid template variables."""
    # Create provider service
    provider_service = LLMProviderService(db_session)

    # Create provider
    provider_input = LLMProviderInput(
        name="watsonx",
        base_url="https://us-south.ml.cloud.ibm.com",
        api_key="test-api-key",
        project_id="test-project-id",
    )
    provider_service.create_provider(provider_input)

    # Create template service
    template_service = PromptTemplateService(db_session)

    # Test missing required variable
    with pytest.raises(ValueError, match="Template variables missing"):
        template_service.create_template(
            base_user.id,
            PromptTemplateInput(
                name="test-template",
                provider="watsonx",
                template_type=PromptTemplateType.RAG_QUERY,
                template_format="{context}\n\n{question}",
                input_variables={"context": "Retrieved context"},  # Missing question
            ),
        )

    # Test undefined variable in template
    with pytest.raises(ValueError, match="Template variables missing"):
        template_service.create_template(
            base_user.id,
            PromptTemplateInput(
                name="test-template",
                provider="watsonx",
                template_type=PromptTemplateType.RAG_QUERY,
                template_format="{context}\n\n{undefined_var}",  # Undefined variable
                input_variables={"context": "Retrieved context", "question": "User's question"},
            ),
        )


def test_invalid_provider_configuration(db_session: Session, base_user):
    """Test error handling for invalid provider configuration."""
    provider_service = LLMProviderService(db_session)
    template_service = PromptTemplateService(db_session)

    # Create provider with invalid URL
    provider_input = LLMProviderInput(
        name="watsonx", base_url="invalid-url", api_key="test-api-key", project_id="test-project-id"
    )
    provider_service.create_provider(provider_input)

    # Test invalid provider name
    with pytest.raises(ValueError, match="Invalid provider"):
        template_service.create_template(
            base_user.id,
            PromptTemplateInput(
                name="test-template",
                provider="invalid",  # Invalid provider name
                template_type=PromptTemplateType.RAG_QUERY,
                template_format="{context}\n\n{question}",
                input_variables={"context": "Retrieved context", "question": "User's question"},
            ),
        )


def test_invalid_model_configuration(db_session: Session):
    """Test error handling for invalid model configuration."""
    provider_service = LLMProviderService(db_session)

    # Create provider
    provider_input = LLMProviderInput(
        name="watsonx",
        base_url="https://us-south.ml.cloud.ibm.com",
        api_key="test-api-key",
        project_id="test-project-id",
    )
    provider = provider_service.create_provider(provider_input)

    # Test invalid model configuration
    with pytest.raises(ValueError):
        provider_service.create_provider_model(
            LLMModelInput(
                provider_id=provider.id,
                model_id="",  # Empty model ID
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
        )

    # Test negative timeout
    with pytest.raises(ValueError):
        provider_service.create_provider_model(
            LLMModelInput(
                provider_id=provider.id,
                model_id="google/flan-ul2",
                default_model_id="google/flan-ul2",
                model_type=ModelType.GENERATION,
                timeout=-1,  # Negative timeout
                max_retries=3,
                batch_size=10,
                retry_delay=1.0,
                concurrency_limit=10,
                stream=False,
                rate_limit=10,
                is_default=True,
                is_active=True,
            )
        )
