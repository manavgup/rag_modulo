"""Unit tests for hierarchical chunking module."""

# pylint: disable=redefined-outer-name,import-error
# Justification: pytest fixtures are meant to be redefined as parameters
# import-error: pylint can't resolve paths when run standalone, but tests work fine

import pytest
from backend.rag_solution.data_ingestion.hierarchical_chunking import (
    HierarchicalChunk,
    create_hierarchical_chunks,
    create_sentence_based_hierarchical_chunks,
    get_child_chunks,
    get_chunk_with_parents,
    get_parent_for_chunk,
)


@pytest.fixture
def sample_text() -> str:
    """Create sample text for testing."""
    return (
        "Machine learning is a subset of artificial intelligence. "
        "It focuses on enabling computers to learn from data. "
        "Deep learning is a specialized form of machine learning. "
        "It uses neural networks with multiple layers. "
        "These networks can process complex patterns in data. "
        "Applications include image recognition and natural language processing. "
        "The field has grown rapidly in recent years. "
        "Many industries now use machine learning for various tasks."
    )


@pytest.fixture
def long_text() -> str:
    """Create longer text for hierarchical testing."""
    paragraphs = [
        "Natural language processing (NLP) is a branch of artificial intelligence. "
        "It deals with the interaction between computers and human language. "
        "NLP combines computational linguistics with machine learning. "
        "The goal is to enable computers to understand, interpret, and generate human language.",
        "Common NLP tasks include text classification and sentiment analysis. "
        "Named entity recognition identifies key information in text. "
        "Machine translation converts text between languages. "
        "Question answering systems respond to user queries.",
        "Modern NLP relies heavily on deep learning models. "
        "Transformer architectures have revolutionized the field. "
        "Models like BERT and GPT have achieved remarkable results. "
        "These systems can now understand context and nuance in language.",
    ]
    return " ".join(paragraphs)


class TestHierarchicalChunk:
    """Tests for HierarchicalChunk dataclass."""

    def test_chunk_creation(self) -> None:
        """Test basic chunk creation."""
        chunk = HierarchicalChunk(
            chunk_id="test-123",
            text="Sample text",
            parent_id=None,
            level=0,
        )

        assert chunk.chunk_id == "test-123"
        assert chunk.text == "Sample text"
        assert chunk.parent_id is None
        assert chunk.level == 0
        assert chunk.child_ids == []

    def test_chunk_with_parent(self) -> None:
        """Test chunk with parent relationship."""
        parent = HierarchicalChunk(chunk_id="parent-1", text="Parent text", level=0)
        child = HierarchicalChunk(chunk_id="child-1", text="Child text", parent_id="parent-1", level=1)

        assert child.parent_id == parent.chunk_id
        assert child.level == 1


class TestCreateHierarchicalChunks:
    """Tests for create_hierarchical_chunks function."""

    def test_empty_text(self) -> None:
        """Test handling of empty text."""
        chunks = create_hierarchical_chunks("")
        assert len(chunks) == 0

    def test_basic_hierarchy_creation(self, sample_text: str) -> None:
        """Test creating basic 2-level hierarchy."""
        chunks = create_hierarchical_chunks(
            sample_text,
            parent_chunk_size=200,
            child_chunk_size=50,
            overlap=10,
            levels=2,
        )

        # Should have both parent and child chunks
        assert len(chunks) > 0

        parents = [c for c in chunks if c.level == 0]
        children = [c for c in chunks if c.level == 1]

        assert len(parents) > 0
        assert len(children) > 0
        assert len(children) > len(parents)  # More children than parents

    def test_three_level_hierarchy(self, long_text: str) -> None:
        """Test creating 3-level hierarchy with root."""
        chunks = create_hierarchical_chunks(
            long_text,
            parent_chunk_size=300,
            child_chunk_size=100,
            overlap=20,
            levels=3,
        )

        root_chunks = [c for c in chunks if c.level == 0]
        parent_chunks = [c for c in chunks if c.level == 1]
        child_chunks = [c for c in chunks if c.level == 2]

        # Should have exactly 1 root
        assert len(root_chunks) == 1
        assert len(parent_chunks) > 0
        assert len(child_chunks) > 0

        # Root should have children
        root = root_chunks[0]
        assert len(root.child_ids) > 0  # type: ignore

    def test_parent_child_relationships(self, sample_text: str) -> None:
        """Test that parent-child relationships are correctly established."""
        chunks = create_hierarchical_chunks(
            sample_text,
            parent_chunk_size=150,
            child_chunk_size=40,
            levels=2,
        )

        parents = [c for c in chunks if c.level == 0]
        children = [c for c in chunks if c.level == 1]

        # Each child should have a parent
        for child in children:
            assert child.parent_id is not None
            parent = next((p for p in parents if p.chunk_id == child.parent_id), None)
            assert parent is not None
            assert child.chunk_id in parent.child_ids  # type: ignore

    def test_chunk_text_overlap(self, sample_text: str) -> None:
        """Test that chunks have appropriate overlap."""
        chunks = create_hierarchical_chunks(
            sample_text,
            parent_chunk_size=100,
            child_chunk_size=50,
            overlap=10,
            levels=2,
        )

        children = [c for c in chunks if c.level == 1]
        if len(children) > 1:
            # Check that consecutive chunks have some text overlap
            for i in range(len(children) - 1):
                # Overlap is approximate due to text finding logic
                assert (
                    children[i].end_index > children[i + 1].start_index
                    or children[i + 1].start_index - children[i].end_index < 20
                )

    def test_start_end_indices(self, sample_text: str) -> None:
        """Test that start and end indices are correctly set."""
        chunks = create_hierarchical_chunks(sample_text, levels=2)

        for chunk in chunks:
            assert chunk.start_index >= 0
            assert chunk.end_index > chunk.start_index
            assert chunk.end_index <= len(sample_text)


class TestSentenceBasedHierarchicalChunks:
    """Tests for sentence-based hierarchical chunking."""

    def test_empty_text(self) -> None:
        """Test handling of empty text."""
        chunks = create_sentence_based_hierarchical_chunks("")
        assert len(chunks) == 0

    def test_sentence_grouping(self, sample_text: str) -> None:
        """Test that sentences are grouped correctly."""
        chunks = create_sentence_based_hierarchical_chunks(
            sample_text,
            sentences_per_child=2,
            children_per_parent=3,
        )

        assert len(chunks) > 0

        parents = [c for c in chunks if c.level == 0]
        children = [c for c in chunks if c.level == 1]

        assert len(parents) > 0
        assert len(children) > 0

    def test_parent_contains_child_text(self, sample_text: str) -> None:
        """Test that parent chunks contain their children's text."""
        chunks = create_sentence_based_hierarchical_chunks(
            sample_text,
            sentences_per_child=2,
            children_per_parent=4,
        )

        parents = {c.chunk_id: c for c in chunks if c.level == 0}
        children = [c for c in chunks if c.level == 1]

        for child in children:
            if child.parent_id and child.parent_id in parents:
                parent = parents[child.parent_id]
                # Child text should be substring of parent text (allowing for whitespace differences)
                assert child.text.strip() in parent.text or parent.text in child.text


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_child_chunks(self, sample_text: str) -> None:
        """Test extracting only child chunks."""
        all_chunks = create_hierarchical_chunks(sample_text, levels=2)
        child_chunks = get_child_chunks(all_chunks)

        # All returned chunks should be at the highest level
        max_level = max(c.level for c in all_chunks)
        assert all(c.level == max_level for c in child_chunks)

    def test_get_child_chunks_empty(self) -> None:
        """Test get_child_chunks with empty list."""
        assert get_child_chunks([]) == []

    def test_get_parent_for_chunk(self, sample_text: str) -> None:
        """Test finding parent for a chunk."""
        all_chunks = create_hierarchical_chunks(sample_text, levels=2)
        children = [c for c in all_chunks if c.level == 1]

        if children:
            child = children[0]
            parent = get_parent_for_chunk(child.chunk_id, all_chunks)

            assert parent is not None
            assert parent.chunk_id == child.parent_id
            assert child.chunk_id in parent.child_ids  # type: ignore

    def test_get_parent_for_root_chunk(self, sample_text: str) -> None:
        """Test that root chunks have no parent."""
        all_chunks = create_hierarchical_chunks(sample_text, levels=2)
        root = next(c for c in all_chunks if c.level == 0)

        parent = get_parent_for_chunk(root.chunk_id, all_chunks)
        assert parent is None

    def test_get_parent_nonexistent_chunk(self, sample_text: str) -> None:
        """Test finding parent for non-existent chunk."""
        all_chunks = create_hierarchical_chunks(sample_text, levels=2)
        parent = get_parent_for_chunk("nonexistent-id", all_chunks)

        assert parent is None

    def test_get_chunk_with_parents(self, sample_text: str) -> None:
        """Test retrieving chunk with its parent hierarchy."""
        all_chunks = create_hierarchical_chunks(sample_text, levels=3)
        children = [c for c in all_chunks if c.level == 2]

        if children:
            child = children[0]
            hierarchy = get_chunk_with_parents(child.chunk_id, all_chunks)

            # Should include child, parent, and potentially root
            assert len(hierarchy) > 0
            assert hierarchy[0].chunk_id == child.chunk_id

            # Check parent chain
            for i in range(len(hierarchy) - 1):
                current = hierarchy[i]
                parent = hierarchy[i + 1]
                assert current.parent_id == parent.chunk_id

    def test_get_chunk_with_siblings(self, sample_text: str) -> None:
        """Test retrieving chunk with siblings."""
        all_chunks = create_hierarchical_chunks(sample_text, levels=2)
        children = [c for c in all_chunks if c.level == 1]

        if len(children) > 1:
            child = children[0]
            hierarchy = get_chunk_with_parents(child.chunk_id, all_chunks, include_siblings=True)

            # Should include target chunk, siblings, and parent
            assert len(hierarchy) > 1

            # First chunk should be the target
            assert hierarchy[0].chunk_id == child.chunk_id

            # Should have siblings
            siblings = [c for c in hierarchy if c.level == child.level and c.chunk_id != child.chunk_id]
            assert len(siblings) > 0

    def test_get_chunk_with_parents_empty(self, sample_text: str) -> None:
        """Test get_chunk_with_parents with non-existent chunk."""
        all_chunks = create_hierarchical_chunks(sample_text, levels=2)
        hierarchy = get_chunk_with_parents("nonexistent-id", all_chunks)

        assert len(hierarchy) == 0


class TestChunkSizes:
    """Tests for chunk size configurations."""

    def test_small_child_chunks(self, long_text: str) -> None:
        """Test creating very small child chunks."""
        chunks = create_hierarchical_chunks(
            long_text,
            parent_chunk_size=500,
            child_chunk_size=50,
            levels=2,
        )

        children = [c for c in chunks if c.level == 1]
        # Should have created child chunks
        assert len(children) > 0
        # Most chunks should be around the target size (allowing for overlap and edge cases)
        avg_size = sum(len(c.text) for c in children) / len(children)
        assert avg_size < 200  # Average should be reasonably small

    def test_large_parent_chunks(self, long_text: str) -> None:
        """Test creating large parent chunks."""
        chunks = create_hierarchical_chunks(
            long_text,
            parent_chunk_size=1000,
            child_chunk_size=200,
            levels=2,
        )

        parents = [c for c in chunks if c.level == 0]
        # Should have fewer large parents
        assert len(parents) >= 1
