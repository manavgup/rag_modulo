"""Model fixtures for pytest."""

import pytest

from core.config import settings
from core.logging_utils import get_logger
from rag_solution.schemas.llm_model_schema import LLMModelInput, ModelType
from rag_solution.schemas.llm_provider_schema import LLMProviderOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.llm_model_service import LLMModelService

logger = get_logger("tests.fixtures.llm_model")


@pytest.fixture(scope="session")
def base_model_input(ensure_watsonx_provider: LLMProviderOutput) -> LLMModelInput:
    """Create base model input for testing."""
    return LLMModelInput(
        provider_id=ensure_watsonx_provider.id,
        model_id="test-model",
        default_model_id="test-model",
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


@pytest.fixture(scope="session")
def ensure_watsonx_models(session_llm_model_service: LLMModelService, ensure_watsonx_provider: LLMProviderOutput, base_user: UserOutput) -> LLMProviderOutput:
    """Ensure WatsonX models are configured."""
    try:
        provider = ensure_watsonx_provider

        # Create generation model
        gen_model = LLMModelInput(
            provider_id=provider.id,
            model_id=settings.rag_llm or "ibm/granite-3-8b-instruct",
            default_model_id=settings.rag_llm or "ibm/granite-3-8b-instruct",
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
        session_llm_model_service.create_model(gen_model)

        # Create embedding model
        embed_model = LLMModelInput(
            provider_id=provider.id,
            model_id="sentence-transformers/all-minilm-l6-v2",
            default_model_id="sentence-transformers/all-minilm-l6-v2",
            model_type=ModelType.EMBEDDING,
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
        session_llm_model_service.create_model(embed_model)

        logger.info(f"Successfully configured WatsonX models for provider {provider.id}")
        return provider

    except Exception as e:
        logger.error(f"Failed to configure WatsonX models: {e}")
        raise
