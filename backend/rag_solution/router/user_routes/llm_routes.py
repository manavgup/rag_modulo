"""LLM-related routes including parameters and providers."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db
from rag_solution.schemas.llm_parameters_schema import (
    LLMParametersOutput,
    LLMParametersInput
)
from rag_solution.schemas.llm_provider_schema import (
    LLMProviderOutput,
    LLMProviderInput
)
from rag_solution.schemas.llm_model_schema import LLMModelOutput
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService
from core.authorization import authorize_decorator

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# LLM Parameters Routes
@router.get("/{user_id}/llm-parameters", 
    response_model=List[LLMParametersOutput],
    summary="Get LLM parameters",
    description="Retrieve all LLM parameters for a user",
    responses={
        200: {"description": "LLM parameters retrieved successfully"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="user")
async def get_llm_parameters(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> List[LLMParametersOutput]:
    """Retrieve all LLM parameters for a user."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access parameters")
    
    service = LLMParametersService(db)
    try:
        return service.get_parameters(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve LLM parameters: {str(e)}"
        )

@router.post("/{user_id}/llm-parameters", 
    response_model=LLMParametersOutput,
    summary="Create LLM parameters",
    description="Create a new set of LLM parameters for a user"
)
@authorize_decorator(role="user")
async def create_llm_parameters(
    user_id: UUID,
    parameters_input: LLMParametersInput,
    request: Request,
    db: Session = Depends(get_db)
) -> LLMParametersOutput:
    """Create a new set of LLM parameters for a user."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to create parameters")
    
    service = LLMParametersService(db)
    try:
        return service.create_parameters(parameters_input)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create LLM parameters: {str(e)}"
        )

@router.put("/{user_id}/llm-parameters/{parameter_id}", 
    response_model=LLMParametersOutput,
    summary="Update LLM parameters",
    description="Update an existing set of LLM parameters"
)
@authorize_decorator(role="user")
async def update_llm_parameters(
    user_id: UUID,
    parameter_id: UUID,
    parameters_input: LLMParametersInput,
    request: Request,
    db: Session = Depends(get_db)
) -> LLMParametersOutput:
    """Update an existing set of LLM parameters."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to update parameters")
    
    service = LLMParametersService(db)
    try:
        update_data = parameters_input.model_dump(exclude_unset=True)
        return service.update_parameters(parameter_id, update_data)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update LLM parameters: {str(e)}"
        )

@router.delete("/{user_id}/llm-parameters/{parameter_id}", 
    response_model=bool,
    summary="Delete LLM parameters",
    description="Delete an existing set of LLM parameters"
)
@authorize_decorator(role="user")
async def delete_llm_parameters(
    user_id: UUID,
    parameter_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> bool:
    """Delete an existing set of LLM parameters."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to delete parameters")
    
    service = LLMParametersService(db)
    try:
        return service.delete_parameters(parameter_id)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete LLM parameters: {str(e)}"
        )

@router.put("/{user_id}/llm-parameters/{parameter_id}/default", 
    response_model=LLMParametersOutput,
    summary="Set default LLM parameters",
    description="Set a specific set of LLM parameters as default"
)
@authorize_decorator(role="user")
async def set_default_llm_parameters(
    user_id: UUID,
    parameter_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> LLMParametersOutput:
    """Set a specific set of LLM parameters as default."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to set default parameters")
    
    service = LLMParametersService(db)
    try:
        return service.set_default_parameters(parameter_id)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to set default LLM parameters: {str(e)}"
        )

# LLM Provider Routes
@router.get("/{user_id}/llm-providers", 
    response_model=List[LLMProviderOutput],
    summary="Get LLM providers",
    description="Retrieve all LLM providers for a user"
)
@authorize_decorator(role="user")
async def get_llm_providers(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> List[LLMProviderOutput]:
    """Retrieve all LLM providers for a user."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access providers")
    
    service = LLMProviderService(db)
    try:
        return service.get_all_providers(is_active=True)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve LLM providers: {str(e)}"
        )

@router.post("/{user_id}/llm-providers", 
    response_model=LLMProviderOutput,
    summary="Create LLM provider",
    description="Create a new LLM provider configuration"
)
@authorize_decorator(role="user")
async def create_llm_provider(
    user_id: UUID,
    provider_input: LLMProviderInput,
    request: Request,
    db: Session = Depends(get_db)
) -> LLMProviderOutput:
    """Create a new LLM provider configuration."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to create provider")
    
    service = LLMProviderService(db)
    try:
        if not provider_input.user_id:
            provider_input.user_id = user_id
        return service.create_provider(provider_input)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create LLM provider: {str(e)}"
        )

@router.put("/{user_id}/llm-providers/{provider_id}", 
    response_model=LLMProviderOutput,
    summary="Update LLM provider",
    description="Update an existing LLM provider configuration"
)
@authorize_decorator(role="user")
async def update_llm_provider(
    user_id: UUID,
    provider_id: UUID,
    provider_input: LLMProviderInput,
    request: Request,
    db: Session = Depends(get_db)
) -> LLMProviderOutput:
    """Update an existing LLM provider configuration."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to update provider")
    
    service = LLMProviderService(db)
    try:
        update_data = provider_input.model_dump(exclude_unset=True)
        return service.update_provider(provider_id, update_data)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update LLM provider: {str(e)}"
        )

@router.delete("/{user_id}/llm-providers/{provider_id}", 
    response_model=bool,
    summary="Delete LLM provider",
    description="Delete an existing LLM provider configuration"
)
@authorize_decorator(role="user")
async def delete_llm_provider(
    user_id: UUID,
    provider_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> bool:
    """Delete an existing LLM provider configuration."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to delete provider")
    
    service = LLMProviderService(db)
    try:
        return service.delete_provider(provider_id)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete LLM provider: {str(e)}"
        )

@router.get("/{user_id}/llm-providers/models", 
    response_model=List[LLMModelOutput],
    summary="Get provider models",
    description="Retrieve all available models from providers"
)
@authorize_decorator(role="user")
async def get_provider_models(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> List[LLMModelOutput]:
    """Retrieve all available models from providers."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access provider models")
    
    service = LLMProviderService(db)
    try:
        # Get all providers for the user and their models
        providers = service.get_providers_for_user(user_id)
        all_models = []
        for provider in providers:
            models = service.get_available_models(provider.id)
            all_models.extend(models)
        return all_models
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve provider models: {str(e)}"
        )

@router.get("/{user_id}/llm-providers/{provider_id}/models", 
    response_model=List[LLMModelOutput],
    summary="Get provider models",
    description="Retrieve all available models for a specific provider"
)
@authorize_decorator(role="user")
async def get_provider_specific_models(
    user_id: UUID,
    provider_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> List[LLMModelOutput]:
    """Retrieve all available models for a specific provider."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access provider models")
    
    service = LLMProviderService(db)
    try:
        return service.get_provider_models(provider_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve provider models: {str(e)}"
        )
