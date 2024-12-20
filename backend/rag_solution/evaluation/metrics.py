from typing import Any, Callable, Dict, List, Optional, Type

import numpy as np

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel,Field


class RetrievalMetricResult(BaseModel):
    """Metric result.

    Attributes:
        score (float): Score for the metric
        metadata (Dict[str, Any]): Metadata for the metric result

    """

    score: float = Field(..., description="Score for the metric")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata for the metric result"
    )

    def __str__(self) -> str:
        """String representation."""
        return f"Score: {self.score}\nMetadata: {self.metadata}"

    def __float__(self) -> float:
        """Float representation."""
        return self.score


class BaseRetrievalMetric(BaseModel, ABC):
    """Base class for retrieval metrics."""

    metric_name: str

    @abstractmethod
    def compute(
        self,
        query: Optional[str] = None,
        expected_ids: Optional[List[str]] = None,
        retrieved_ids: Optional[List[str]] = None,
        expected_texts: Optional[List[str]] = None,
        retrieved_texts: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> RetrievalMetricResult:
        """Compute metric.

        Args:
            query (Optional[str]): Query string
            expected_ids (Optional[List[str]]): Expected ids
            retrieved_ids (Optional[List[str]]): Retrieved ids
            **kwargs: Additional keyword arguments

        """

    class Config:
        arbitrary_types_allowed = True


_AGG_FUNC: Dict[str, Callable] = {"mean": np.mean, "median": np.median, "max": np.max}


class HitRate(BaseRetrievalMetric):
    """Hit rate metric."""

    metric_name: str = "hit_rate"

    def compute(
        self,
        query: Optional[str] = None,
        expected_ids: Optional[List[str]] = None,
        retrieved_ids: Optional[List[str]] = None,
        expected_texts: Optional[List[str]] = None,
        retrieved_texts: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> RetrievalMetricResult:
        """Compute metric."""
        if retrieved_ids is None or expected_ids is None:
            raise ValueError("Retrieved ids and expected ids must be provided")
        is_hit = any(id in expected_ids for id in retrieved_ids)
        return RetrievalMetricResult(
            score=1.0 if is_hit else 0.0,
        )


class MRR(BaseRetrievalMetric):
    """MRR metric."""

    metric_name: str = "mrr"

    def compute(
        self,
        query: Optional[str] = None,
        expected_ids: Optional[List[str]] = None,
        retrieved_ids: Optional[List[str]] = None,
        expected_texts: Optional[List[str]] = None,
        retrieved_texts: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> RetrievalMetricResult:
        """Compute metric."""
        if retrieved_ids is None or expected_ids is None:
            raise ValueError("Retrieved ids and expected ids must be provided")
        for i, id in enumerate(retrieved_ids):
            if id in expected_ids:
                return RetrievalMetricResult(
                    score=1.0 / (i + 1),
                )
        return RetrievalMetricResult(
            score=0.0,
        )


METRIC_REGISTRY: Dict[str, Type[BaseRetrievalMetric]] = {
    "hit_rate": HitRate,
    "mrr": MRR,
    # "cohere_rerank_relevancy": CohereRerankRelevancyMetric,
}


def extract_queries(dataset):
    values = []
    for value in dataset.queries.values():
        values.append(value)
    return values


def extract_node_ids(documents):
    # make sure order of node_ids matches the relevance rankings from the retriever
    node_ids = []
    # Assuming the structure has only one key in the outer dictionary

    for doc in documents:
        node_ids.append(f"{doc.metadata['node_id']}")
    # Concatenate node_ids into a single string separated by a comma
    return node_ids


def resolve_metrics(metrics: List[str]) -> List[Type[BaseRetrievalMetric]]:
    """Resolve metrics from list of metric names."""
    for metric in metrics:
        if metric not in METRIC_REGISTRY:
            raise ValueError(f"Invalid metric name: {metric}")

    return [METRIC_REGISTRY[metric] for metric in metrics]


class AnswerSimilarity(BaseModel):
    answer_similarity_rate: int = Field(description="numerical score of the answer quality")
    reasoning: str = Field(
        description="reasoning why the answer_quality score was given"
    )


class Faithfulness(BaseModel):
    faithfulness_rate: str = Field(description="factual consistency of the answer can only take one of these values High,Medium,Low")
    reasoning: str = Field(
        description="A clear explanation of the assessment, referencing specific discrepancies or alignments between the answer and the context."
    )


class AnswerRelevance(BaseModel):
    answer_relevance_rate: str = Field(description="answer relevance rate High,Medium,Low")
    reasoning: str = Field(
        description="reasoning why the answer_relevance rate was given focus on Completeness: Does the answer fully address the question?,Precision: Is the answer free of unnecessary or redundant information?,Is the answer factually consistent with the given question?"
    )


class ContextRelevance(BaseModel):
    context_relevance_rate: int = Field(
        description="score to assess the relevancy of retrieved documents to the question High,Medium,Low"
    )
    reasoning: str = Field(
        description="reasoning why the relevancy_score score was given justify your rating for each document concisely but clearly."
    )

