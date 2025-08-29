import functools
import logging
import operator
import re
from collections.abc import Callable

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from core.config import settings
from vectordbs.utils.watsonx import get_embeddings, get_tokenization

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def split_sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.?!])\s+", text)


def combine_sentences(sentences: list[str]) -> list[str]:
    combined_sentences = []
    for i in range(len(sentences)):
        combined_sentence = sentences[i]
        if i > 0:
            combined_sentence = sentences[i - 1] + " " + combined_sentence
        if i < len(sentences) - 1:
            combined_sentence += " " + sentences[i + 1]
        combined_sentences.append(combined_sentence)
    return combined_sentences


def simple_chunking(text: str, min_chunk_size: int, max_chunk_size: int, overlap: int) -> list[str]:
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
    sentences = split_sentences(text)
    tokenized_sentences = get_tokenization(sentences)

    chunks = []
    current_chunk = []
    current_token_count = 0

    for sentence, tokens in zip(sentences, tokenized_sentences, strict=False):
        if current_token_count + len(tokens) > max_tokens and current_chunk:
            chunks.append(" ".join(current_chunk))
            # Keep the last 'overlap' tokens for the next chunk
            overlap_tokens = functools.reduce(operator.iadd, [get_tokenization([sent])[0] for sent in current_chunk[-2:]], [])[-overlap:]
            current_chunk = [sentences[sentences.index(current_chunk[-1])]]
            current_token_count = len(overlap_tokens)

        current_chunk.append(sentence)
        current_token_count += len(tokens)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def calculate_cosine_distances(embeddings: np.ndarray) -> list[float]:
    distances = []
    for i in range(len(embeddings) - 1):
        similarity = cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
        distance = 1 - similarity
        distances.append(distance)
    return distances


def simple_chunker(text: str) -> list[str]:
    return simple_chunking(
        text,
        settings.min_chunk_size,
        settings.max_chunk_size,
        settings.chunk_overlap,
    )


def semantic_chunker(text: str) -> list[str]:
    return semantic_chunking(
        text,
        settings.min_chunk_size,
        settings.max_chunk_size,
    )


def get_chunking_method() -> Callable[[str], list[str]]:
    if settings.chunking_strategy.lower() == "semantic":
        return semantic_chunker
    else:
        return simple_chunker
