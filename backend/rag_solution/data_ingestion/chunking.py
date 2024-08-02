import logging
from typing import List

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from core.config import settings
from vectordbs.utils.watsonx import get_embeddings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def simple_chunking(text: str, min_chunk_size: int, max_chunk_size: int, overlap: int) -> List[str]:
    """
    Chunk the text into chunks of a specified size with a specified overlap.

    Args:
        text (str): The text to be chunked.
        chunk_size (int): The size of each chunk.
        overlap (int): The number of overlapping characters between chunks.

    Returns:
        List[str]: A list of text chunks.
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + max_chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        start += max_chunk_size - overlap

    return chunks


def semantic_chunking(
    text: str,
    min_chunk_size: int = 1,
    max_chunk_size: int = 100,
    threshold: float = 0.8,
) -> List[str]:
    """
    Chunk the text into semantically coherent chunks using embedding similarity.

    Args:
        text (str): The text to be chunked.
        min_chunk_size (int): Minimum number of sentences in a chunk.
        max_chunk_size (int): Maximum number of sentences in a chunk.
        threshold (float): The similarity threshold for determining chunk boundaries.

    Returns:
        List[str]: A list of semantically coherent text chunks.
    """
    # Split the text into sentences
    sentences = [s.strip() for s in text.split(".") if s.strip()]

    # Get embeddings for all sentences
    embeddings_list: List[float] = get_embeddings(sentences)

    # Reshape embeddings into a 2D array
    embeddings_array = np.array(embeddings_list).reshape(len(sentences), -1)

    chunks: List[str] = []
    current_chunk: List[str] = []
    current_embedding: np.ndarray = embeddings_array[0]

    for i, (sentence, embedding) in enumerate(zip(sentences, embeddings_array)):
        current_chunk = [sentence]
        current_embedding = embedding

        similarity = cosine_similarity([current_embedding], [embedding])[0][0]
        logger.info(
            f"Similarity: {similarity}",
            f"** Current chunk length: {len(current_chunk)}",
        )

        if similarity >= threshold and len(current_chunk) < max_chunk_size:
            # Add to current chunk
            current_chunk.append(sentence)
            # Update current embedding as the average
            current_embedding = np.mean(
                np.vstack([current_embedding, embedding]), axis=0
            )
        else:
            # Add the current chunk to chunks and start a new one
            chunks.append(". ".join(current_chunk) + ".")
            current_chunk = [sentence]
            current_embedding = embedding

    # Add the last chunk if it meets the minimum size
    if current_chunk:
        chunks.append(". ".join(current_chunk) + ".")

    logger.info(f"Number of chunks created: {len(chunks)}")
    return chunks


def semantic_chunking_for_tables(tables: List[List[List[str]]], min_chunk_size: int = 1, max_chunk_size: int = 100,
                                 threshold: float = 0.8) -> List[str]:
    """
    Chunk the extracted table content into semantically coherent chunks using embedding similarity.

    Args:
        tables (List[List[List[str]]]): List of tables, where each table is a list of rows, and each row is a list of cells.
        min_chunk_size (int): Minimum number of rows in a chunk.
        max_chunk_size (int): Maximum number of rows in a chunk.
        threshold (float): The similarity threshold for determining chunk boundaries.

    Returns:
        List[str]: A list of semantically coherent text chunks.
    """
    all_chunks = []

    for table in tables:
        # Convert each row to a string
        table_rows = [" | ".join(row) for row in table]

        # Use semantic_chunking on each row
        for row in table_rows:
            row_chunks = semantic_chunking(
                row, min_chunk_size, max_chunk_size, threshold
            )
            all_chunks.extend(row_chunks)

    # Merge small chunks if necessary
    final_chunks = []
    current_chunk = ""
    for chunk in all_chunks:
        if len(current_chunk) + len(chunk) <= max_chunk_size:
            current_chunk += (" " if current_chunk else "") + chunk
        else:
            if current_chunk:
                final_chunks.append(current_chunk)
            current_chunk = chunk
    if current_chunk:
        final_chunks.append(current_chunk)

    return final_chunks


def get_chunking_method():
    if settings.chunking_strategy.lower() == "semantic":
        return lambda text: semantic_chunking(
            text,
            settings.min_chunk_size,
            settings.max_chunk_size,
            settings.semantic_threshold,
        )
    else:
        return lambda text: simple_chunking(
            text,
            settings.min_chunk_size,
            settings.max_chunk_size,
            settings.chunk_overlap,
        )
