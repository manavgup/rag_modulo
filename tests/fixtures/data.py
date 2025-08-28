"""Test data fixtures for pytest."""

from typing import List
import pytest
from core.config import settings

@pytest.fixture
def test_documents() -> List[str]:
    """Create test document texts."""
    return [
        "Python is a high-level programming language created by Guido van Rossum in 1991. "
        "It is widely used in software development, data science, and artificial intelligence. "
        "Python is known for its simplicity, readability, and extensive standard library.",
        
        "Python supports multiple programming paradigms, including procedural, "
        "object-oriented, and functional programming. Its design philosophy emphasizes "
        "code readability with the use of significant indentation and clean syntax.",
        
        "The Python Package Index (PyPI) contains over 300,000 packages for various "
        "programming tasks. Popular frameworks like Django and Flask are used for "
        "web development, while libraries like NumPy and Pandas are essential for "
        "data analysis."
    ]

@pytest.fixture
def test_questions() -> List[str]:
    """Create test questions."""
    return [
        "What is Python?",
        "Who created Python and when?",
        "What programming paradigms does Python support?",
        "Why is Python known for its readability?"
    ]

@pytest.fixture
def test_prompt_template_data(base_user) -> dict:
    """Create test prompt template data."""
    return {
        "name": "test-question-template",
        "provider": "watsonx",
        "template_type": "QUESTION_GENERATION",
        "system_prompt": (
            "You are an AI assistant that generates relevant questions based on "
            "the given context. Generate clear, focused questions that can be "
            "answered using the information provided."
        ),
        "template_format": (
            "{context}\n\n"
            "Generate {num_questions} specific questions that can be answered "
            "using only the information provided above."
        ),
        "input_variables": {
            "context": "Retrieved passages from knowledge base",
            "num_questions": "Number of questions to generate"
        },
        "example_inputs": {
            "context": "Python supports multiple programming paradigms.",
            "num_questions": 3
        },
        "is_default": True
    }

@pytest.fixture
def sample_content() -> str:
    """Provide comprehensive sample content that requires chunking."""
    return """
    Introduction to Python Programming
    ================================
    Python has emerged as one of the most influential programming languages in the software development landscape. 
    Created by Guido van Rossum in 1991, Python has grown from a scripting language to a comprehensive platform 
    for everything from web development to artificial intelligence. Its philosophy emphasizes code readability with 
    the use of significant whitespace, making it an excellent choice for beginners while remaining powerful enough 
    for advanced applications.

    Core Language Features
    =====================
    Python's syntax is notably clean and readable, relying on indentation to define code blocks. The language 
    supports multiple programming paradigms, including:

    Object-Oriented Programming
    --------------------------
    Python implements object-oriented programming (OOP) principles through a class-based system. Classes serve as 
    blueprints for objects, encapsulating data and behavior. Inheritance is supported, allowing for code reuse 
    and hierarchical relationships between classes.

    Example:
    class Animal:
        def __init__(self, name):
            self.name = name
        
        def speak(self):
            pass

    class Dog(Animal):
        def speak(self):
            return f"{self.name} says woof!"

    Functional Programming
    ---------------------
    While Python isn't a purely functional language, it supports many functional programming concepts. Functions 
    are first-class objects, meaning they can be passed as arguments, returned from other functions, and assigned 
    to variables.

    Standard Library and Package Management
    ====================================
    Python's "batteries included" philosophy is evident in its extensive standard library. The standard library 
    provides modules for:
    - File I/O operations
    - System operations
    - Network programming
    - Date and time handling
    - Database interfaces
    - Concurrent programming

    The Python Package Index (PyPI) hosts over 300,000 third-party packages, making it easy to extend Python's 
    capabilities for specific use cases."""

@pytest.fixture
def indexed_large_document(vector_store, base_collection, base_file, get_watsonx, sample_content: str): 
    """Add chunked documents to vector store."""
    from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source
    from rag_solution.data_ingestion.chunking import simple_chunking

    # Get chunks using configuration
    chunks = simple_chunking(
        text=sample_content,
        min_chunk_size=settings.min_chunk_size,
        max_chunk_size=settings.max_chunk_size,
        overlap=settings.chunk_overlap
    )
    
    # Get embeddings for all chunks
    embeddings = get_watsonx.get_embeddings(chunks)
    
    # Calculate chunk positions
    positions = []
    current_pos = 0
    
    for chunk in chunks:
        if current_pos > 0:
            chunk_start = sample_content.find(chunk.strip(), positions[-1][0])
            if chunk_start == -1:
                chunk_start = sample_content.find(chunk.strip())
        else:
            chunk_start = sample_content.find(chunk.strip())
            
        chunk_end = chunk_start + len(chunk)
        positions.append((chunk_start, chunk_end))
        current_pos = chunk_end
    
    # Create document chunks
    document_chunks = [
        DocumentChunk(
            chunk_id=f"chunk_{i}",
            text=chunk,
            embeddings=embedding,
            metadata=DocumentChunkMetadata(
                source=Source.OTHER,
                document_id=base_file.document_id,
                page_number=1,
                chunk_number=i,
                start_index=pos[0],
                end_index=pos[1]
            )
        )
        for i, (chunk, embedding, pos) in enumerate(zip(chunks, embeddings, positions))
    ]
    
    # Create document
    document = Document(
        document_id=base_file.document_id,
        name="python_comprehensive_guide.txt",
        chunks=document_chunks
    )

    # Set up vector store
    vector_store.delete_collection(base_collection.vector_db_name)
    vector_store.create_collection(
        base_collection.vector_db_name, 
        {"embedding_model": settings.embedding_model}
    )
    vector_store.add_documents(base_collection.vector_db_name, [document])

    yield base_collection.vector_db_name

    # Cleanup
    vector_store.delete_collection(base_collection.vector_db_name)