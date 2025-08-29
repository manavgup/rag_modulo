"""Prompt template routes."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.authorization import authorize_decorator
from rag_solution.file_management.database import get_db
from rag_solution.models.prompt_template import PromptTemplateType
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateOutput
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
@authorize_decorator(role="user")
async def get_prompt_templates(
    user_id: UUID, request: Request, db: Session = Depends(get_db)
) -> list[PromptTemplateOutput]:
    """Retrieve all prompt templates for a user."""
    if not hasattr(request.state, "user") or request.state.user["uuid"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access templates")

    service = PromptTemplateService(db)
    try:
        return service.get_user_templates(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve prompt templates: {e!s}")


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
@authorize_decorator(role="user")
async def create_prompt_template(
    user_id: UUID, template_input: PromptTemplateInput, request: Request, db: Session = Depends(get_db)
) -> PromptTemplateOutput:
    """Create a new prompt template for a user."""
    if not hasattr(request.state, "user") or request.state.user["uuid"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to create template")

    service = PromptTemplateService(db)
    try:
        if not template_input.user_id:
            template_input.user_id = user_id
        return service.create_template(template_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create prompt template: {e!s}")


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
@authorize_decorator(role="user")
async def update_prompt_template(
    user_id: UUID,
    template_id: UUID,
    template_input: PromptTemplateInput,
    request: Request,
    db: Session = Depends(get_db),
) -> PromptTemplateOutput:
    """Update an existing prompt template."""
    if not hasattr(request.state, "user") or request.state.user["uuid"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to update template")

    service = PromptTemplateService(db)
    try:
        # Ensure user_id is set in the input
        if not template_input.user_id:
            template_input.user_id = user_id
        return service.update_template(template_id, template_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update prompt template: {e!s}")


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
@authorize_decorator(role="user")
async def delete_prompt_template(
    user_id: UUID, template_id: UUID, request: Request, db: Session = Depends(get_db)
) -> bool:
    """Delete an existing prompt template."""
    if not hasattr(request.state, "user") or request.state.user["uuid"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to delete template")

    service = PromptTemplateService(db)
    try:
        return service.delete_template(user_id, template_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete prompt template: {e!s}")


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
@authorize_decorator(role="user")
async def set_default_prompt_template(
    user_id: UUID, template_id: UUID, request: Request, db: Session = Depends(get_db)
) -> PromptTemplateOutput:
    """Set a specific prompt template as default."""
    if not hasattr(request.state, "user") or request.state.user["uuid"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to set default template")

    service = PromptTemplateService(db)
    try:
        return service.set_default_template(template_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to set default prompt template: {e!s}")


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
@authorize_decorator(role="user")
async def get_prompt_templates_by_type(
    user_id: UUID, template_type: PromptTemplateType, request: Request, db: Session = Depends(get_db)
) -> list[PromptTemplateOutput]:
    """Retrieve prompt templates for a user by their type."""
    if not hasattr(request.state, "user") or request.state.user["uuid"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access templates")

    service = PromptTemplateService(db)
    try:
        return service.get_templates_by_type(user_id, template_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve prompt templates: {e!s}")
