"""Citation attribution service for post-hoc and semantic similarity-based attribution.

This service provides fallback attribution when LLM-generated citations fail validation.
Implements industry best practices from Anthropic, Perplexity, and LlamaIndex for
deterministic citation attribution.

Key features:
- Semantic similarity-based attribution using embeddings
- Lexical overlap (BM25-style) attribution as fallback
- Citation validation and verification
- Support for chunk-level and sentence-level attribution
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import UUID4

from core.logging_utils import get_logger
from rag_solution.schemas.structured_output_schema import Citation

logger = get_logger("services.citation_attribution")

# Attribution thresholds
SEMANTIC_SIMILARITY_THRESHOLD = 0.75  # Minimum cosine similarity for attribution
LEXICAL_OVERLAP_THRESHOLD = 0.3  # Minimum word overlap ratio for attribution
MIN_EXCERPT_LENGTH = 20  # Minimum characters for excerpt
MAX_EXCERPT_LENGTH = 500  # Maximum characters for excerpt


class CitationAttributionService:
    """Service for post-hoc citation attribution using semantic similarity.

    This service provides deterministic citation attribution as a fallback when
    LLM-generated citations fail validation. It uses semantic similarity and
    lexical overlap to attribute answer sentences to retrieved chunks.

    Attributes:
        embedding_service: Service for generating text embeddings
        similarity_threshold: Minimum similarity score for attribution (default: 0.75)
        lexical_threshold: Minimum lexical overlap for fallback (default: 0.3)
    """

    def __init__(
        self,
        embedding_service: Any | None = None,
        similarity_threshold: float = SEMANTIC_SIMILARITY_THRESHOLD,
        lexical_threshold: float = LEXICAL_OVERLAP_THRESHOLD,
    ) -> None:
        """Initialize citation attribution service.

        Args:
            embedding_service: Optional service for generating embeddings
            similarity_threshold: Minimum cosine similarity for attribution
            lexical_threshold: Minimum lexical overlap ratio for fallback
        """
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
        self.lexical_threshold = lexical_threshold
        self.logger = get_logger(f"{__name__}.CitationAttributionService")

    def attribute_citations(
        self,
        answer: str,
        context_documents: list[dict[str, Any]],
        max_citations: int = 5,
    ) -> list[Citation]:
        """Attribute citations to answer using semantic similarity and lexical overlap.

        This method provides deterministic citation attribution by:
        1. Splitting answer into sentences
        2. Computing similarity between each sentence and retrieved chunks
        3. Attributing chunks with similarity above threshold
        4. Falling back to lexical overlap if semantic similarity unavailable

        Args:
            answer: Generated answer text
            context_documents: Retrieved chunks with metadata
            max_citations: Maximum number of citations to return

        Returns:
            List of attributed citations with relevance scores
        """
        if not context_documents:
            self.logger.warning("No context documents provided for attribution")
            return []

        # Try semantic similarity attribution if embedding service available
        if self.embedding_service:
            try:
                citations = self._semantic_similarity_attribution(answer, context_documents, max_citations)
                if citations:
                    self.logger.info(f"Attributed {len(citations)} citations using semantic similarity")
                    return citations
            except Exception as e:
                self.logger.warning(f"Semantic similarity attribution failed: {e}, falling back to lexical overlap")

        # Fallback to lexical overlap attribution
        citations = self._lexical_overlap_attribution(answer, context_documents, max_citations)
        self.logger.info(f"Attributed {len(citations)} citations using lexical overlap")
        return citations

    def _semantic_similarity_attribution(
        self,
        answer: str,
        context_documents: list[dict[str, Any]],
        max_citations: int,
    ) -> list[Citation]:
        """Attribute citations using semantic similarity (embeddings).

        Args:
            answer: Generated answer text
            context_documents: Retrieved chunks with metadata
            max_citations: Maximum number of citations

        Returns:
            List of citations with semantic similarity scores
        """
        # Split answer into sentences
        sentences = self._split_into_sentences(answer)

        # Get embeddings for answer sentences
        sentence_embeddings = self.embedding_service.get_embeddings(sentences)

        # Get embeddings for context chunks
        chunk_texts = [doc.get("content", "") for doc in context_documents]
        chunk_embeddings = self.embedding_service.get_embeddings(chunk_texts)

        # Compute similarity matrix
        citation_scores: dict[int, float] = {}
        for sent_idx, sent_emb in enumerate(sentence_embeddings):
            for chunk_idx, chunk_emb in enumerate(chunk_embeddings):
                similarity = self._cosine_similarity(sent_emb, chunk_emb)
                if similarity >= self.similarity_threshold:
                    # Track highest similarity score for each chunk
                    if chunk_idx not in citation_scores or similarity > citation_scores[chunk_idx]:
                        citation_scores[chunk_idx] = similarity

        # Create citations for top-scoring chunks
        citations = self._create_citations_from_scores(
            citation_scores,
            context_documents,
            answer,
            max_citations,
        )

        return citations

    def _lexical_overlap_attribution(
        self,
        answer: str,
        context_documents: list[dict[str, Any]],
        max_citations: int,
    ) -> list[Citation]:
        """Attribute citations using lexical overlap (BM25-style).

        Args:
            answer: Generated answer text
            context_documents: Retrieved chunks with metadata
            max_citations: Maximum number of citations

        Returns:
            List of citations with lexical overlap scores
        """
        # Tokenize answer
        answer_words = set(self._tokenize(answer.lower()))

        # Compute overlap with each chunk
        citation_scores: dict[int, float] = {}
        for idx, doc in enumerate(context_documents):
            content = doc.get("content", "")
            chunk_words = set(self._tokenize(content.lower()))

            # Compute Jaccard similarity (overlap / union)
            if chunk_words:
                overlap = len(answer_words & chunk_words)
                union = len(answer_words | chunk_words)
                score = overlap / union if union > 0 else 0.0

                if score >= self.lexical_threshold:
                    citation_scores[idx] = score

        # Create citations for top-scoring chunks
        citations = self._create_citations_from_scores(
            citation_scores,
            context_documents,
            answer,
            max_citations,
        )

        return citations

    def _create_citations_from_scores(
        self,
        citation_scores: dict[int, float],
        context_documents: list[dict[str, Any]],
        answer: str,
        max_citations: int,
    ) -> list[Citation]:
        """Create Citation objects from attribution scores.

        Args:
            citation_scores: Mapping of chunk index to relevance score
            context_documents: Retrieved chunks with metadata
            answer: Generated answer text (for excerpt extraction)
            max_citations: Maximum number of citations

        Returns:
            List of Citation objects sorted by relevance
        """
        citations = []

        # Sort by score (highest first) and limit to max_citations
        sorted_indices = sorted(citation_scores.keys(), key=lambda idx: citation_scores[idx], reverse=True)[
            :max_citations
        ]

        for chunk_idx in sorted_indices:
            doc = context_documents[chunk_idx]
            score = citation_scores[chunk_idx]

            # Extract excerpt from chunk content
            content = doc.get("content", "")
            excerpt = self._extract_excerpt(content, answer)

            # Create citation
            try:
                citation = Citation(
                    document_id=UUID4(doc.get("id")),
                    title=doc.get("title", "Untitled"),
                    excerpt=excerpt,
                    page_number=doc.get("page_number"),
                    relevance_score=round(score, 3),
                    chunk_id=doc.get("chunk_id"),
                )
                citations.append(citation)
            except Exception as e:
                self.logger.warning(f"Failed to create citation for chunk {chunk_idx}: {e}")
                continue

        return citations

    def _extract_excerpt(self, content: str, answer: str) -> str:
        """Extract most relevant excerpt from content.

        Args:
            content: Full chunk content
            answer: Generated answer (for finding relevant section)

        Returns:
            Excerpt of appropriate length
        """
        # Find sentences in content that overlap with answer
        content_sentences = self._split_into_sentences(content)
        answer_words = set(self._tokenize(answer.lower()))

        best_sentence = ""
        best_overlap = 0

        for sentence in content_sentences:
            sentence_words = set(self._tokenize(sentence.lower()))
            overlap = len(answer_words & sentence_words)

            if overlap > best_overlap:
                best_overlap = overlap
                best_sentence = sentence

        # Use best sentence as excerpt, or truncate content if no good match
        if best_sentence and len(best_sentence) >= MIN_EXCERPT_LENGTH:
            excerpt = best_sentence
        else:
            excerpt = content

        # Truncate to max length
        if len(excerpt) > MAX_EXCERPT_LENGTH:
            excerpt = excerpt[:MAX_EXCERPT_LENGTH] + "..."

        # Ensure minimum length
        if len(excerpt) < MIN_EXCERPT_LENGTH:
            excerpt = content[:MAX_EXCERPT_LENGTH] if len(content) > MAX_EXCERPT_LENGTH else content

        return excerpt.strip()

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences using simple heuristics.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Simple sentence splitting on period, exclamation, question mark
        # followed by whitespace or end of string
        sentences = re.split(r"[.!?]+\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words.

        Args:
            text: Input text

        Returns:
            List of word tokens
        """
        # Simple whitespace tokenization with punctuation removal
        words = re.findall(r"\b\w+\b", text.lower())
        return words

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0.0-1.0)
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vectors must have same length: {len(vec1)} != {len(vec2)}")

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def validate_citation_support(
        self,
        citation: Citation,
        context_documents: list[dict[str, Any]],
        min_overlap: float = 0.3,
    ) -> bool:
        """Validate that a citation's excerpt actually appears in the source document.

        Args:
            citation: Citation to validate
            context_documents: Retrieved chunks
            min_overlap: Minimum word overlap ratio to consider valid

        Returns:
            True if citation is supported by source, False otherwise
        """
        # Find the document matching this citation
        doc = next(
            (d for d in context_documents if str(d.get("id")) == str(citation.document_id)),
            None,
        )

        if not doc:
            self.logger.warning(f"Citation references unknown document {citation.document_id}")
            return False

        # Check if excerpt appears in document content
        content = doc.get("content", "").lower()
        excerpt = citation.excerpt.lower()

        # Direct substring match
        if excerpt in content:
            return True

        # Fuzzy match using word overlap
        excerpt_words = set(self._tokenize(excerpt))
        content_words = set(self._tokenize(content))

        if not excerpt_words:
            return False

        overlap_ratio = len(excerpt_words & content_words) / len(excerpt_words)
        return overlap_ratio >= min_overlap
