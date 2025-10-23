"""Concrete implementations of RAG techniques.

This package contains implementations of various RAG techniques that can be
composed into pipelines for dynamic retrieval augmentation.

Available techniques:
- VectorRetrievalTechnique: Vector-based document retrieval
- RerankingTechnique: LLM-based result reranking
- (More techniques to be added as they are implemented)

All techniques are automatically registered with the technique registry
when imported.
"""

# Import all technique implementations to auto-register them
# Note: As new techniques are implemented, import them here to auto-register

__all__ = [
    # Technique implementations will be added here as they're created
]
