"""Technique registry for discovering and instantiating techniques.

The registry provides:
- Centralized technique discovery
- Technique instantiation with dependency injection
- Metadata caching for performance
- Pipeline validation
- Technique compatibility checking
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from rag_solution.techniques.base import BaseTechnique, TechniqueMetadata, TechniqueStage

T = TypeVar("T", bound=type[BaseTechnique])

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class TechniqueRegistry:
    """Registry for discovering and instantiating RAG techniques.

    The registry maintains a catalog of all available techniques and provides
    methods for:
    - Registering new techniques
    - Listing available techniques
    - Instantiating techniques with dependency injection
    - Validating technique pipelines
    - Checking technique compatibility

    Usage:
        # Register a technique
        registry.register("my_technique", MyTechniqueClass)

        # Get a technique instance
        technique = registry.get_technique("my_technique")

        # List all techniques
        all_techniques = registry.list_techniques()

        # List techniques by stage
        retrieval_techniques = registry.list_techniques(stage=TechniqueStage.RETRIEVAL)

        # Validate a pipeline
        is_valid, error = registry.validate_pipeline(["hyde", "vector_retrieval", "reranking"])
    """

    def __init__(self) -> None:
        """Initialize the technique registry."""
        self._techniques: dict[str, type[BaseTechnique]] = {}
        self._metadata_cache: dict[str, TechniqueMetadata] = {}
        self._instances: dict[str, BaseTechnique] = {}  # Singleton instances

    def register(
        self, technique_id: str, technique_class: type[BaseTechnique], *, singleton: bool = True
    ) -> None:
        """Register a technique in the registry.

        Args:
            technique_id: Unique identifier for the technique
            technique_class: Class implementing BaseTechnique
            singleton: Whether to reuse a single instance (default: True)

        Raises:
            ValueError: If technique_id is already registered
        """
        if technique_id in self._techniques:
            logger.warning(f"Technique {technique_id} is already registered, overwriting")

        self._techniques[technique_id] = technique_class

        # Cache metadata for performance
        try:
            instance = technique_class()
            self._metadata_cache[technique_id] = instance.get_metadata()

            if singleton:
                self._instances[technique_id] = instance

        except Exception as e:
            logger.error(f"Failed to instantiate technique {technique_id}: {e}")
            raise ValueError(f"Invalid technique class for {technique_id}: {e}") from e

        logger.info(f"Registered technique: {technique_id} ({technique_class.__name__})")

    def unregister(self, technique_id: str) -> None:
        """Unregister a technique from the registry.

        Args:
            technique_id: Unique identifier of the technique to remove
        """
        if technique_id in self._techniques:
            del self._techniques[technique_id]
            self._metadata_cache.pop(technique_id, None)
            self._instances.pop(technique_id, None)
            logger.info(f"Unregistered technique: {technique_id}")

    def get_technique(self, technique_id: str, **kwargs: Any) -> BaseTechnique:
        """Get a technique instance by ID.

        Args:
            technique_id: Unique identifier of the technique
            **kwargs: Additional arguments to pass to technique constructor (if not singleton)

        Returns:
            Instance of the requested technique

        Raises:
            ValueError: If technique_id is not registered
        """
        if technique_id not in self._techniques:
            raise ValueError(
                f"Unknown technique: {technique_id}. "
                f"Available techniques: {list(self._techniques.keys())}"
            )

        # Return singleton instance if available
        if technique_id in self._instances and not kwargs:
            return self._instances[technique_id]

        # Create new instance
        try:
            technique_class = self._techniques[technique_id]
            instance = technique_class(**kwargs)
            return instance
        except Exception as e:
            logger.error(f"Failed to instantiate technique {technique_id}: {e}")
            raise ValueError(f"Failed to create technique {technique_id}: {e}") from e

    def get_metadata(self, technique_id: str) -> TechniqueMetadata:
        """Get metadata for a technique.

        Args:
            technique_id: Unique identifier of the technique

        Returns:
            TechniqueMetadata object

        Raises:
            ValueError: If technique_id is not registered
        """
        if technique_id not in self._metadata_cache:
            raise ValueError(f"Unknown technique: {technique_id}")

        return self._metadata_cache[technique_id]

    def list_techniques(
        self, stage: TechniqueStage | None = None, requires_llm: bool | None = None
    ) -> list[TechniqueMetadata]:
        """List available techniques, optionally filtered.

        Args:
            stage: Filter by pipeline stage (optional)
            requires_llm: Filter by LLM requirement (optional)

        Returns:
            List of TechniqueMetadata objects matching the filters
        """
        techniques = list(self._metadata_cache.values())

        if stage is not None:
            techniques = [t for t in techniques if t.stage == stage]

        if requires_llm is not None:
            techniques = [t for t in techniques if t.requires_llm == requires_llm]

        return techniques

    def validate_pipeline(self, technique_ids: list[str]) -> tuple[bool, str | None]:
        """Validate a technique pipeline configuration.

        Checks:
        1. All techniques exist in the registry
        2. Techniques are ordered by stage (preprocessing -> generation)
        3. No incompatible techniques in the same pipeline
        4. Required dependencies are met

        Args:
            technique_ids: List of technique IDs in pipeline order

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if pipeline is valid
            - error_message: None if valid, error description if invalid
        """
        if not technique_ids:
            return False, "Pipeline cannot be empty"

        # Check all techniques exist
        for technique_id in technique_ids:
            if technique_id not in self._techniques:
                return False, f"Unknown technique: {technique_id}"

        # Get metadata for all techniques
        metadata_list = [self._metadata_cache[tid] for tid in technique_ids]

        # Check stage ordering
        stage_order = [
            TechniqueStage.QUERY_PREPROCESSING,
            TechniqueStage.QUERY_TRANSFORMATION,
            TechniqueStage.RETRIEVAL,
            TechniqueStage.POST_RETRIEVAL,
            TechniqueStage.RERANKING,
            TechniqueStage.COMPRESSION,
            TechniqueStage.GENERATION,
        ]

        prev_stage_index = -1
        for metadata in metadata_list:
            try:
                current_stage_index = stage_order.index(metadata.stage)
            except ValueError:
                return False, f"Unknown stage: {metadata.stage}"

            if current_stage_index < prev_stage_index:
                return False, (
                    f"Invalid stage ordering: {metadata.technique_id} "
                    f"({metadata.stage}) cannot come after previous stage"
                )
            prev_stage_index = current_stage_index

        # Check for incompatibilities
        for i, metadata in enumerate(metadata_list):
            technique_id = technique_ids[i]

            # Check if this technique is incompatible with others in pipeline
            for other_id in technique_ids:
                if other_id == technique_id:
                    continue

                if other_id in metadata.incompatible_with:
                    return False, (
                        f"Incompatible techniques: {technique_id} " f"cannot be used with {other_id}"
                    )

        return True, None

    def get_compatible_techniques(self, technique_id: str) -> list[str]:
        """Get list of techniques compatible with the given technique.

        Args:
            technique_id: Technique to check compatibility for

        Returns:
            List of compatible technique IDs
        """
        if technique_id not in self._metadata_cache:
            return []

        metadata = self._metadata_cache[technique_id]

        # If compatible_with is specified, return that list
        if metadata.compatible_with:
            return metadata.compatible_with

        # Otherwise, return all techniques except incompatible ones
        return [
            tid
            for tid in self._techniques
            if tid not in metadata.incompatible_with and tid != technique_id
        ]

    def is_registered(self, technique_id: str) -> bool:
        """Check if a technique is registered.

        Args:
            technique_id: Technique ID to check

        Returns:
            True if registered, False otherwise
        """
        return technique_id in self._techniques

    def clear(self) -> None:
        """Clear all registered techniques.

        Warning: This will remove all techniques from the registry.
        Primarily useful for testing.
        """
        self._techniques.clear()
        self._metadata_cache.clear()
        self._instances.clear()
        logger.info("Cleared all techniques from registry")


# Global registry instance
# This is the main registry used throughout the application
technique_registry = TechniqueRegistry()


def register_technique(technique_id: str | None = None, *, singleton: bool = True) -> Callable[[T], T]:
    """Decorator for automatically registering techniques.

    Usage:
        @register_technique("my_technique")
        class MyTechnique(BaseTechnique):
            ...

        # Or use the technique_id from the class
        @register_technique()
        class MyTechnique(BaseTechnique):
            technique_id = "my_technique"
            ...

    Args:
        technique_id: Technique ID (optional, uses class.technique_id if not provided)
        singleton: Whether to use singleton instances (default: True)

    Returns:
        Decorator function
    """

    def decorator(technique_class: T) -> T:
        # Determine technique ID
        tid = technique_id
        if tid is None:
            if not hasattr(technique_class, "technique_id"):
                raise ValueError(
                    f"Technique class {technique_class.__name__} must define "
                    f"technique_id or provide it to @register_technique()"
                )
            tid = technique_class.technique_id

        # Register the technique
        technique_registry.register(tid, technique_class, singleton=singleton)

        return technique_class

    return decorator
