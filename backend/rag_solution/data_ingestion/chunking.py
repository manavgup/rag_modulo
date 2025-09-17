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
from vectordbs.utils.watsonx import get_embeddings, get_tokenization

if TYPE_CHECKING:
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import-untyped]
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

    embeddings = get_embeddings(combined_sentences)
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


def token_based_chunking(text: str, max_tokens: int = 100, overlap: int = 20) -> list[str]:
    """Split text into chunks based on token count.

    Args:
        text: Input text to chunk
        max_tokens: Maximum tokens per chunk
        overlap: Number of tokens to overlap between chunks

    Returns:
        List of token-based chunks
    """
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


def get_chunking_method(settings: Settings = get_settings()) -> Callable[[str], list[str]]:
    """Get the appropriate chunking method based on settings.

    Args:
        settings: Configuration settings

    Returns:
        Chunking function
    """
    if settings.chunking_strategy.lower() == "semantic":
        return semantic_chunker
    return simple_chunker
