"""Tests for evaluation service with different metrics."""
import pytest
from typing import Dict, Any, List
import numpy as np

from rag_solution.evaluation.evaluator import Evaluator
from rag_solution.evaluation.llm_as_judge_evals import LLMJudge
from rag_solution.evaluation.metrics import (
    calculate_retrieval_metrics,
    calculate_generation_metrics,
    calculate_overall_metrics
)

@pytest.mark.evaluation
class TestEvaluationMetrics:
    """Test evaluation service with different metrics."""

    @pytest.fixture
    def evaluator(self, db_session) -> Evaluator:
        """Create evaluator fixture."""
        return Evaluator(db_session)

    @pytest.fixture
    def llm_judge(self, db_session) -> LLMJudge:
        """Create LLM judge fixture."""
        return LLMJudge(db_session)

    @pytest.fixture
    def test_retrieval_results(self) -> Dict[str, Any]:
        """Test retrieval results."""
        return {
            "query": "Who created Python?",
            "retrieved_documents": [
                {
                    "content": "Python was created by Guido van Rossum.",
                    "score": 0.95,
                    "metadata": {"source": "test.txt", "page": 1}
                },
                {
                    "content": "Python is a high-level programming language.",
                    "score": 0.85,
                    "metadata": {"source": "test.txt", "page": 1}
                }
            ],
            "relevant_documents": [
                {
                    "content": "Python was created by Guido van Rossum.",
                    "metadata": {"source": "test.txt", "page": 1}
                }
            ]
        }

    @pytest.fixture
    def test_generation_results(self) -> Dict[str, Any]:
        """Test generation results."""
        return {
            "query": "Who created Python?",
            "generated_answer": "Python was created by Guido van Rossum.",
            "ground_truth": "Guido van Rossum created Python.",
            "context": [
                "Python was created by Guido van Rossum.",
                "Python is a high-level programming language."
            ]
        }

    @pytest.mark.unit
    async def test_retrieval_metrics(
        self,
        evaluator: Evaluator,
        test_retrieval_results: Dict[str, Any]
    ):
        """Test retrieval evaluation metrics."""
        metrics = await calculate_retrieval_metrics(
            retrieved_docs=test_retrieval_results["retrieved_documents"],
            relevant_docs=test_retrieval_results["relevant_documents"]
        )

        # Verify metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "mrr" in metrics
        assert "ndcg" in metrics

        # Verify metric values
        assert 0 <= metrics["precision"] <= 1
        assert 0 <= metrics["recall"] <= 1
        assert 0 <= metrics["f1_score"] <= 1
        assert 0 <= metrics["mrr"] <= 1
        assert 0 <= metrics["ndcg"] <= 1

        # Verify expected values for this test case
        assert metrics["precision"] == 0.5  # 1 relevant out of 2 retrieved
        assert metrics["recall"] == 1.0  # Found the only relevant document
        assert metrics["f1_score"] == pytest.approx(0.67, abs=0.01)  # Harmonic mean
        assert metrics["mrr"] == 1.0  # Relevant doc is first
        assert metrics["ndcg"] > 0.9  # High NDCG due to relevant doc being first

    @pytest.mark.unit
    async def test_generation_metrics(
        self,
        evaluator: Evaluator,
        test_generation_results: Dict[str, Any]
    ):
        """Test generation evaluation metrics."""
        metrics = await calculate_generation_metrics(
            generated_answer=test_generation_results["generated_answer"],
            ground_truth=test_generation_results["ground_truth"]
        )

        # Verify metrics
        assert "rouge_1" in metrics
        assert "rouge_2" in metrics
        assert "rouge_l" in metrics
        assert "bleu" in metrics
        assert "exact_match" in metrics
        assert "semantic_similarity" in metrics

        # Verify metric values
        assert 0 <= metrics["rouge_1"] <= 1
        assert 0 <= metrics["rouge_2"] <= 1
        assert 0 <= metrics["rouge_l"] <= 1
        assert 0 <= metrics["bleu"] <= 1
        assert isinstance(metrics["exact_match"], bool)
        assert 0 <= metrics["semantic_similarity"] <= 1

        # Verify expected values for this test case
        assert metrics["rouge_1"] > 0.8  # High unigram overlap
        assert metrics["rouge_2"] > 0.7  # High bigram overlap
        assert metrics["rouge_l"] > 0.8  # High longest common subsequence
        assert metrics["bleu"] > 0.7  # High BLEU score
        assert not metrics["exact_match"]  # Different word order
        assert metrics["semantic_similarity"] > 0.9  # High semantic similarity

    @pytest.mark.integration
    async def test_llm_judge_evaluation(
        self,
        llm_judge: LLMJudge,
        test_generation_results: Dict[str, Any]
    ):
        """Test LLM-based evaluation."""
        evaluation = await llm_judge.evaluate_response(
            question=test_generation_results["query"],
            context=test_generation_results["context"],
            response=test_generation_results["generated_answer"],
            ground_truth=test_generation_results["ground_truth"]
        )

        # Verify evaluation results
        assert "relevance_score" in evaluation
        assert "factual_accuracy" in evaluation
        assert "answer_completeness" in evaluation
        assert "context_usage" in evaluation
        assert "overall_quality" in evaluation
        assert "feedback" in evaluation

        # Verify score ranges
        assert 0 <= evaluation["relevance_score"] <= 1
        assert 0 <= evaluation["factual_accuracy"] <= 1
        assert 0 <= evaluation["answer_completeness"] <= 1
        assert 0 <= evaluation["context_usage"] <= 1
        assert 0 <= evaluation["overall_quality"] <= 1

        # Verify expected scores for this test case
        assert evaluation["relevance_score"] > 0.8
        assert evaluation["factual_accuracy"] > 0.9
        assert evaluation["answer_completeness"] > 0.9
        assert evaluation["context_usage"] > 0.8
        assert evaluation["overall_quality"] > 0.8

    @pytest.mark.performance
    async def test_evaluation_performance(
        self,
        evaluator: Evaluator,
        llm_judge: LLMJudge,
        test_retrieval_results: Dict[str, Any],
        test_generation_results: Dict[str, Any]
    ):
        """Test evaluation performance."""
        import time
        import asyncio

        # Measure retrieval metrics performance
        retrieval_start = time.time()
        for _ in range(10):
            await calculate_retrieval_metrics(
                retrieved_docs=test_retrieval_results["retrieved_documents"],
                relevant_docs=test_retrieval_results["relevant_documents"]
            )
        retrieval_time = (time.time() - retrieval_start) / 10

        # Measure generation metrics performance
        generation_start = time.time()
        for _ in range(10):
            await calculate_generation_metrics(
                generated_answer=test_generation_results["generated_answer"],
                ground_truth=test_generation_results["ground_truth"]
            )
        generation_time = (time.time() - generation_start) / 10

        # Measure LLM judge performance
        llm_start = time.time()
        await llm_judge.evaluate_response(
            question=test_generation_results["query"],
            context=test_generation_results["context"],
            response=test_generation_results["generated_answer"],
            ground_truth=test_generation_results["ground_truth"]
        )
        llm_time = time.time() - llm_start

        # Verify performance metrics
        assert retrieval_time < 0.1  # Retrieval metrics should be fast
        assert generation_time < 0.1  # Generation metrics should be fast
        assert llm_time < 5.0  # LLM evaluation should complete within 5 seconds

    @pytest.mark.error
    async def test_evaluation_error_handling(
        self,
        evaluator: Evaluator,
        llm_judge: LLMJudge
    ):
        """Test evaluation error handling."""
        # Test with empty documents
        with pytest.raises(ValueError) as exc:
            await calculate_retrieval_metrics(
                retrieved_docs=[],
                relevant_docs=[]
            )
            assert "empty document list" in str(exc.value).lower()

        # Test with invalid scores
        with pytest.raises(ValueError) as exc:
            await calculate_retrieval_metrics(
                retrieved_docs=[{"content": "test", "score": 1.5}],  # Score > 1
                relevant_docs=[{"content": "test"}]
            )
            assert "invalid score" in str(exc.value).lower()

        # Test with missing ground truth
        with pytest.raises(ValueError) as exc:
            await calculate_generation_metrics(
                generated_answer="test answer",
                ground_truth=""  # Empty ground truth
            )
            assert "missing ground truth" in str(exc.value).lower()

        # Test LLM judge with invalid input
        with pytest.raises(ValueError) as exc:
            await llm_judge.evaluate_response(
                question="",  # Empty question
                context=[],
                response="test",
                ground_truth="test"
            )
            assert "invalid input" in str(exc.value).lower()
