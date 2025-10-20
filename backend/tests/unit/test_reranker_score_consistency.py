"""Test that reranker maintains score consistency between QueryResult and chunk."""

import pytest
from pydantic import UUID4

from rag_solution.generation.providers.base import LLMBase
from rag_solution.retrieval.reranker import LLMReranker, SimpleReranker
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase, PromptTemplateType
from vectordbs.data_types import DocumentChunkMetadata, DocumentChunkWithScore, QueryResult, Source


@pytest.fixture
def sample_query_results():
    """Create sample QueryResults with various scores."""
    results = []
    for i, score in enumerate([0.9, 0.7, 0.5]):
        chunk = DocumentChunkWithScore(
            chunk_id=f"chunk-{i}",
            text=f"Document text {i}",
            score=score,
            metadata=DocumentChunkMetadata(
                source=Source.PDF,
                document_id=f"doc-{i}",
                page_number=1,
                chunk_number=i,
            ),
            document_id=f"doc-{i}",
        )
        results.append(QueryResult(chunk=chunk, score=score, embeddings=[]))
    return results


def test_simple_reranker_maintains_score_consistency(sample_query_results):
    """Test that SimpleReranker maintains score consistency."""
    reranker = SimpleReranker()
    reranked = reranker.rerank("test query", sample_query_results, top_k=3)

    # Verify scores are consistent
    for result in reranked:
        assert result.score == result.chunk.score, (
            f"QueryResult.score ({result.score}) should match " f"chunk.score ({result.chunk.score})"
        )


def test_llm_reranker_maintains_score_consistency():
    """Test that LLMReranker maintains score consistency between QueryResult and chunk."""

    # Create mock LLM provider
    class MockLLM(LLMBase):
        def generate_text(self, user_id, prompt, template=None, variables=None):
            """Return mock scores."""
            if isinstance(prompt, list):
                return ["Score: 9.5", "Score: 8.0", "Score: 6.5"]
            return "Score: 9.5"

    # Create mock template
    class MockTemplate(PromptTemplateBase):
        id: UUID4 = UUID4("00000000-0000-0000-0000-000000000000")
        name: str = "test"
        user_id: UUID4 = UUID4("00000000-0000-0000-0000-000000000000")
        template_type: PromptTemplateType = PromptTemplateType.RERANKING
        template: str = "Score this: {document}"
        is_default: bool = True

    # Create sample results
    results = []
    for i, score in enumerate([0.9, 0.7, 0.5]):
        chunk = DocumentChunkWithScore(
            chunk_id=f"chunk-{i}",
            text=f"Document text {i}",
            score=score,
            metadata=DocumentChunkMetadata(
                source=Source.PDF,
                document_id=f"doc-{i}",
                page_number=1,
                chunk_number=i,
            ),
            document_id=f"doc-{i}",
        )
        results.append(QueryResult(chunk=chunk, score=score, embeddings=[]))

    # Create reranker
    llm = MockLLM()
    template = MockTemplate()
    reranker = LLMReranker(
        llm_provider=llm, user_id=UUID4("00000000-0000-0000-0000-000000000000"), prompt_template=template
    )

    # Rerank
    reranked = reranker.rerank("test query", results, top_k=3)

    # CRITICAL TEST: Verify scores are consistent after reranking
    for result in reranked:
        assert result.score is not None, "QueryResult.score should not be None"
        assert result.chunk is not None, "chunk should not be None"
        assert result.chunk.score is not None, "chunk.score should not be None"
        assert result.score == result.chunk.score, (
            f"FAIL: QueryResult.score ({result.score}) must match " f"chunk.score ({result.chunk.score})"
        )


def test_llm_reranker_updates_both_scores():
    """Test that LLMReranker updates both QueryResult.score and chunk.score."""

    class MockLLM(LLMBase):
        def generate_text(self, user_id, prompt, template=None, variables=None):
            return ["Score: 10.0"]  # Perfect score

    class MockTemplate(PromptTemplateBase):
        id: UUID4 = UUID4("00000000-0000-0000-0000-000000000000")
        name: str = "test"
        user_id: UUID4 = UUID4("00000000-0000-0000-0000-000000000000")
        template_type: PromptTemplateType = PromptTemplateType.RERANKING
        template: str = "Score: {document}"
        is_default: bool = True

    # Original score is low
    chunk = DocumentChunkWithScore(
        chunk_id="chunk-1",
        text="Test document",
        score=0.3,  # Low original score
        metadata=DocumentChunkMetadata(
            source=Source.PDF,
            document_id="doc-1",
            page_number=1,
            chunk_number=1,
        ),
        document_id="doc-1",
    )
    result = QueryResult(chunk=chunk, score=0.3, embeddings=[])

    # Rerank
    llm = MockLLM()
    template = MockTemplate()
    reranker = LLMReranker(
        llm_provider=llm, user_id=UUID4("00000000-0000-0000-0000-000000000000"), prompt_template=template, score_scale=10
    )
    reranked = reranker.rerank("test query", [result], top_k=1)

    # Verify both scores are updated to the new LLM score (10.0/10 = 1.0)
    assert len(reranked) == 1
    assert reranked[0].score == 1.0, f"Expected QueryResult.score=1.0, got {reranked[0].score}"
    assert reranked[0].chunk.score == 1.0, f"Expected chunk.score=1.0, got {reranked[0].chunk.score}"


def test_reranker_with_none_chunk():
    """Test that reranker handles None chunks gracefully."""

    class MockLLM(LLMBase):
        def generate_text(self, user_id, prompt, template=None, variables=None):
            return []  # No response for None chunk

    class MockTemplate(PromptTemplateBase):
        id: UUID4 = UUID4("00000000-0000-0000-0000-000000000000")
        name: str = "test"
        user_id: UUID4 = UUID4("00000000-0000-0000-0000-000000000000")
        template_type: PromptTemplateType = PromptTemplateType.RERANKING
        template: str = "Score: {document}"
        is_default: bool = True

    # Result with None chunk
    result = QueryResult(chunk=None, score=0.5, embeddings=[])

    llm = MockLLM()
    template = MockTemplate()
    reranker = LLMReranker(
        llm_provider=llm, user_id=UUID4("00000000-0000-0000-0000-000000000000"), prompt_template=template
    )

    # Should not crash
    reranked = reranker.rerank("test query", [result], top_k=1)

    # Verify it handles None chunk properly
    assert len(reranked) == 1
    assert reranked[0].chunk is None
