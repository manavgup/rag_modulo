"""Prompt template routes."""

import logging
from pydantic import UUID4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from rag_solution.core.dependencies import verify_user_access
from rag_solution.file_management.database import get_db
from rag_solution.models.prompt_template import PromptTemplateType
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.prompt_template_service import PromptTemplateService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{user_id}/prompt-templates",
    response_model=list[PromptTemplateOutput],
    summary="Get prompt templates",
    description="Retrieve all prompt templates for a user",
    responses={
        200: {"description": "Prompt templates retrieved successfully"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_prompt_templates(
    user_id: UUID4, db: Session = Depends(get_db), user: UserOutput = Depends(verify_user_access)
) -> list[PromptTemplateOutput]:
    """Retrieve all prompt templates for a user."""
    service = PromptTemplateService(db)
    try:
        return service.get_user_templates(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve prompt templates: {e!s}") from e


@router.post(
    "/{user_id}/prompt-templates",
    response_model=PromptTemplateOutput,
    summary="Create prompt template",
    description="Create a new prompt template for a user",
    responses={
        201: {"description": "Prompt template created successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"},
    },
)
async def create_prompt_template(
    user_id: UUID4, template_input: PromptTemplateInput, db: Session = Depends(get_db), user: UserOutput = Depends(verify_user_access)
) -> PromptTemplateOutput:
    """Create a new prompt template for a user."""
    service = PromptTemplateService(db)
    try:
        if not template_input.user_id:
            template_input.user_id = user_id
        return service.create_template(template_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create prompt template: {e!s}") from e


@router.put(
    "/{user_id}/prompt-templates/{template_id}",
    response_model=PromptTemplateOutput,
    summary="Update prompt template",
    description="Update an existing prompt template",
    responses={
        200: {"description": "Prompt template updated successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Not authorized"},
        404: {"description": "Template not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_prompt_template(
    user_id: UUID4,
    template_id: UUID4,
    template_input: PromptTemplateInput,
    db: Session = Depends(get_db),
    user: UserOutput = Depends(verify_user_access),
) -> PromptTemplateOutput:
    """Update an existing prompt template."""
    service = PromptTemplateService(db)
    try:
        # Ensure user_id is set in the input
        if not template_input.user_id:
            template_input.user_id = user_id
        return service.update_template(template_id, template_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update prompt template: {e!s}") from e


@router.delete(
    "/{user_id}/prompt-templates/{template_id}",
    response_model=bool,
    summary="Delete prompt template",
    description="Delete an existing prompt template",
    responses={
        200: {"description": "Prompt template deleted successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "Template not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_prompt_template(
    user_id: UUID4, template_id: UUID4, db: Session = Depends(get_db), user: UserOutput = Depends(verify_user_access)
) -> bool:
    """Delete an existing prompt template."""
    service = PromptTemplateService(db)
    try:
        return service.delete_template(user_id, template_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete prompt template: {e!s}") from e


@router.put(
    "/{user_id}/prompt-templates/{template_id}/default",
    response_model=PromptTemplateOutput,
    summary="Set default prompt template",
    description="Set a specific prompt template as default",
    responses={
        200: {"description": "Default template set successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "Template not found"},
        500: {"description": "Internal server error"},
    },
)
async def set_default_prompt_template(
    user_id: UUID4, template_id: UUID4, db: Session = Depends(get_db), user: UserOutput = Depends(verify_user_access)
) -> PromptTemplateOutput:
    """Set a specific prompt template as default."""
    service = PromptTemplateService(db)
    try:
        return service.set_default_template(template_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to set default prompt template: {e!s}") from e


@router.get(
    "/{user_id}/prompt-templates/type/{template_type}",
    response_model=list[PromptTemplateOutput],
    summary="Get prompt templates by type",
    description="Retrieve prompt templates for a user by their type",
    responses={
        200: {"description": "Prompt templates retrieved successfully"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_prompt_templates_by_type(
    user_id: UUID4, template_type: PromptTemplateType, db: Session = Depends(get_db), user: UserOutput = Depends(verify_user_access)
) -> list[PromptTemplateOutput]:
    """Retrieve prompt templates for a user by their type."""
    service = PromptTemplateService(db)
    try:
        return service.get_templates_by_type(user_id, template_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve prompt templates: {e!s}") from e
