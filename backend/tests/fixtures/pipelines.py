"""Pipeline configuration fixtures for pytest."""


import pytest

from core.config import settings
from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.llm_provider_schema import LLMProviderOutput
from rag_solution.schemas.pipeline_schema import (
    ChunkingStrategy,
    ContextStrategy,
    PipelineConfigInput,
    PipelineConfigOutput,
    RetrieverType,
)
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.prompt_template_service import PromptTemplateService


@pytest.fixture(scope="session")
def default_pipeline_config(
    pipeline_service: PipelineService,
    base_user: UserOutput,
    base_collection: CollectionOutput,
    ensure_watsonx_provider: LLMProviderOutput,
) -> PipelineConfigOutput:
    """Create default pipeline configuration using service."""
    config_input = PipelineConfigInput(
        name="default-pipeline",
        description="Default test pipeline configuration",
        chunking_strategy=ChunkingStrategy.FIXED,
        embedding_model=settings.embedding_model,
        retriever=RetrieverType.VECTOR,
        context_strategy=ContextStrategy.SIMPLE,
        provider_id=ensure_watsonx_provider.id,
        collection_id=base_collection.id,
        user_id=base_user.id,
        enable_logging=True,
        max_context_length=2048,
        timeout=30.0,
        is_default=True,
    )
    return pipeline_service.create_pipeline(config_input)


@pytest.fixture(scope="session")
def base_pipeline_config(
    base_user: UserOutput,
    base_collection: CollectionOutput,
    llm_parameters_service: LLMParametersService,
    prompt_template_service: PromptTemplateService,
    pipeline_service: PipelineService,
    llm_provider_service: LLMProviderService,
) -> dict[str, object]:
    """Create test configurations for user."""

    # Get existing WatsonX provider
    watsonx_provider = llm_provider_service.get_provider_by_name("watsonx")
    if not watsonx_provider:
        raise ValueError("WatsonX provider not found")

    # Create parameters
    parameters_input = LLMParametersInput(
        name="test-parameters",
        description="Test parameters for pipeline",
        user_id=base_user.id,
        temperature=0.7,
        max_new_tokens=1000,
        top_k=50,
        top_p=0.95,
        is_default=True,
    )
    parameters = llm_parameters_service.create_parameters(parameters_input)

    # Create templates
    templates = {}
    for template_type in [PromptTemplateType.RAG_QUERY, PromptTemplateType.RESPONSE_EVALUATION]:
        template_input = PromptTemplateInput(
            name=f"test-{template_type.value}",
            user_id=base_user.id,
            template_type=template_type,
            template_format="Context:\n{context}\nQuestion:{question}",
            input_variables={
                "context": "Retrieved passages from knowledge base",
                "question": "User's question to answer",
            },
            max_context_length=2048,
            is_default=True,
        )
        templates[template_type] = prompt_template_service.create_template(template_input)

    # Create pipeline config
    pipeline_config = pipeline_service.create_pipeline(
        PipelineConfigInput(
            name="test-pipeline",
            description="Test pipeline configuration",
            chunking_strategy=ChunkingStrategy.FIXED,
            embedding_model="sentence-transformers/all-minilm-l6-v2",
            retriever=RetrieverType.VECTOR,
            context_strategy=ContextStrategy.SIMPLE,
            provider_id=watsonx_provider.id,
            collection_id=base_collection.id,
            user_id=base_user.id,
            enable_logging=True,
            max_context_length=2048,
            timeout=30.0,
        )
    )

    return {"parameters": parameters, "templates": templates, "pipeline": pipeline_config}
