"""Initialize LLM providers during application startup."""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from core.config import settings
from core.logging_utils import get_logger
from rag_solution.services.provider_config_service import ProviderConfigService
from rag_solution.repository.prompt_template_repository import PromptTemplateRepository
from rag_solution.schemas.llm_parameters_schema import LLMParametersCreate
from rag_solution.schemas.provider_config_schema import ProviderConfig, ProviderRuntimeSettings
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

        # Create runtime configuration
        runtime_config = ProviderRuntimeSettings(
            timeout=30,
            max_retries=3,
            batch_size=10,
            retry_delay=1.0,
            concurrency_limit=10,
            stream=False,
            rate_limit=10
        )

        # Create provider configuration
        provider_config = ProviderConfig(
            model_id=settings.rag_llm,
            provider_name="watsonx",
            api_key=settings.wx_api_key,
            api_url=settings.wx_url,
            project_id=settings.wx_project_id,
            default_model_id=settings.rag_llm,
            embedding_model=settings.embedding_model,
            runtime=runtime_config,
            is_active=True
        )

        # Create default prompt template
        template_repo = PromptTemplateRepository(db)
        default_template = template_repo.get_default_for_provider("watsonx")
        if not default_template:
            # Create default chat template
            chat_template = PromptTemplateCreate(
                name="watsonx-chat",
                provider="watsonx",
                system_prompt="You are an AI assistant specializing in answering questions based on the given context.",
                context_prefix="Context:",
                query_prefix="Question:",
                answer_prefix="Answer:",
                is_default=True
            )
            template_repo.create(chat_template)
            logger.info("Created default chat template for WatsonX")

            # Create question generation template
            question_template = PromptTemplateCreate(
                name="watsonx-question-gen",
                provider="watsonx",
                system_prompt="You are an AI assistant specializing in generating insightful questions from given text.",
                context_prefix="Text to generate questions from:\n",
                query_prefix="Generate {num_questions} specific questions based on the text. Questions must be directly answerable from the text. Focus only on information explicitly stated. Each question should end with a question mark.\n",
                answer_prefix="Generated questions:",
                is_default=False
            )
            template_repo.create(question_template)
            logger.info("Created question generation template for WatsonX")

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
