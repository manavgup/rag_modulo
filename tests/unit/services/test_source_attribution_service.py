"""Unit tests for SourceAttributionService."""


import pytest
from rag_solution.schemas.chain_of_thought_schema import (
    ReasoningStep,
    SourceAttribution,
    SourceSummary,
)
from rag_solution.services.source_attribution_service import SourceAttributionService


class TestSourceAttributionService:
    """Test cases for SourceAttributionService."""

    @pytest.fixture
    def service(self) -> SourceAttributionService:
        """Create a SourceAttributionService instance."""
        return SourceAttributionService()

    @pytest.fixture
    def sample_source_attribution(self) -> SourceAttribution:
        """Create a sample source attribution."""
        return SourceAttribution(
            document_id="doc_123",
            document_title="Test Document",
            relevance_score=0.85,
            excerpt="This is a test excerpt from the document",
            chunk_index=1,
            retrieval_rank=1,
        )

    @pytest.fixture
    def sample_reasoning_steps(self) -> list[ReasoningStep]:
        """Create sample reasoning steps with source attributions."""
        return [
            ReasoningStep(
                step_number=1,
                question="First step question",
                intermediate_answer="First answer",
                confidence_score=0.8,
                source_attributions=[
                    SourceAttribution(
                        document_id="doc_1",
                        document_title="Document 1",
                        relevance_score=0.9,
                        excerpt="Excerpt 1",
                        retrieval_rank=1,
                    ),
                    SourceAttribution(
                        document_id="doc_2",
                        document_title="Document 2",
                        relevance_score=0.75,
                        excerpt="Excerpt 2",
                        retrieval_rank=2,
                    ),
                ],
            ),
            ReasoningStep(
                step_number=2,
                question="Second step question",
                intermediate_answer="Second answer",
                confidence_score=0.9,
                source_attributions=[
                    SourceAttribution(
                        document_id="doc_1",  # Duplicate from step 1
                        document_title="Document 1",
                        relevance_score=0.85,  # Different score
                        excerpt="Excerpt 1 modified",
                        retrieval_rank=1,
                    ),
                    SourceAttribution(
                        document_id="doc_3",
                        document_title="Document 3",
                        relevance_score=0.8,
                        excerpt="Excerpt 3",
                        retrieval_rank=2,
                    ),
                ],
            ),
        ]

    # ============================================================================
    # INITIALIZATION TESTS
    # ============================================================================

    def test_init(self, service: SourceAttributionService) -> None:
        """Test SourceAttributionService initialization."""
        assert service._source_cache == {}

    # ============================================================================
    # CREATE SOURCE ATTRIBUTION TESTS
    # ============================================================================

    def test_create_source_attribution_minimal(self, service: SourceAttributionService) -> None:
        """Test creating source attribution with minimal required fields."""
        attribution = service.create_source_attribution(
            document_id="doc_123",
            relevance_score=0.75,
        )

        assert attribution.document_id == "doc_123"
        assert attribution.relevance_score == 0.75
        assert attribution.document_title is None
        assert attribution.excerpt is None
        assert attribution.chunk_index is None
        assert attribution.retrieval_rank is None

        # Should be cached
        assert "doc_123" in service._source_cache
        assert service._source_cache["doc_123"] == attribution

    def test_create_source_attribution_full(self, service: SourceAttributionService) -> None:
        """Test creating source attribution with all fields."""
        attribution = service.create_source_attribution(
            document_id="doc_456",
            relevance_score=0.95,
            document_title="Complete Document",
            excerpt="Full excerpt text",
            chunk_index=5,
            retrieval_rank=2,
        )

        assert attribution.document_id == "doc_456"
        assert attribution.relevance_score == 0.95
        assert attribution.document_title == "Complete Document"
        assert attribution.excerpt == "Full excerpt text"
        assert attribution.chunk_index == 5
        assert attribution.retrieval_rank == 2

        # Should be cached
        assert "doc_456" in service._source_cache

    def test_create_source_attribution_caching(self, service: SourceAttributionService) -> None:
        """Test that source attributions are cached properly."""
        # Create first attribution
        attr1 = service.create_source_attribution(
            document_id="doc_cache",
            relevance_score=0.5,
        )

        # Create second attribution with same ID
        attr2 = service.create_source_attribution(
            document_id="doc_cache",
            relevance_score=0.9,
        )

        # Cache should contain the latest version
        assert service._source_cache["doc_cache"] == attr2
        assert service._source_cache["doc_cache"].relevance_score == 0.9

    # ============================================================================
    # EXTRACT SOURCES FROM CONTEXT TESTS
    # ============================================================================

    def test_extract_sources_from_empty_context(self, service: SourceAttributionService) -> None:
        """Test extracting sources from empty context documents."""
        attributions = service.extract_sources_from_context(
            context_documents=[],
            search_results=None,
        )

        assert attributions == []

    def test_extract_sources_from_context_documents_only(self, service: SourceAttributionService) -> None:
        """Test extracting sources from context documents without search results."""
        context_documents = [
            "First document content",
            "Second document content with more text",
            "Third document",
        ]

        attributions = service.extract_sources_from_context(
            context_documents=context_documents,
            search_results=None,
        )

        assert len(attributions) == 3
        assert attributions[0].document_id == "context_doc_0"
        assert attributions[0].relevance_score == 1.0
        assert attributions[0].retrieval_rank == 1

        assert attributions[1].document_id == "context_doc_1"
        assert attributions[1].relevance_score == 0.9
        assert attributions[1].retrieval_rank == 2

        assert attributions[2].document_id == "context_doc_2"
        assert attributions[2].relevance_score == 0.8
        assert attributions[2].retrieval_rank == 3

    def test_extract_sources_from_context_with_id(self, service: SourceAttributionService) -> None:
        """Test extracting sources from context with embedded document IDs."""
        context_documents = [
            "id: doc_abc123 Some content here",
            "id: doc_xyz789 More content",
        ]

        attributions = service.extract_sources_from_context(
            context_documents=context_documents,
            search_results=None,
        )

        assert len(attributions) == 2
        assert attributions[0].document_id == "doc_abc123"
        assert attributions[1].document_id == "doc_xyz789"

    def test_extract_sources_from_context_with_malformed_id(self, service: SourceAttributionService) -> None:
        """Test extracting sources from context with malformed ID."""
        context_documents = [
            "id: Some content without proper ID format",
        ]

        attributions = service.extract_sources_from_context(
            context_documents=context_documents,
            search_results=None,
        )

        assert len(attributions) == 1
        # Should extract the ID even if format is unexpected
        assert "Some" in attributions[0].document_id

    def test_extract_sources_from_context_with_id_parsing_exception(self, service: SourceAttributionService) -> None:
        """Test extracting sources from context when ID parsing raises exception."""
        # Test IndexError - no content after "id:"
        context_documents = [
            "id:",
        ]

        attributions = service.extract_sources_from_context(
            context_documents=context_documents,
            search_results=None,
        )

        assert len(attributions) == 1
        # Should fall back to default ID
        assert attributions[0].document_id == "context_doc_0"

    def test_extract_sources_from_context_skip_empty(self, service: SourceAttributionService) -> None:
        """Test that empty context documents are skipped."""
        context_documents = [
            "Valid content",
            "",
            "   ",
            "More valid content",
        ]

        attributions = service.extract_sources_from_context(
            context_documents=context_documents,
            search_results=None,
        )

        assert len(attributions) == 2
        assert attributions[0].document_id == "context_doc_0"
        assert attributions[1].document_id == "context_doc_3"

    def test_extract_sources_from_search_results(self, service: SourceAttributionService) -> None:
        """Test extracting sources from structured search results."""
        search_results = [
            {
                "document_id": "doc_1",
                "title": "First Document",
                "score": 0.95,
                "content": "This is the first document with some content",
                "chunk_index": 0,
            },
            {
                "document_id": "doc_2",
                "title": "Second Document",
                "score": 0.85,
                "content": "Second document content",
                "chunk_index": 1,
            },
        ]

        attributions = service.extract_sources_from_context(
            context_documents=[],
            search_results=search_results,
        )

        assert len(attributions) == 2
        assert attributions[0].document_id == "doc_1"
        assert attributions[0].document_title == "First Document"
        assert attributions[0].relevance_score == 0.95
        assert attributions[0].excerpt == "This is the first document with some content"
        assert attributions[0].chunk_index == 0
        assert attributions[0].retrieval_rank == 1

        assert attributions[1].document_id == "doc_2"
        assert attributions[1].retrieval_rank == 2

    def test_extract_sources_from_search_results_alternative_keys(self, service: SourceAttributionService) -> None:
        """Test extracting sources with alternative key names."""
        search_results = [
            {
                "document_id": "doc_1",
                "document_title": "Alt Title",  # Alternative key
                "relevance_score": 0.9,  # Alternative key
                "text": "Alt text content",  # Alternative key
            },
        ]

        attributions = service.extract_sources_from_context(
            context_documents=[],
            search_results=search_results,
        )

        assert len(attributions) == 1
        assert attributions[0].document_title == "Alt Title"
        assert attributions[0].relevance_score == 0.9
        assert attributions[0].excerpt == "Alt text content"

    def test_extract_sources_from_search_results_missing_fields(self, service: SourceAttributionService) -> None:
        """Test extracting sources with missing optional fields."""
        search_results = [
            {
                "document_id": "doc_minimal",
                # Missing most fields
            },
        ]

        attributions = service.extract_sources_from_context(
            context_documents=[],
            search_results=search_results,
        )

        assert len(attributions) == 1
        assert attributions[0].document_id == "doc_minimal"
        assert attributions[0].document_title is None
        assert attributions[0].relevance_score == 0.5  # Default
        assert attributions[0].excerpt == ""
        assert attributions[0].chunk_index is None

    def test_extract_sources_from_search_results_type_conversion(self, service: SourceAttributionService) -> None:
        """Test type conversion for search result fields."""
        search_results = [
            {
                "document_id": 12345,  # Integer ID
                "title": 67890,  # Integer title
                "score": "0.75",  # String score (invalid)
                "content": 123,  # Integer content
                "chunk_index": "5",  # String chunk_index
            },
        ]

        attributions = service.extract_sources_from_context(
            context_documents=[],
            search_results=search_results,
        )

        assert len(attributions) == 1
        assert attributions[0].document_id == "12345"  # Converted to string
        assert attributions[0].document_title == "67890"  # Converted to string
        assert attributions[0].relevance_score == 0.5  # Default due to invalid type
        assert attributions[0].excerpt == "123"  # Converted to string
        assert attributions[0].chunk_index == 5  # Converted to int

    def test_extract_sources_from_search_results_invalid_chunk_index(self, service: SourceAttributionService) -> None:
        """Test handling of invalid chunk_index values."""
        search_results = [
            {
                "document_id": "doc_1",
                "chunk_index": "invalid",  # Cannot convert to int
            },
        ]

        attributions = service.extract_sources_from_context(
            context_documents=[],
            search_results=search_results,
        )

        assert len(attributions) == 1
        assert attributions[0].chunk_index is None

    def test_extract_sources_long_excerpt_truncation(self, service: SourceAttributionService) -> None:
        """Test that long excerpts are truncated to 200 characters."""
        long_content = "a" * 300

        search_results = [
            {
                "document_id": "doc_1",
                "content": long_content,
            },
        ]

        attributions = service.extract_sources_from_context(
            context_documents=[],
            search_results=search_results,
        )

        assert len(attributions[0].excerpt) == 200
        assert attributions[0].excerpt == "a" * 200

    def test_extract_sources_context_precedence_over_search_results(self, service: SourceAttributionService) -> None:
        """Test that search_results take precedence over context_documents."""
        context_documents = ["This should be ignored"]
        search_results = [{"document_id": "doc_1", "score": 0.9}]

        attributions = service.extract_sources_from_context(
            context_documents=context_documents,
            search_results=search_results,
        )

        # Should use search_results, not context_documents
        assert len(attributions) == 1
        assert attributions[0].document_id == "doc_1"

    # ============================================================================
    # AGGREGATE SOURCES ACROSS STEPS TESTS
    # ============================================================================

    def test_aggregate_sources_empty_steps(self, service: SourceAttributionService) -> None:
        """Test aggregating sources from empty reasoning steps."""
        summary = service.aggregate_sources_across_steps([])

        assert summary.all_sources == []
        assert summary.primary_sources == []
        assert summary.source_usage_by_step == {}

    def test_aggregate_sources_single_step(self, service: SourceAttributionService) -> None:
        """Test aggregating sources from a single reasoning step."""
        steps = [
            ReasoningStep(
                step_number=1,
                question="Test question",
                intermediate_answer="Test answer",
                source_attributions=[
                    SourceAttribution(
                        document_id="doc_1",
                        relevance_score=0.9,
                        document_title="Doc 1",
                    ),
                ],
            ),
        ]

        summary = service.aggregate_sources_across_steps(steps)

        assert len(summary.all_sources) == 1
        assert summary.all_sources[0].document_id == "doc_1"
        assert len(summary.primary_sources) == 1
        assert summary.source_usage_by_step[1] == ["doc_1"]

    def test_aggregate_sources_multiple_steps(self, service: SourceAttributionService, sample_reasoning_steps: list[ReasoningStep]) -> None:
        """Test aggregating sources from multiple reasoning steps."""
        summary = service.aggregate_sources_across_steps(sample_reasoning_steps)

        # Should have 3 unique sources (doc_1, doc_2, doc_3)
        assert len(summary.all_sources) == 3

        # Sources should be sorted by relevance score (descending)
        assert summary.all_sources[0].document_id == "doc_1"  # 0.9 (highest)
        assert summary.all_sources[1].document_id == "doc_3"  # 0.8
        assert summary.all_sources[2].document_id == "doc_2"  # 0.75

        # Step usage tracking
        assert len(summary.source_usage_by_step) == 2
        assert summary.source_usage_by_step[1] == ["doc_1", "doc_2"]
        assert summary.source_usage_by_step[2] == ["doc_1", "doc_3"]

    def test_aggregate_sources_deduplication(self, service: SourceAttributionService, sample_reasoning_steps: list[ReasoningStep]) -> None:
        """Test that duplicate sources are deduplicated with highest relevance."""
        summary = service.aggregate_sources_across_steps(sample_reasoning_steps)

        # doc_1 appears in both steps with scores 0.9 and 0.85
        # Should keep the highest score (0.9)
        doc_1_sources = [s for s in summary.all_sources if s.document_id == "doc_1"]
        assert len(doc_1_sources) == 1
        assert doc_1_sources[0].relevance_score == 0.9

    def test_aggregate_sources_deduplication_keeps_higher_score(self, service: SourceAttributionService) -> None:
        """Test that deduplication keeps the source with higher relevance score."""
        steps = [
            ReasoningStep(
                step_number=1,
                question="Test",
                intermediate_answer="Test",
                source_attributions=[
                    SourceAttribution(document_id="doc_1", relevance_score=0.5),
                ],
            ),
            ReasoningStep(
                step_number=2,
                question="Test",
                intermediate_answer="Test",
                source_attributions=[
                    SourceAttribution(document_id="doc_1", relevance_score=0.9),  # Higher score in step 2
                ],
            ),
        ]

        summary = service.aggregate_sources_across_steps(steps)

        # Should keep the higher score (0.9) from step 2
        doc_1_sources = [s for s in summary.all_sources if s.document_id == "doc_1"]
        assert len(doc_1_sources) == 1
        assert doc_1_sources[0].relevance_score == 0.9

    def test_aggregate_sources_primary_sources_high_relevance(self, service: SourceAttributionService) -> None:
        """Test primary sources selection with high relevance scores."""
        steps = [
            ReasoningStep(
                step_number=1,
                question="Test",
                intermediate_answer="Test",
                source_attributions=[
                    SourceAttribution(document_id="doc_1", relevance_score=0.95),
                    SourceAttribution(document_id="doc_2", relevance_score=0.85),
                    SourceAttribution(document_id="doc_3", relevance_score=0.75),
                    SourceAttribution(document_id="doc_4", relevance_score=0.72),
                ],
            ),
        ]

        summary = service.aggregate_sources_across_steps(steps)

        # Primary sources are top 3 with relevance > 0.7
        assert len(summary.primary_sources) == 3
        assert summary.primary_sources[0].document_id == "doc_1"
        assert summary.primary_sources[1].document_id == "doc_2"
        assert summary.primary_sources[2].document_id == "doc_3"

    def test_aggregate_sources_primary_sources_low_relevance(self, service: SourceAttributionService) -> None:
        """Test primary sources selection when all have low relevance."""
        steps = [
            ReasoningStep(
                step_number=1,
                question="Test",
                intermediate_answer="Test",
                source_attributions=[
                    SourceAttribution(document_id="doc_1", relevance_score=0.5),
                    SourceAttribution(document_id="doc_2", relevance_score=0.4),
                    SourceAttribution(document_id="doc_3", relevance_score=0.3),
                    SourceAttribution(document_id="doc_4", relevance_score=0.2),
                ],
            ),
        ]

        summary = service.aggregate_sources_across_steps(steps)

        # No sources > 0.7, so take top 3
        assert len(summary.primary_sources) == 3
        assert summary.primary_sources[0].relevance_score == 0.5
        assert summary.primary_sources[1].relevance_score == 0.4
        assert summary.primary_sources[2].relevance_score == 0.3

    def test_aggregate_sources_primary_sources_less_than_three(self, service: SourceAttributionService) -> None:
        """Test primary sources selection with less than 3 sources."""
        steps = [
            ReasoningStep(
                step_number=1,
                question="Test",
                intermediate_answer="Test",
                source_attributions=[
                    SourceAttribution(document_id="doc_1", relevance_score=0.9),
                    SourceAttribution(document_id="doc_2", relevance_score=0.6),
                ],
            ),
        ]

        summary = service.aggregate_sources_across_steps(steps)

        # Should include both sources (only 1 > 0.7, but limit is 3)
        assert len(summary.primary_sources) == 1
        assert summary.primary_sources[0].document_id == "doc_1"

    def test_aggregate_sources_no_sources(self, service: SourceAttributionService) -> None:
        """Test aggregating sources when steps have no attributions."""
        steps = [
            ReasoningStep(
                step_number=1,
                question="Test",
                intermediate_answer="Test",
                source_attributions=[],
            ),
        ]

        summary = service.aggregate_sources_across_steps(steps)

        assert summary.all_sources == []
        assert summary.primary_sources == []
        assert summary.source_usage_by_step[1] == []

    # ============================================================================
    # ENHANCE REASONING STEP WITH SOURCES TESTS
    # ============================================================================

    def test_enhance_reasoning_step_with_retrieved_documents(self, service: SourceAttributionService) -> None:
        """Test enhancing a reasoning step with retrieved documents."""
        step = ReasoningStep(
            step_number=1,
            question="Test question",
            intermediate_answer="Test answer",
        )

        retrieved_documents = [
            {
                "document_id": "doc_1",
                "title": "Document 1",
                "score": 0.9,
                "content": "Document content",
            },
        ]

        enhanced_step = service.enhance_reasoning_step_with_sources(
            step=step,
            retrieved_documents=retrieved_documents,
        )

        assert len(enhanced_step.source_attributions) == 1
        assert enhanced_step.source_attributions[0].document_id == "doc_1"
        assert enhanced_step.source_attributions[0].relevance_score == 0.9

    def test_enhance_reasoning_step_with_context_used(self, service: SourceAttributionService) -> None:
        """Test enhancing a reasoning step using existing context_used field."""
        step = ReasoningStep(
            step_number=1,
            question="Test question",
            intermediate_answer="Test answer",
            context_used=["Context document 1", "Context document 2"],
        )

        enhanced_step = service.enhance_reasoning_step_with_sources(
            step=step,
            retrieved_documents=None,
        )

        assert len(enhanced_step.source_attributions) == 2
        assert enhanced_step.source_attributions[0].document_id == "context_doc_0"
        assert enhanced_step.source_attributions[1].document_id == "context_doc_1"

    def test_enhance_reasoning_step_prioritizes_retrieved_documents(self, service: SourceAttributionService) -> None:
        """Test that retrieved_documents take precedence over context_used."""
        step = ReasoningStep(
            step_number=1,
            question="Test question",
            intermediate_answer="Test answer",
            context_used=["This should be ignored"],
        )

        retrieved_documents = [{"document_id": "doc_1", "score": 0.9}]

        enhanced_step = service.enhance_reasoning_step_with_sources(
            step=step,
            retrieved_documents=retrieved_documents,
        )

        assert len(enhanced_step.source_attributions) == 1
        assert enhanced_step.source_attributions[0].document_id == "doc_1"

    def test_enhance_reasoning_step_empty_sources(self, service: SourceAttributionService) -> None:
        """Test enhancing a reasoning step with no sources available."""
        step = ReasoningStep(
            step_number=1,
            question="Test question",
            intermediate_answer="Test answer",
            context_used=[],
        )

        enhanced_step = service.enhance_reasoning_step_with_sources(
            step=step,
            retrieved_documents=None,
        )

        assert enhanced_step.source_attributions == []

    # ============================================================================
    # FORMAT SOURCES FOR DISPLAY TESTS
    # ============================================================================

    def test_format_sources_for_display_basic(self, service: SourceAttributionService) -> None:
        """Test formatting sources for display with basic source summary."""
        source_summary = SourceSummary(
            all_sources=[
                SourceAttribution(
                    document_id="doc_1",
                    document_title="Document 1",
                    relevance_score=0.95,
                    excerpt="Excerpt from doc 1",
                    retrieval_rank=1,
                ),
                SourceAttribution(
                    document_id="doc_2",
                    document_title="Document 2",
                    relevance_score=0.85,
                    excerpt="Excerpt from doc 2",
                    retrieval_rank=2,
                ),
            ],
            primary_sources=[
                SourceAttribution(
                    document_id="doc_1",
                    document_title="Document 1",
                    relevance_score=0.95,
                    excerpt="Excerpt from doc 1",
                    retrieval_rank=1,
                ),
            ],
            source_usage_by_step={
                1: ["doc_1"],
                2: ["doc_1", "doc_2"],
            },
        )

        formatted = service.format_sources_for_display(source_summary, include_excerpts=True)

        assert formatted["total_sources"] == 2
        assert len(formatted["primary_sources"]) == 1
        assert len(formatted["all_sources"]) == 2

        # Check primary source formatting
        primary = formatted["primary_sources"][0]
        assert primary["document_id"] == "doc_1"
        assert primary["title"] == "Document 1"
        assert primary["relevance"] == 0.95
        assert primary["rank"] == 1
        assert primary["excerpt"] == "Excerpt from doc 1"

        # Check step breakdown
        assert "step_1" in formatted["step_breakdown"]
        assert formatted["step_breakdown"]["step_1"]["step_number"] == 1
        assert formatted["step_breakdown"]["step_1"]["sources_used"] == 1
        assert formatted["step_breakdown"]["step_1"]["document_ids"] == ["doc_1"]

    def test_format_sources_for_display_without_excerpts(self, service: SourceAttributionService) -> None:
        """Test formatting sources without including excerpts."""
        source_summary = SourceSummary(
            all_sources=[
                SourceAttribution(
                    document_id="doc_1",
                    relevance_score=0.9,
                    excerpt="This should not appear",
                ),
            ],
            primary_sources=[
                SourceAttribution(
                    document_id="doc_1",
                    relevance_score=0.9,
                    excerpt="This should not appear",
                ),
            ],
            source_usage_by_step={1: ["doc_1"]},
        )

        formatted = service.format_sources_for_display(source_summary, include_excerpts=False)

        # Excerpts should not be included
        assert "excerpt" not in formatted["primary_sources"][0]
        assert "excerpt" not in formatted["all_sources"][0]

    def test_format_sources_for_display_missing_titles(self, service: SourceAttributionService) -> None:
        """Test formatting sources with missing document titles."""
        source_summary = SourceSummary(
            all_sources=[
                SourceAttribution(
                    document_id="doc_no_title",
                    relevance_score=0.8,
                ),
            ],
            primary_sources=[],
            source_usage_by_step={},
        )

        formatted = service.format_sources_for_display(source_summary)

        # Should use document_id as fallback for title
        assert formatted["all_sources"][0]["title"] == "doc_no_title"

    def test_format_sources_for_display_relevance_rounding(self, service: SourceAttributionService) -> None:
        """Test that relevance scores are rounded to 2 decimal places."""
        source_summary = SourceSummary(
            all_sources=[
                SourceAttribution(
                    document_id="doc_1",
                    relevance_score=0.123456789,
                ),
            ],
            primary_sources=[],
            source_usage_by_step={},
        )

        formatted = service.format_sources_for_display(source_summary)

        assert formatted["all_sources"][0]["relevance"] == 0.12

    def test_format_sources_for_display_no_retrieval_rank(self, service: SourceAttributionService) -> None:
        """Test formatting sources without retrieval rank."""
        source_summary = SourceSummary(
            all_sources=[],
            primary_sources=[
                SourceAttribution(
                    document_id="doc_1",
                    relevance_score=0.9,
                    retrieval_rank=None,
                ),
            ],
            source_usage_by_step={},
        )

        formatted = service.format_sources_for_display(source_summary)

        # Rank should not be included when None
        assert "rank" not in formatted["primary_sources"][0]

    def test_format_sources_for_display_empty_summary(self, service: SourceAttributionService) -> None:
        """Test formatting an empty source summary."""
        source_summary = SourceSummary(
            all_sources=[],
            primary_sources=[],
            source_usage_by_step={},
        )

        formatted = service.format_sources_for_display(source_summary)

        assert formatted["total_sources"] == 0
        assert formatted["primary_sources"] == []
        assert formatted["all_sources"] == []
        assert formatted["step_breakdown"] == {}

    def test_format_sources_for_display_multiple_steps(self, service: SourceAttributionService) -> None:
        """Test formatting sources with multiple reasoning steps."""
        source_summary = SourceSummary(
            all_sources=[
                SourceAttribution(document_id="doc_1", relevance_score=0.9),
                SourceAttribution(document_id="doc_2", relevance_score=0.8),
                SourceAttribution(document_id="doc_3", relevance_score=0.7),
            ],
            primary_sources=[],
            source_usage_by_step={
                1: ["doc_1"],
                2: ["doc_1", "doc_2"],
                3: ["doc_2", "doc_3"],
            },
        )

        formatted = service.format_sources_for_display(source_summary)

        assert len(formatted["step_breakdown"]) == 3
        assert formatted["step_breakdown"]["step_1"]["sources_used"] == 1
        assert formatted["step_breakdown"]["step_2"]["sources_used"] == 2
        assert formatted["step_breakdown"]["step_3"]["sources_used"] == 2
        assert formatted["step_breakdown"]["step_3"]["document_ids"] == ["doc_2", "doc_3"]

    # ============================================================================
    # EDGE CASES AND ERROR HANDLING TESTS
    # ============================================================================

    def test_multiple_service_instances_independent_caches(self) -> None:
        """Test that multiple service instances have independent caches."""
        service1 = SourceAttributionService()
        service2 = SourceAttributionService()

        service1.create_source_attribution(document_id="doc_1", relevance_score=0.5)

        assert "doc_1" in service1._source_cache
        assert "doc_1" not in service2._source_cache

    def test_extract_sources_with_unicode_content(self, service: SourceAttributionService) -> None:
        """Test extracting sources with unicode characters."""
        context_documents = [
            "Document with unicode: 你好世界 🌍",
            "id: doc_unicode émojis 🎉",
        ]

        attributions = service.extract_sources_from_context(
            context_documents=context_documents,
            search_results=None,
        )

        assert len(attributions) == 2
        assert "你好世界" in attributions[0].excerpt
        assert attributions[1].document_id == "doc_unicode"

    def test_aggregate_sources_preserves_metadata(self, service: SourceAttributionService) -> None:
        """Test that aggregation preserves source metadata."""
        steps = [
            ReasoningStep(
                step_number=1,
                question="Test",
                intermediate_answer="Test",
                source_attributions=[
                    SourceAttribution(
                        document_id="doc_1",
                        document_title="Important Doc",
                        relevance_score=0.9,
                        excerpt="Important excerpt",
                        chunk_index=5,
                        retrieval_rank=1,
                    ),
                ],
            ),
        ]

        summary = service.aggregate_sources_across_steps(steps)

        source = summary.all_sources[0]
        assert source.document_title == "Important Doc"
        assert source.excerpt == "Important excerpt"
        assert source.chunk_index == 5
        assert source.retrieval_rank == 1

    def test_extract_sources_with_very_long_context(self, service: SourceAttributionService) -> None:
        """Test extracting sources from very long context documents."""
        long_context = "x" * 10000

        context_documents = [long_context]

        attributions = service.extract_sources_from_context(
            context_documents=context_documents,
            search_results=None,
        )

        assert len(attributions) == 1
        # Should truncate to 200 characters
        assert len(attributions[0].excerpt) == 200

    def test_format_sources_comprehensive_output(self, service: SourceAttributionService) -> None:
        """Test comprehensive output formatting with all fields."""
        source_summary = SourceSummary(
            all_sources=[
                SourceAttribution(
                    document_id="doc_1",
                    document_title="Title 1",
                    relevance_score=0.95,
                    excerpt="Excerpt 1",
                    chunk_index=0,
                    retrieval_rank=1,
                ),
                SourceAttribution(
                    document_id="doc_2",
                    document_title="Title 2",
                    relevance_score=0.85,
                    excerpt="Excerpt 2",
                    chunk_index=1,
                    retrieval_rank=2,
                ),
            ],
            primary_sources=[
                SourceAttribution(
                    document_id="doc_1",
                    document_title="Title 1",
                    relevance_score=0.95,
                    excerpt="Excerpt 1",
                    chunk_index=0,
                    retrieval_rank=1,
                ),
            ],
            source_usage_by_step={
                1: ["doc_1"],
                2: ["doc_1", "doc_2"],
            },
        )

        formatted = service.format_sources_for_display(source_summary, include_excerpts=True)

        # Verify all expected keys are present
        assert "total_sources" in formatted
        assert "primary_sources" in formatted
        assert "all_sources" in formatted
        assert "step_breakdown" in formatted

        # Verify structure is correct
        assert isinstance(formatted["total_sources"], int)
        assert isinstance(formatted["primary_sources"], list)
        assert isinstance(formatted["all_sources"], list)
        assert isinstance(formatted["step_breakdown"], dict)
