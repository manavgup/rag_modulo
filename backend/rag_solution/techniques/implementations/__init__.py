"""Concrete implementations of RAG techniques.

This package contains implementations of various RAG techniques that can be
composed into pipelines for dynamic retrieval augmentation.

Available techniques (wrapping existing infrastructure):
- VectorRetrievalTechnique: Vector search (wraps existing VectorRetriever)
- HybridRetrievalTechnique: Vector + keyword (wraps existing HybridRetriever)
- FusionRetrievalTechnique: Alias for HybridRetrievalTechnique
- LLMRerankingTechnique: LLM-based reranking (wraps existing LLMReranker)
- RerankingTechnique: Alias for LLMRerankingTechnique

All techniques are automatically registered with the technique registry
when imported.
"""

# Import adapter techniques to auto-register them
# These wrap existing retrieval infrastructure
from rag_solution.techniques.implementations.adapters import (
    FusionRetrievalTechnique,
    HybridRetrievalTechnique,
    LLMRerankingTechnique,
    RerankingTechnique,
    VectorRetrievalTechnique,
)

__all__ = [
    "FusionRetrievalTechnique",
    "HybridRetrievalTechnique",
    "LLMRerankingTechnique",
    "RerankingTechnique",
    "VectorRetrievalTechnique",
]
