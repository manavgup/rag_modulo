"""Pipeline configuration routes."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db
from rag_solution.schemas.pipeline_schema import (
    PipelineConfigInput,
    PipelineConfigOutput
)
from rag_solution.services.pipeline_service import PipelineService
from core.authorization import authorize_decorator

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/{user_id}/pipelines", 
    response_model=List[PipelineConfigOutput],
    summary="Get pipeline configurations",
    description="Retrieve all pipeline configurations for a user",
    responses={
        200: {"description": "Pipeline configurations retrieved successfully"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="user")
async def get_pipelines(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> List[PipelineConfigOutput]:
    """Retrieve all pipeline configurations for a user."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access pipelines")
    
    service = PipelineService(db)
    try:
        return service.get_user_pipelines(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve pipeline configurations: {str(e)}"
        )

@router.post("/{user_id}/pipelines", 
    response_model=PipelineConfigOutput,
    summary="Create pipeline configuration",
    description="Create a new pipeline configuration for a user",
    responses={
        201: {"description": "Pipeline configuration created successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="user")
async def create_pipeline(
    user_id: UUID,
    pipeline_input: PipelineConfigInput,
    request: Request,
    db: Session = Depends(get_db)
) -> PipelineConfigOutput:
    """Create a new pipeline configuration for a user."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to create pipeline")
    
    service = PipelineService(db)
    try:
        if not pipeline_input.user_id:
            pipeline_input.user_id = user_id
        return service.create_pipeline(pipeline_input)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create pipeline configuration: {str(e)}"
        )

@router.put("/{user_id}/pipelines/{pipeline_id}", 
    response_model=PipelineConfigOutput,
    summary="Update pipeline configuration",
    description="Update an existing pipeline configuration",
    responses={
        200: {"description": "Pipeline configuration updated successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Not authorized"},
        404: {"description": "Pipeline not found"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="user")
async def update_pipeline(
    user_id: UUID,
    pipeline_id: UUID,
    pipeline_input: PipelineConfigInput,
    request: Request,
    db: Session = Depends(get_db)
) -> PipelineConfigOutput:
    """Update an existing pipeline configuration."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to update pipeline")
    
    service = PipelineService(db)
    try:
        update_data = pipeline_input.model_dump(exclude_unset=True)
        return service.update_pipeline(pipeline_id, update_data)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update pipeline configuration: {str(e)}"
        )

@router.delete("/{user_id}/pipelines/{pipeline_id}", 
    response_model=bool,
    summary="Delete pipeline configuration",
    description="Delete an existing pipeline configuration",
    responses={
        200: {"description": "Pipeline configuration deleted successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "Pipeline not found"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="user")
async def delete_pipeline(
    user_id: UUID,
    pipeline_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> bool:
    """Delete an existing pipeline configuration."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to delete pipeline")
    
    service = PipelineService(db)
    try:
        return service.delete_pipeline(pipeline_id)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete pipeline configuration: {str(e)}"
        )

@router.put("/{user_id}/pipelines/{pipeline_id}/default", 
    response_model=PipelineConfigOutput,
    summary="Set default pipeline",
    description="Set a specific pipeline configuration as default",
    responses={
        200: {"description": "Default pipeline set successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "Pipeline not found"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="user")
async def set_default_pipeline(
    user_id: UUID,
    pipeline_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> PipelineConfigOutput:
    """Set a specific pipeline configuration as default."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to set default pipeline")
    
    service = PipelineService(db)
    try:
        return service.set_default_pipeline(pipeline_id)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to set default pipeline: {str(e)}"
        )
