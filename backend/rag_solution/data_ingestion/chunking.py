"""Document chunking utilities.

This module provides various chunking strategies for breaking down documents
into smaller, manageable pieces for vector storage and retrieval.
"""

import functools
import logging
import operator
import re
from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np

from core.config import Settings, get_settings
from rag_solution.data_ingestion.hierarchical_chunking import (
    create_hierarchical_chunks,
    create_sentence_based_hierarchical_chunks,
    get_child_chunks,
)

# Import shared embedding utility
from vectordbs.utils.embeddings import get_embeddings_for_vector_store

# Keep get_tokenization import for deprecated function backward compatibility
from vectordbs.utils.watsonx import get_tokenization

if TYPE_CHECKING:
    from sklearn.metrics.pairwise import cosine_similarity
else:
    try:
        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import-untyped]
    except ImportError:
        cosine_similarity = None

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences based on punctuation.

    Args:
        text: Input text to split

    Returns:
        List of sentences
    """
    return re.split(r"(?<=[.?!])\s+", text)


def combine_sentences(sentences: list[str]) -> list[str]:
    """Combine sentences with their neighbors for context.

    Args:
        sentences: List of sentences to combine

    Returns:
        List of combined sentences
    """
    combined_sentences = []
    for i, sentence in enumerate(sentences):
        combined_sentence = sentence
        if i > 0:
            combined_sentence = sentences[i - 1] + " " + combined_sentence
        if i < len(sentences) - 1:
            combined_sentence += " " + sentences[i + 1]
        combined_sentences.append(combined_sentence)
    return combined_sentences


def simple_chunking(text: str, min_chunk_size: int, max_chunk_size: int, overlap: int) -> list[str]:
    """Split text into chunks with overlap.

    Args:
        text: Input text to chunk
        min_chunk_size: Minimum size for a chunk
        max_chunk_size: Maximum size for a chunk
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if max_chunk_size < min_chunk_size:
        raise ValueError("max_chunk_size must be greater than or equal to min_chunk_size")

    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + max_chunk_size, text_length)
        chunk = text[start:end]

        if len(chunk) >= min_chunk_size:
            chunks.append(chunk)
        elif chunks:  # If it's the last chunk and it's too small, append it to the previous chunk
            chunks[-1] += chunk
        else:  # If it's the only chunk and it's too small, keep it anyway
            chunks.append(chunk)

        start += max_chunk_size - overlap

    return chunks


def semantic_chunking(text: str, min_chunk_size: int = 1, max_chunk_size: int = 100) -> list[str]:
    """Split text into semantically meaningful chunks.

    Args:
        text: Input text to chunk
        min_chunk_size: Minimum size for a chunk
        max_chunk_size: Maximum size for a chunk

    Returns:
        List of semantic chunks
    """
    if not text:
        return []
    sentences = split_sentences(text)
    combined_sentences = combine_sentences(sentences)

    # Use default settings for embedding generation
    settings = get_settings()
    embeddings = get_embeddings_for_vector_store(combined_sentences, settings)
    embeddings_array = np.array(embeddings)

    # Ensure the array has the correct shape for cosine similarity
    if embeddings_array.ndim == 1:
        embeddings_array = embeddings_array.reshape(1, -1)

    # Check for empty or insufficient embeddings
    if embeddings_array.size == 0:
        return []

    distances = calculate_cosine_distances(embeddings_array)
    if len(distances) == 0:
        return []

    breakpoint_percentile_threshold = 80
    breakpoint_distance_threshold = np.percentile(distances, breakpoint_percentile_threshold)

    indices_above_thresh = [i for i, distance in enumerate(distances) if distance > breakpoint_distance_threshold]

    chunks = []
    start_index = 0

    for index in indices_above_thresh:
        chunk = " ".join(sentences[start_index : index + 1])
        if len(chunk) >= min_chunk_size and len(chunk) <= max_chunk_size:
            chunks.append(chunk)
        start_index = index + 1

    if start_index < len(sentences):
        chunk = " ".join(sentences[start_index:])
        if len(chunk) >= min_chunk_size and len(chunk) <= max_chunk_size:
            chunks.append(chunk)

    return chunks


def sentence_based_chunking(
    text: str, target_chars: int = 750, overlap_chars: int = 100, min_chars: int = 500
) -> list[str]:
    """Sentence-based chunking with conservative character limits (FAST, no API calls).

    Strategy for IBM Slate 512-token limit:
    - Conservative char/token ratio: 2.5 chars/token (handles technical docs)
    - Target: 750 chars ≈ 300 tokens (guidance: 200-400 tokens for 512-token models)
    - Overlap: 100 chars ≈ 40 tokens (~13% overlap)
    - Min: 500 chars ≈ 200 tokens
    - Max safe: 1000 chars ≈ 400 tokens (well under 512 limit)
    - Chunks at sentence boundaries (semantic)

    Args:
        text: Input text to chunk
        target_chars: Target characters per chunk (default: 750)
        overlap_chars: Characters to overlap between chunks (default: 100)
        min_chars: Minimum characters for a chunk (default: 500)

    Returns:
        List of sentence-based chunks
    """
    if not text:
        return []

    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_char_count = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # Handle oversized sentences by splitting them
        if sentence_len > target_chars:
            # Save current chunk first if not empty
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append(chunk_text)
                current_chunk = []
                current_char_count = 0

            # Split oversized sentence into target-sized pieces
            start = 0
            while start < sentence_len:
                end = min(start + target_chars, sentence_len)
                # Try to break at word boundary
                if end < sentence_len:
                    last_space = sentence[start:end].rfind(" ")
                    if last_space > target_chars * 0.5:  # At least 50% full
                        end = start + last_space

                chunk_piece = sentence[start:end].strip()
                if chunk_piece:  # Only append non-empty chunks
                    chunks.append(chunk_piece)
                start = end

            continue

        # Account for space between sentences when joining
        space_len = 1 if current_chunk else 0

        # STRICT: Don't add sentence if it would exceed target
        if current_char_count + space_len + sentence_len > target_chars and current_chunk:
            # Save current chunk (don't add the sentence that would exceed)
            chunk_text = " ".join(current_chunk)
            chunks.append(chunk_text)

            # Create overlap: keep last sentences that fit in overlap_chars
            overlap_chunk: list[str] = []
            overlap_count = 0

            for i in range(len(current_chunk) - 1, -1, -1):
                sent_len = len(current_chunk[i])
                space = 1 if overlap_chunk else 0
                if overlap_count + space + sent_len <= overlap_chars:
                    overlap_chunk.insert(0, current_chunk[i])
                    overlap_count += sent_len + space
                else:
                    break

            current_chunk = overlap_chunk
            current_char_count = overlap_count

        current_chunk.append(sentence)
        current_char_count += sentence_len + space_len

    # Add final chunk if it meets minimum size
    if current_chunk:
        chunk_text = " ".join(current_chunk)

        if len(chunk_text) >= min_chars or not chunks:
            chunks.append(chunk_text)
        elif chunks:
            # Merge small final chunk with previous chunk
            chunks[-1] += " " + chunk_text

    avg_chars = sum(len(c) for c in chunks) / len(chunks) if chunks else 0
    logger.info(
        f"Created {len(chunks)} sentence-based chunks: avg {avg_chars:.0f} chars "
        f"(~{avg_chars / 2.5:.0f} tokens estimated)"
    )

    return chunks


def token_based_chunking(text: str, max_tokens: int = 100, overlap: int = 20) -> list[str]:
    """DEPRECATED: Use efficient_token_chunking() instead.

    This function makes WatsonX API calls for every sentence - very slow.
    Kept for backward compatibility only.

    Args:
        text: Input text to chunk
        max_tokens: Maximum tokens per chunk
        overlap: Number of tokens to overlap between chunks

    Returns:
        List of token-based chunks
    """
    logger.warning("token_based_chunking() is deprecated - use efficient_token_chunking() instead")

    sentences = split_sentences(text)
    tokenized_sentences = get_tokenization(sentences)

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_token_count = 0

    for sentence, tokens in zip(sentences, tokenized_sentences, strict=False):
        if current_token_count + len(tokens) > max_tokens and current_chunk:
            chunks.append(" ".join(current_chunk))
            # Keep the last 'overlap' tokens for the next chunk
            overlap_tokens: list[str] = functools.reduce(
                operator.iadd, [get_tokenization([sent])[0] for sent in current_chunk[-2:]], []
            )[-overlap:]
            current_chunk = [sentences[sentences.index(current_chunk[-1])]]
            current_token_count = len(overlap_tokens)

        current_chunk.append(sentence)
        current_token_count += len(tokens)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def calculate_cosine_distances(embeddings: np.ndarray) -> list[float]:
    """Calculate cosine distances between consecutive embeddings.

    Args:
        embeddings: Array of embeddings

    Returns:
        List of cosine distances
    """
    distances = []
    for i in range(len(embeddings) - 1):
        similarity = cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
        distance = 1 - similarity
        distances.append(distance)
    return distances


def simple_chunker(text: str, settings: Settings = get_settings()) -> list[str]:
    """Simple chunking using settings configuration.

    Args:
        text: Input text to chunk
        settings: Configuration settings

    Returns:
        List of chunks
    """
    return simple_chunking(
        text,
        settings.min_chunk_size,
        settings.max_chunk_size,
        settings.chunk_overlap,
    )


def semantic_chunker(text: str, settings: Settings = get_settings()) -> list[str]:
    """Semantic chunking using settings configuration.

    Args:
        text: Input text to chunk
        settings: Configuration settings

    Returns:
        List of semantic chunks
    """
    return semantic_chunking(
        text,
        settings.min_chunk_size,
        settings.max_chunk_size,
    )


def hierarchical_chunker_wrapper(text: str, settings: Settings = get_settings()) -> list[str]:
    """Wrapper for hierarchical chunking that returns only child chunk texts.

    This wrapper extracts only the leaf (child) chunks from hierarchical chunking
    for use in the standard ingestion pipeline. The hierarchy metadata is stored
    separately during ingestion.

    Args:
        text: Input text to chunk
        settings: Configuration settings

    Returns:
        List of child chunk texts
    """
    strategy = getattr(settings, "hierarchical_strategy", "size_based")

    if strategy == "sentence_based":
        all_chunks = create_sentence_based_hierarchical_chunks(
            text,
            sentences_per_child=getattr(settings, "hierarchical_sentences_per_child", 3),
            children_per_parent=getattr(settings, "hierarchical_children_per_parent", 5),
        )
    else:
        all_chunks = create_hierarchical_chunks(
            text,
            parent_chunk_size=getattr(settings, "hierarchical_parent_size", 1500),
            child_chunk_size=getattr(settings, "hierarchical_child_size", 300),
            overlap=settings.chunk_overlap,
            levels=getattr(settings, "hierarchical_levels", 2),
        )

    # Extract only child chunks for indexing
    child_chunks = get_child_chunks(all_chunks)
    return [chunk.text for chunk in child_chunks]


def sentence_chunker(text: str, settings: Settings = get_settings()) -> list[str]:
    """Sentence-based chunking using settings configuration.

    All config values (min_chunk_size, max_chunk_size, chunk_overlap) are in CHARACTERS.
    Conservative char-to-token ratio (2.5:1) provides safety margin for IBM Slate 512-token limit.

    Args:
        text: Input text to chunk
        settings: Configuration settings (all values in characters)

    Returns:
        List of sentence-based chunks
    """
    # Use config values directly as characters (no conversion needed)
    target_chars = settings.max_chunk_size
    overlap_chars = settings.chunk_overlap
    min_chars = settings.min_chunk_size

    return sentence_based_chunking(text, target_chars=target_chars, overlap_chars=overlap_chars, min_chars=min_chars)


def token_chunker(text: str, settings: Settings = get_settings()) -> list[str]:
    """DEPRECATED: Use sentence_chunker() instead - it's faster and safer.

    This function makes WatsonX API calls which is very slow.

    Args:
        text: Input text to chunk
        settings: Configuration settings

    Returns:
        List of token-based chunks
    """
    logger.warning("token_chunker() is deprecated - use sentence_chunker() instead")
    # Use 80% of max tokens to leave safety margin
    max_tokens = int(settings.max_chunk_size * 0.8) if settings.max_chunk_size < 512 else 410
    overlap = int(settings.chunk_overlap * 0.8) if settings.chunk_overlap < 100 else 80
    return token_based_chunking(text, max_tokens=max_tokens, overlap=overlap)


def get_chunking_method(settings: Settings = get_settings()) -> Callable[[str], list[str]]:
    """Get the appropriate chunking method based on settings.

    Args:
        settings: Configuration settings

    Returns:
        Chunking function
    """
    strategy = settings.chunking_strategy.lower()

    if strategy == "sentence":
        return lambda text: sentence_chunker(text, settings)
    if strategy == "semantic":
        return semantic_chunker
    if strategy == "hierarchical":
        return lambda text: hierarchical_chunker_wrapper(text, settings)
    if strategy == "token":
        return lambda text: token_chunker(text, settings)

    return simple_chunker
