"""Pipeline configuration routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from rag_solution.core.dependencies import verify_user_access
from rag_solution.file_management.database import get_db
from rag_solution.schemas.pipeline_schema import PipelineConfigInput, PipelineConfigOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{user_id}/pipelines",
    response_model=list[PipelineConfigOutput],
    summary="Get pipeline configurations",
    description="Retrieve all pipeline configurations for a user",
    responses={
        200: {"description": "Pipeline configurations retrieved successfully"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_pipelines(
    user_id: UUID4,
    db: Session = Depends(get_db),
    user: UserOutput = Depends(verify_user_access),
    settings: Annotated[Settings, Depends(get_settings)] = Depends(get_settings)
) -> list[PipelineConfigOutput]:
    """Retrieve all pipeline configurations for a user."""
    service = PipelineService(db, settings)
    try:
        return service.get_user_pipelines(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve pipeline configurations: {e!s}") from e


@router.post(
    "/{user_id}/pipelines",
    response_model=PipelineConfigOutput,
    summary="Create pipeline configuration",
    description="Create a new pipeline configuration for a user",
    responses={
        201: {"description": "Pipeline configuration created successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"},
    },
)
async def create_pipeline(
    user_id: UUID4,
    pipeline_input: PipelineConfigInput,
    db: Session = Depends(get_db),
    user: UserOutput = Depends(verify_user_access),
    settings: Annotated[Settings, Depends(get_settings)] = Depends(get_settings)
) -> PipelineConfigOutput:
    """Create a new pipeline configuration for a user."""
    service = PipelineService(db, settings)
    try:
        if not pipeline_input.user_id:
            pipeline_input.user_id = user_id
        return service.create_pipeline(pipeline_input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create pipeline configuration: {e!s}") from e


@router.put(
    "/{user_id}/pipelines/{pipeline_id}",
    response_model=PipelineConfigOutput,
    summary="Update pipeline configuration",
    description="Update an existing pipeline configuration",
    responses={
        200: {"description": "Pipeline configuration updated successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Not authorized"},
        404: {"description": "Pipeline not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_pipeline(
    user_id: UUID4,
    pipeline_id: UUID4,
    pipeline_input: PipelineConfigInput,
    db: Session = Depends(get_db),
    user: UserOutput = Depends(verify_user_access),
    settings: Annotated[Settings, Depends(get_settings)] = Depends(get_settings)
) -> PipelineConfigOutput:
    """Update an existing pipeline configuration."""
    service = PipelineService(db, settings)
    try:
        return service.update_pipeline(pipeline_id, pipeline_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update pipeline configuration: {e!s}") from e


@router.delete(
    "/{user_id}/pipelines/{pipeline_id}",
    response_model=bool,
    summary="Delete pipeline configuration",
    description="Delete an existing pipeline configuration",
    responses={
        200: {"description": "Pipeline configuration deleted successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "Pipeline not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_pipeline(
    user_id: UUID4,
    pipeline_id: UUID4,
    db: Session = Depends(get_db),
    user: UserOutput = Depends(verify_user_access),
    settings: Annotated[Settings, Depends(get_settings)] = Depends(get_settings)
) -> bool:
    """Delete an existing pipeline configuration."""
    service = PipelineService(db, settings)
    try:
        return service.delete_pipeline(pipeline_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete pipeline configuration: {e!s}") from e


@router.put(
    "/{user_id}/pipelines/{pipeline_id}/default",
    response_model=PipelineConfigOutput,
    summary="Set default pipeline",
    description="Set a specific pipeline configuration as default",
    responses={
        200: {"description": "Default pipeline set successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "Pipeline not found"},
        500: {"description": "Internal server error"},
    },
)
async def set_default_pipeline(
    user_id: UUID4,
    pipeline_id: UUID4,
    db: Session = Depends(get_db),
    user: UserOutput = Depends(verify_user_access),
    settings: Annotated[Settings, Depends(get_settings)] = Depends(get_settings)
) -> PipelineConfigOutput:
    """Set a specific pipeline configuration as default."""
    service = PipelineService(db, settings)
    try:
        return service.set_default_pipeline(pipeline_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to set default pipeline: {e!s}") from e
