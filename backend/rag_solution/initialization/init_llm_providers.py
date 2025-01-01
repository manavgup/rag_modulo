"""Initialize LLM providers during application startup."""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from core.config import settings
from core.logging_utils import get_logger
from rag_solution.services.provider_config_service import ProviderConfigService
from rag_solution.repository.prompt_template_repository import PromptTemplateRepository
from rag_solution.schemas.llm_parameters_schema import LLMParametersCreate
from rag_solution.schemas.provider_config_schema import ProviderModelConfigInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateCreate

logger = get_logger(__name__)

def initialize_watsonx_provider(db: Session) -> None:
    """Initialize WatsonX provider configuration if credentials are available."""
    try:
        # Check if WatsonX credentials are available
        if not all([settings.wx_api_key, settings.wx_url, settings.wx_project_id]):
            logger.info("WatsonX credentials not found, skipping initialization")
            return

        provider_service = ProviderConfigService(db)

        # Check if WatsonX provider already exists
        existing_config = provider_service.get_provider_config("watsonx")
        if existing_config:
            logger.info("WatsonX provider already configured")
            return

        # Create default LLM parameters from settings
        parameters = LLMParametersCreate(
            name="watsonx-default",
            max_new_tokens=settings.max_new_tokens,
            temperature=settings.temperature,
            top_k=settings.top_k,
            top_p=settings.top_p,
            repetition_penalty=settings.repetition_penalty
        )

        # Create provider configuration
        provider_config = ProviderModelConfigInput(
            model_id=settings.rag_llm,
            provider_name="watsonx",
            api_key=settings.wx_api_key,
            api_url=settings.wx_url,
            project_id=settings.wx_project_id,
            default_model_id=settings.rag_llm,
            embedding_model=settings.embedding_model,
            is_active=True
        )

        # Create default prompt template
        template_repo = PromptTemplateRepository(db)
        default_template = template_repo.get_default_for_provider("watsonx")
        if not default_template:
            template = PromptTemplateCreate(
                name="watsonx-default",
                provider="watsonx",
                system_prompt="You are an AI assistant specializing in answering questions based on the given context.",
                context_prefix="Context:",
                query_prefix="Question:",
                answer_prefix="Answer:",
                is_default=True
            )
            template_repo.create(template)
            logger.info("Created default prompt template for WatsonX")

        # Register the provider
        provider_service.register_provider_model(
            provider="watsonx",
            model_id=settings.rag_llm,
            parameters=parameters,
            provider_config=provider_config
        )
        logger.info("Successfully initialized WatsonX provider")

    except Exception as e:
        logger.error(f"Error initializing WatsonX provider: {e}")
        raise

def initialize_llm_providers(db: Session) -> None:
    """Initialize all configured LLM providers."""
    try:
        # Initialize WatsonX (primary provider)
        initialize_watsonx_provider(db)

        # Initialize other providers as needed
        # These would be implemented similar to WatsonX when required
        # initialize_openai_provider(db)
        # initialize_anthropic_provider(db)

    except Exception as e:
        logger.error(f"Error during LLM provider initialization: {e}")
        raise
