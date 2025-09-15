"""LLM-related routes including parameters and providers."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session

from rag_solution.core.dependencies import get_db, verify_user_access
from rag_solution.schemas.llm_model_schema import LLMModelOutput
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput, LLMParametersOutput
from rag_solution.schemas.llm_provider_schema import LLMProviderInput, LLMProviderOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService

logger = logging.getLogger(__name__)

router = APIRouter()


# LLM Parameters Routes
@router.get(
    "/{user_id}/llm-parameters",
    response_model=list[LLMParametersOutput],
    summary="Get LLM parameters",
    description="Retrieve all LLM parameters for a user",
    responses={
        200: {"description": "LLM parameters retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_llm_parameters(user_id: UUID4, user: Annotated[UserOutput, Depends(verify_user_access)], db: Annotated[Session, Depends(get_db)]) -> list[LLMParametersOutput]:
    """Retrieve all LLM parameters for a user."""
    service = LLMParametersService(db)
    try:
        return service.get_user_parameters(user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve LLM parameters: {e!s}") from e


@router.post(
    "/{user_id}/llm-parameters",
    response_model=LLMParametersOutput,
    summary="Create LLM parameters",
    description="Create a new set of LLM parameters for a user",
)
async def create_llm_parameters(
    user_id: UUID4,
    parameters_input: LLMParametersInput,
    user: Annotated[UserOutput, Depends(verify_user_access)],
    db: Annotated[Session, Depends(get_db)],
) -> LLMParametersOutput:
    """Create a new set of LLM parameters for a user."""
    service = LLMParametersService(db)
    try:
        return service.create_parameters(parameters_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create LLM parameters: {e!s}") from e


@router.put(
    "/{user_id}/llm-parameters/{parameter_id}",
    response_model=LLMParametersOutput,
    summary="Update LLM parameters",
    description="Update an existing set of LLM parameters",
)
async def update_llm_parameters(
    user_id: UUID4,
    parameter_id: UUID4,
    parameters_input: LLMParametersInput,
    user: Annotated[UserOutput, Depends(verify_user_access)],
    db: Annotated[Session, Depends(get_db)],
) -> LLMParametersOutput:
    """Update an existing set of LLM parameters."""
    service = LLMParametersService(db)
    try:
        return service.update_parameters(parameter_id, parameters_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update LLM parameters: {e!s}") from e


@router.delete(
    "/{user_id}/llm-parameters/{parameter_id}",
    response_model=bool,
    summary="Delete LLM parameters",
    description="Delete an existing set of LLM parameters",
)
async def delete_llm_parameters(
    user_id: UUID4,
    parameter_id: UUID4,
    user: Annotated[UserOutput, Depends(verify_user_access)],
    db: Annotated[Session, Depends(get_db)],
) -> bool:
    """Delete an existing set of LLM parameters."""
    service = LLMParametersService(db)
    try:
        service.delete_parameters(parameter_id)
        return True
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete LLM parameters: {e!s}") from e


@router.put(
    "/{user_id}/llm-parameters/{parameter_id}/default",
    response_model=LLMParametersOutput,
    summary="Set default LLM parameters",
    description="Set a specific set of LLM parameters as default",
)
async def set_default_llm_parameters(
    user_id: UUID4,
    parameter_id: UUID4,
    user: Annotated[UserOutput, Depends(verify_user_access)],
    db: Annotated[Session, Depends(get_db)],
) -> LLMParametersOutput:
    """Set a specific set of LLM parameters as default."""
    service = LLMParametersService(db)
    try:
        return service.set_default_parameters(parameter_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to set default LLM parameters: {e!s}") from e


# LLM Provider Routes
@router.get(
    "/{user_id}/llm-providers",
    response_model=list[LLMProviderOutput],
    summary="Get LLM providers",
    description="Retrieve all LLM providers for a user",
)
async def get_llm_providers(user_id: UUID4, user: Annotated[UserOutput, Depends(verify_user_access)], db: Annotated[Session, Depends(get_db)]) -> list[LLMProviderOutput]:
    """Retrieve all LLM providers for a user."""
    service = LLMProviderService(db)
    try:
        return service.get_all_providers(is_active=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve LLM providers: {e!s}") from e


@router.post(
    "/{user_id}/llm-providers",
    response_model=LLMProviderOutput,
    summary="Create LLM provider",
    description="Create a new LLM provider configuration",
)
async def create_llm_provider(
    user_id: UUID4,
    provider_input: LLMProviderInput,
    user: Annotated[UserOutput, Depends(verify_user_access)],
    db: Annotated[Session, Depends(get_db)],
) -> LLMProviderOutput:
    """Create a new LLM provider configuration."""
    service = LLMProviderService(db)
    try:
        if not provider_input.user_id:
            provider_input.user_id = user_id
        return service.create_provider(provider_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create LLM provider: {e!s}") from e


@router.put(
    "/{user_id}/llm-providers/{provider_id}",
    response_model=LLMProviderOutput,
    summary="Update LLM provider",
    description="Update an existing LLM provider configuration",
)
async def update_llm_provider(
    user_id: UUID4,
    provider_id: UUID4,
    provider_input: LLMProviderInput,
    user: Annotated[UserOutput, Depends(verify_user_access)],
    db: Annotated[Session, Depends(get_db)],
) -> LLMProviderOutput | None:
    """Update an existing LLM provider configuration."""
    service = LLMProviderService(db)
    try:
        update_data = provider_input.model_dump(exclude_unset=True)
        return service.update_provider(provider_id, update_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update LLM provider: {e!s}") from e


@router.delete(
    "/{user_id}/llm-providers/{provider_id}",
    response_model=bool,
    summary="Delete LLM provider",
    description="Delete an existing LLM provider configuration",
)
async def delete_llm_provider(
    user_id: UUID4,
    provider_id: UUID4,
    user: Annotated[UserOutput, Depends(verify_user_access)],
    db: Annotated[Session, Depends(get_db)],
) -> bool:
    """Delete an existing LLM provider configuration."""
    service = LLMProviderService(db)
    try:
        return service.delete_provider(provider_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete LLM provider: {e!s}") from e


@router.get(
    "/{user_id}/llm-providers/models",
    response_model=list[LLMModelOutput],
    summary="Get provider models",
    description="Retrieve all available models from providers",
)
async def get_provider_models(user_id: UUID4, user: Annotated[UserOutput, Depends(verify_user_access)], db: Annotated[Session, Depends(get_db)]) -> list[LLMModelOutput]:
    """Retrieve all available models from providers."""
    service = LLMProviderService(db)
    try:
        # Get all active providers and their models
        providers = service.get_all_providers(is_active=True)
        all_models = []
        for provider in providers:
            models = service.get_provider_models(provider.id)
            all_models.extend(models)
        return all_models
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve provider models: {e!s}") from e


@router.get(
    "/{user_id}/llm-providers/{provider_id}/models",
    response_model=list[LLMModelOutput],
    summary="Get provider models",
    description="Retrieve all available models for a specific provider",
)
async def get_provider_specific_models(
    user_id: UUID4,
    provider_id: UUID4,
    user: Annotated[UserOutput, Depends(verify_user_access)],
    db: Annotated[Session, Depends(get_db)],
) -> list[LLMModelOutput]:
    """Retrieve all available models for a specific provider."""
    service = LLMProviderService(db)
    try:
        return service.get_provider_models(provider_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve provider models: {e!s}") from e
