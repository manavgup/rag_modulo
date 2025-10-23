"""RAG Technique System - Dynamic technique selection and composition.

This package provides a framework for dynamically selecting and composing
RAG techniques at runtime. It enables users to configure which retrieval
augmentation techniques to apply on a per-query basis without code changes.

Key components:
- base: Core abstractions (BaseTechnique, TechniqueContext, etc.)
- registry: Technique discovery and instantiation
- pipeline: Pipeline builder and executor
- implementations: Concrete technique implementations
"""

from rag_solution.techniques.base import (
    BaseTechnique,
    TechniqueContext,
    TechniqueMetadata,
    TechniqueResult,
    TechniqueStage,
)
from rag_solution.techniques.pipeline import TechniquePipeline, TechniquePipelineBuilder
from rag_solution.techniques.registry import TechniqueRegistry, technique_registry

__all__ = [
    # Base abstractions
    "BaseTechnique",
    "TechniqueContext",
    "TechniqueMetadata",
    "TechniqueResult",
    "TechniqueStage",
    # Pipeline
    "TechniquePipeline",
    "TechniquePipelineBuilder",
    # Registry
    "TechniqueRegistry",
    "technique_registry",
]
