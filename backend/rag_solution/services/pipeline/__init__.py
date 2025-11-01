"""
Pipeline architecture for search service.

This module provides a modern pipeline architecture for the search service,
replacing the monolithic search() method with composable stages.
"""

from .base_stage import BaseStage, StageResult
from .pipeline_executor import PipelineExecutor
from .search_context import SearchContext
from .stages import PipelineResolutionStage, QueryEnhancementStage, RetrievalStage

__all__ = [
    "BaseStage",
    "PipelineExecutor",
    "PipelineResolutionStage",
    "QueryEnhancementStage",
    "RetrievalStage",
    "SearchContext",
    "StageResult",
]
