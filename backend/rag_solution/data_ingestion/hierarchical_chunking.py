"""Hierarchical chunking for improved RAG retrieval quality.

This module implements hierarchical chunking where:
1. Small child chunks are used for precise retrieval
2. Larger parent chunks provide context to the LLM
3. Parent-child relationships preserve document structure
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.config import Settings, get_settings
from core.identity_service import IdentityService

logger = logging.getLogger(__name__)


@dataclass
class HierarchicalChunk:
    """Represents a chunk in a hierarchical structure.

    Attributes:
        chunk_id: Unique identifier for this chunk.
        text: The chunk text content.
        parent_id: ID of the parent chunk (None for top-level).
        child_ids: List of child chunk IDs.
        level: Depth level (0=root, 1=parent, 2=child, etc.).
        start_index: Start position in original document.
        end_index: End position in original document.
    """

    chunk_id: str
    text: str
    parent_id: str | None = None
    child_ids: list[str] | None = None
    level: int = 0
    start_index: int = 0
    end_index: int = 0

    def __post_init__(self) -> None:
        """Initialize child_ids list if None."""
        if self.child_ids is None:
            self.child_ids = []


# pylint: disable=too-many-locals
# Justification: Complex hierarchical chunking requires many intermediate variables
def create_hierarchical_chunks(
    text: str,
    parent_chunk_size: int = 1500,
    child_chunk_size: int = 300,
    overlap: int = 50,
    levels: int = 2,
) -> list[HierarchicalChunk]:
    """Create hierarchical chunks with parent-child relationships.

    Strategy:
    - Level 0 (root): Entire document or very large sections
    - Level 1 (parents): Large chunks for context (~1500 chars)
    - Level 2 (children): Small chunks for retrieval (~300 chars)

    Args:
        text: Input text to chunk.
        parent_chunk_size: Size of parent chunks.
        child_chunk_size: Size of child chunks.
        overlap: Overlap between chunks at each level.
        levels: Number of hierarchy levels (2 or 3).

    Returns:
        List of HierarchicalChunk objects with parent-child relationships.
    """
    # Import here to avoid circular import
    from rag_solution.data_ingestion.chunking import simple_chunking

    if not text:
        return []

    all_chunks: list[HierarchicalChunk] = []

    # Level 0: Create root chunk (entire document or very large section)
    if levels >= 3:
        root_chunk = HierarchicalChunk(
            chunk_id=f"root-{IdentityService.generate_id().hex[:8]}",
            text=text,
            parent_id=None,
            level=0,
            start_index=0,
            end_index=len(text),
        )
        all_chunks.append(root_chunk)
        parent_parent_id = root_chunk.chunk_id
    else:
        parent_parent_id = None

    # Level 1: Create parent chunks
    # Ensure overlap is less than chunk size to avoid infinite loops
    safe_overlap = min(overlap, parent_chunk_size - 1)
    parent_texts = simple_chunking(text, parent_chunk_size // 2, parent_chunk_size, safe_overlap)

    parent_chunks: list[HierarchicalChunk] = []
    current_pos = 0

    for parent_text in parent_texts:
        parent_id = f"parent-{IdentityService.generate_id().hex[:8]}"
        start_index = text.find(parent_text, current_pos)
        if start_index == -1:
            start_index = current_pos
        end_index = start_index + len(parent_text)

        parent_chunk = HierarchicalChunk(
            chunk_id=parent_id,
            text=parent_text,
            parent_id=parent_parent_id,
            level=1 if levels >= 3 else 0,
            start_index=start_index,
            end_index=end_index,
        )
        parent_chunks.append(parent_chunk)
        all_chunks.append(parent_chunk)

        # Update root's children if exists
        if parent_parent_id and levels >= 3:
            all_chunks[0].child_ids.append(parent_id)  # type: ignore

        current_pos = end_index - overlap

    # Level 2: Create child chunks for each parent
    for parent_chunk in parent_chunks:
        # Ensure overlap is less than chunk size to avoid infinite loops
        safe_child_overlap = min(overlap, child_chunk_size - 1)
        child_texts = simple_chunking(
            parent_chunk.text,
            child_chunk_size // 2,
            child_chunk_size,
            safe_child_overlap,
        )

        parent_start = parent_chunk.start_index
        child_current_pos = 0

        for child_text in child_texts:
            child_id = f"child-{IdentityService.generate_id().hex[:8]}"
            child_start_in_parent = parent_chunk.text.find(child_text, child_current_pos)
            if child_start_in_parent == -1:
                child_start_in_parent = child_current_pos

            child_chunk = HierarchicalChunk(
                chunk_id=child_id,
                text=child_text,
                parent_id=parent_chunk.chunk_id,
                level=2 if levels >= 3 else 1,
                start_index=parent_start + child_start_in_parent,
                end_index=parent_start + child_start_in_parent + len(child_text),
            )
            all_chunks.append(child_chunk)
            parent_chunk.child_ids.append(child_id)  # type: ignore

            child_current_pos = child_start_in_parent + len(child_text) - overlap

    logger.info(
        "Created %d hierarchical chunks: %d root, %d parents, %d children",
        len(all_chunks),
        len([c for c in all_chunks if c.level == 0]),
        len([c for c in all_chunks if c.level == 1]),
        len([c for c in all_chunks if c.level == 2]),
    )

    return all_chunks


# pylint: disable=too-many-locals
# Justification: Complex sentence-based chunking requires many intermediate variables
def create_sentence_based_hierarchical_chunks(
    text: str,
    sentences_per_child: int = 3,
    children_per_parent: int = 5,
) -> list[HierarchicalChunk]:
    """Create hierarchical chunks based on sentence grouping.

    This strategy preserves sentence boundaries and is useful for
    documents where sentence structure is important.

    Args:
        text: Input text to chunk.
        sentences_per_child: Number of sentences per child chunk.
        children_per_parent: Number of child chunks per parent.

    Returns:
        List of HierarchicalChunk objects.
    """
    # Import here to avoid circular import
    from rag_solution.data_ingestion.chunking import split_sentences

    if not text:
        return []

    sentences = split_sentences(text)
    if not sentences:
        return []

    all_chunks: list[HierarchicalChunk] = []

    # Calculate sizes
    sentences_per_parent = sentences_per_child * children_per_parent

    # Create parent and child chunks
    current_pos = 0
    sentence_idx = 0

    while sentence_idx < len(sentences):
        # Create parent chunk
        parent_sentences = sentences[sentence_idx : sentence_idx + sentences_per_parent]
        parent_text = " ".join(parent_sentences)
        parent_id = f"parent-{IdentityService.generate_id().hex[:8]}"

        parent_start = text.find(parent_sentences[0], current_pos)
        if parent_start == -1:
            parent_start = current_pos
        parent_end = parent_start + len(parent_text)

        parent_chunk = HierarchicalChunk(
            chunk_id=parent_id,
            text=parent_text,
            parent_id=None,
            level=0,
            start_index=parent_start,
            end_index=parent_end,
        )
        all_chunks.append(parent_chunk)

        # Create child chunks for this parent
        child_start_idx = sentence_idx
        while child_start_idx < min(sentence_idx + sentences_per_parent, len(sentences)):
            child_sentences = sentences[child_start_idx : child_start_idx + sentences_per_child]
            if not child_sentences:
                break

            child_text = " ".join(child_sentences)
            child_id = f"child-{IdentityService.generate_id().hex[:8]}"

            child_start = parent_text.find(child_sentences[0])
            if child_start == -1:
                child_start = 0
            child_start += parent_start

            child_chunk = HierarchicalChunk(
                chunk_id=child_id,
                text=child_text,
                parent_id=parent_id,
                level=1,
                start_index=child_start,
                end_index=child_start + len(child_text),
            )
            all_chunks.append(child_chunk)
            parent_chunk.child_ids.append(child_id)  # type: ignore

            child_start_idx += sentences_per_child

        current_pos = parent_end
        sentence_idx += sentences_per_parent

    logger.info(
        "Created %d sentence-based chunks: %d parents, %d children",
        len(all_chunks),
        len([c for c in all_chunks if c.level == 0]),
        len([c for c in all_chunks if c.level == 1]),
    )

    return all_chunks


def hierarchical_chunker(
    text: str,
    settings: Settings = get_settings(),
    strategy: str = "size_based",
) -> list[HierarchicalChunk]:
    """Create hierarchical chunks using configuration from settings.

    Args:
        text: Input text to chunk.
        settings: Configuration settings.
        strategy: Chunking strategy ("size_based" or "sentence_based").

    Returns:
        List of HierarchicalChunk objects.
    """
    if strategy == "sentence_based":
        return create_sentence_based_hierarchical_chunks(
            text,
            sentences_per_child=getattr(settings, "hierarchical_sentences_per_child", 3),
            children_per_parent=getattr(settings, "hierarchical_children_per_parent", 5),
        )

    return create_hierarchical_chunks(
        text,
        parent_chunk_size=getattr(settings, "hierarchical_parent_size", 1500),
        child_chunk_size=getattr(settings, "hierarchical_child_size", 300),
        overlap=settings.chunk_overlap,
        levels=getattr(settings, "hierarchical_levels", 2),
    )


def get_child_chunks(chunks: list[HierarchicalChunk]) -> list[HierarchicalChunk]:
    """Extract only the leaf (child) chunks for indexing.

    Args:
        chunks: List of all hierarchical chunks.

    Returns:
        List of only child chunks (highest level).
    """
    if not chunks:
        return []

    max_level = max(c.level for c in chunks)
    return [c for c in chunks if c.level == max_level]


def get_parent_for_chunk(chunk_id: str, all_chunks: list[HierarchicalChunk]) -> HierarchicalChunk | None:
    """Get the parent chunk for a given chunk ID.

    Args:
        chunk_id: ID of the chunk to find parent for.
        all_chunks: List of all hierarchical chunks.

    Returns:
        Parent HierarchicalChunk or None if not found.
    """
    target_chunk = next((c for c in all_chunks if c.chunk_id == chunk_id), None)
    if not target_chunk or not target_chunk.parent_id:
        return None

    return next((c for c in all_chunks if c.chunk_id == target_chunk.parent_id), None)


def get_chunk_with_parents(
    chunk_id: str,
    all_chunks: list[HierarchicalChunk],
    include_siblings: bool = False,
) -> list[HierarchicalChunk]:
    """Get a chunk along with its parent hierarchy.

    Args:
        chunk_id: ID of the child chunk.
        all_chunks: List of all hierarchical chunks.
        include_siblings: Whether to include sibling chunks.

    Returns:
        List containing the chunk and its ancestors.
    """
    result: list[HierarchicalChunk] = []

    # Find the target chunk
    target = next((c for c in all_chunks if c.chunk_id == chunk_id), None)
    if not target:
        return result

    result.append(target)

    # Add siblings if requested
    if include_siblings and target.parent_id:
        parent = get_parent_for_chunk(chunk_id, all_chunks)
        if parent and parent.child_ids:
            siblings = [c for c in all_chunks if c.chunk_id in parent.child_ids and c.chunk_id != chunk_id]
            result.extend(siblings)

    # Walk up the parent chain
    current = target
    while current.parent_id:
        parent = get_parent_for_chunk(current.chunk_id, all_chunks)
        if parent:
            result.append(parent)
            current = parent
        else:
            break

    return result
