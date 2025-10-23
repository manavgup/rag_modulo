from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db
from rag_solution.schemas.llm_model_schema import LLMModelInput, LLMModelOutput, LLMModelUpdate, ModelType
from rag_solution.schemas.llm_provider_schema import LLMProviderInput, LLMProviderOutput, LLMProviderUpdate
from rag_solution.services.llm_provider_service import LLMProviderService

router = APIRouter(
    prefix="/api/llm-providers",
    tags=["LLM Providers"],
)


# Dependency Injection
def get_service(db: Annotated[Session, Depends(get_db)]) -> LLMProviderService:
    return LLMProviderService(db)


# -------------------------------
# PROVIDER ROUTES
# -------------------------------


@router.post("/", response_model=LLMProviderOutput)
def create_provider(
    provider_input: LLMProviderInput, service: Annotated[LLMProviderService, Depends(get_service)]
) -> LLMProviderOutput:
    """
    Create a new LLM Provider.
    """
    return service.create_provider(provider_input)


@router.get("/", response_model=list[LLMProviderOutput])
def get_all_providers(
    service: Annotated[LLMProviderService, Depends(get_service)], is_active: bool | None = None
) -> list[LLMProviderOutput]:
    """
    Retrieve all LLM Providers.
    """
    return service.get_all_providers(is_active)


@router.get("/{provider_id}", response_model=LLMProviderOutput)
def get_provider(provider_id: UUID4, service: Annotated[LLMProviderService, Depends(get_service)]) -> LLMProviderOutput:
    """
    Get a specific LLM Provider by ID.
    """
    provider = service.get_provider_by_id(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.put("/{provider_id}", response_model=LLMProviderOutput)
def update_provider(
    provider_id: UUID4, updates: LLMProviderUpdate, service: Annotated[LLMProviderService, Depends(get_service)]
) -> LLMProviderOutput:
    """
    Update a specific LLM Provider with partial updates.

    Accepts LLMProviderUpdate with optional fields for partial updates.
    Raises 404 if provider not found.
    """
    return service.update_provider(provider_id, updates)


@router.delete("/{provider_id}")
def delete_provider(provider_id: UUID4, service: Annotated[LLMProviderService, Depends(get_service)]) -> dict[str, str]:
    """
    Soft delete an LLM Provider.
    """
    success = service.delete_provider(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Provider deleted successfully"}


# -------------------------------
# PROVIDER MODEL ROUTES
# -------------------------------


@router.post("/models/", response_model=LLMModelOutput)
def create_provider_model(
    model_input: LLMModelInput, service: Annotated[LLMProviderService, Depends(get_service)]
) -> LLMModelOutput:
    """
    Create a new Model for an LLM Provider.
    """
    # Extract provider_id from model_input and pass model_data as dict
    provider_id = model_input.provider_id
    model_data = model_input.model_dump(exclude={"provider_id"})
    return service.create_provider_model(provider_id, model_data)


@router.get("/models/provider/{provider_id}", response_model=list[LLMModelOutput])
def get_models_by_provider(
    provider_id: UUID4, service: Annotated[LLMProviderService, Depends(get_service)]
) -> list[LLMModelOutput]:
    """
    Get all Models associated with an LLM Provider.
    """
    return service.get_models_by_provider(provider_id)


@router.get("/models/type/{model_type}", response_model=list[LLMModelOutput])
def get_models_by_type(
    model_type: ModelType, service: Annotated[LLMProviderService, Depends(get_service)]
) -> list[LLMModelOutput]:
    """
    Get Models filtered by type (e.g., 'generation', 'embedding').
    """
    return service.get_models_by_type(model_type)


@router.get("/models/{model_id}", response_model=LLMModelOutput)
def get_model_by_id(model_id: UUID4, service: Annotated[LLMProviderService, Depends(get_service)]) -> LLMModelOutput:
    """
    Get a specific Model by ID.

    Raises 404 if model not found.
    """
    return service.get_model_by_id(model_id)


@router.put("/models/{model_id}", response_model=LLMModelOutput)
def update_model(
    model_id: UUID4, updates: LLMModelUpdate, service: Annotated[LLMProviderService, Depends(get_service)]
) -> LLMModelOutput:
    """
    Update a specific Model with partial updates.

    Accepts LLMModelUpdate with optional fields for partial updates.
    Raises 404 if model not found.
    """
    return service.update_model(model_id, updates)


@router.delete("/models/{model_id}")
def delete_model(model_id: UUID4, service: Annotated[LLMProviderService, Depends(get_service)]) -> dict[str, str]:
    """
    Soft delete a Model.
    """
    success = service.delete_model(model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model deleted successfully"}


# -------------------------------
# PROVIDER WITH MODELS
# -------------------------------


@router.get("/{provider_id}/with-models")
def get_provider_with_models(provider_id: UUID4, service: Annotated[LLMProviderService, Depends(get_service)]) -> Any:
    """
    Get a Provider with all its associated Models.
    """
    provider = service.get_provider_with_models(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider
