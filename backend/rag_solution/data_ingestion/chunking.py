import logging
import re
from typing import List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Callable
from backend.core.config import settings
from backend.vectordbs.utils.watsonx import get_embeddings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def improved_sentence_tokenize(text: str) -> List[str]:
    pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]

def simple_chunking(text: str, min_chunk_size: int, max_chunk_size: int, overlap: int) -> List[str]:
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

def semantic_chunking(text: str, min_chunk_size: int = 1, max_chunk_size: int = 100, threshold: float = 0.5) -> List[str]:
    if max_chunk_size < min_chunk_size:
        raise ValueError("max_chunk_size must be greater than or equal to min_chunk_size")

    sentences = improved_sentence_tokenize(text)
    if len(sentences) == 0:
        logger.warning("No sentences found in the text.")
        return [text] if text else []

    embeddings_list = get_embeddings(sentences)
    embeddings_array = np.array(embeddings_list)

    chunks = []
    current_chunk = [sentences[0]]
    current_embedding = embeddings_array[0].reshape(1, -1)

    for i, (sentence, embedding) in enumerate(zip(sentences[1:], embeddings_array[1:]), 1):
        embedding = embedding.reshape(1, -1)
        similarity = cosine_similarity(current_embedding, embedding)[0][0]
        logger.info(f"Similarity: {similarity:.4f}, Current chunk length: {len(' '.join(current_chunk))}")

        if similarity >= threshold and len(' '.join(current_chunk) + ' ' + sentence) <= max_chunk_size:
            current_chunk.append(sentence)
            current_embedding = np.mean(np.vstack([current_embedding, embedding]), axis=0).reshape(1, -1)
        else:
            if len(' '.join(current_chunk)) >= min_chunk_size:
                chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_embedding = embedding

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    logger.info(f"Number of chunks created: {len(chunks)}")
    return chunks if chunks else [text]  # Return the original text as a single chunk if no chunks were created

def semantic_chunking_for_tables(tables: List[List[List[str]]], min_chunk_size: int = 1, max_chunk_size: int = 100,
                                 threshold: float = 0.8) -> List[str]:
    all_chunks = []

    for table in tables:
        table_text = " ".join([" | ".join(row) for row in table])
        logger.info(f"---- table text: {table_text}")
        # If the table text is shorter than max_chunk_size, add it as a single chunk
        if len(table_text) <= max_chunk_size:
            all_chunks.append(table_text)
        else:
            # Split the table text into smaller parts if it's too long
            table_parts = [table_text[i:i+max_chunk_size] for i in range(0, len(table_text), max_chunk_size)]
            for part in table_parts:
                part_chunks = semantic_chunking(part, min_chunk_size, max_chunk_size, threshold)
                all_chunks.extend(part_chunks)

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
        settings.semantic_threshold,
    )

def get_chunking_method() -> Callable[[str], list[str]]:
    if settings.chunking_strategy.lower() == "semantic":
        return semantic_chunker
    else:
        return simple_chunker
