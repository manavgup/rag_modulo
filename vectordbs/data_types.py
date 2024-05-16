from __future__ import annotations 
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional, Union, Sequence, runtime_checkable
from enum import Enum
from genai.schema import TextEmbeddingParameters
from genai.client import Client

#Document = str
#Documents = List[Document]
#Vector = Union[Sequence[float], Sequence[int]]
# Embeddings
Embedding = Union[Sequence[float], Sequence[int]]
Embeddings = List[Embedding]

@dataclass
class Document:
    document_id: str
    name: str
    chunks: List[DocumentChunk]

@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    vectors: Optional[List[float]] = None
    metadata: Optional[DocumentChunkMetadata] = None

@dataclass
class DocumentChunkMetadata:
    source: Source
    source_id: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    author: Optional[str] = None
    
@dataclass
class DocumentQuery:
    text: str
    metadata: Optional[DocumentMetadataFilter] = None
    
@dataclass   
class Source(str, Enum):
    WEBSITE = "website"
    PDF = "pdf"
    WORD_DOCUMENT = "word_document"
    POWERPOINT = "pptx"
    OTHER = "other"
    

@dataclass
class DocumentMetadataFilter:
    source: Source
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gte: Optional[int] = None
    lte: Optional[int] = None

@dataclass
class DocumentChunkWithScore(DocumentChunk):
    score: Optional[float] = None  

@dataclass
class QueryResult:
    data: Optional[List[DocumentChunkWithScore]] = None
    similarities: Optional[List[float]] = None
    ids: Optional[List[str]] = None

@dataclass
class VectorStoreQuery:
    """Vector store query."""

    # dense embedding
    query_embedding: Optional[List[float]] = None
    similarity_top_k: int = 1
    ids: Optional[List[str]] = None
    query_str: Optional[str] = None
       
@dataclass
class QueryWithEmbedding:
    text: str
    vectors: List[float]

@dataclass
class VectorStoreData:
    id: str
    data: dict
    embedding: List[float]

@dataclass
class VectorStoreQueryMode(str, Enum):
    """Vector store query mode."""
    DEFAULT = "default"
    SPARSE = "sparse"
    HYBRID = "hybrid"
    
    @classmethod
    def get_current_mode(cls):
        """Gets the current query mode."""
        return cls.DEFAULT  # Default to dense vector search
    
class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add_documents(self, collection_name: str, documents: List[Document]):
        """Adds documents to the vector store."""

    @abstractmethod
    def retrieve_documents(self, query: Union[str, QueryWithEmbedding], 
                          collection_name: Optional[str] = None, top_k: int = 4) -> QueryResult:
        """Retrieves documents based on a query or query embedding.
        
        Args:
            query: Either a text string or a QueryWithEmbedding object.
            collection_name: Optional name of the collection.
            top_k: Number of top results to return. (Default: 4)
        
        Returns:
            A QueryResult object containing the retrieved documents and their scores.
        """

    @abstractmethod
    def query(self, query: QueryWithEmbedding,
              collection_name: Optional[str] = None, 
              number_of_results: int = 10, 
              filter: Optional[DocumentMetadataFilter] = None) -> QueryResult:
        """Queries the vector store with filtering and query mode options.

        Args:
            query: Either a text string or a QueryWithEmbedding object.
            collection_name: Optional name of the collection.
            number_of_results: Number of top results to return. (Default: 10)
            filter: Optional metadata filter to apply to the search.
        
        Returns:
            A QueryResult object containing the retrieved documents and their scores.
        """

    @abstractmethod
    def delete_collection(self, collection_name: str):
        """Deletes a collection from the vector store."""

    @abstractmethod
    def delete_documents(self, document_ids: List[str], collection_name: Optional[str] = None):
        """Deletes documents by their IDs from the vector store."""
    
    @abstractmethod
    def get_document(self, document_id: str, collection_name: Optional[str] = None) -> Optional[Document]:
        """Retrieves a document by its ID from the vector store."""
        
    def embed_with_watsonx(self, inputs: list[DocumentChunk], client: Client, 
                           model_id: str, 
                parameters: Optional[TextEmbeddingParameters] = None) -> Embeddings:
        """Embeds text using Watsonx and optionally saves embeddings to a file.

        Args:
            inputs: The documents to embed.
            client: The Watsonx client instance.
            parameters: Optional text embedding parameters.
            output_file_path: If provided, the path to save embeddings.
            file_format: The format for saving embeddings ("json" or "txt").

        Returns:
            The list of embeddings. """
        
        embeddings: Embeddings = []
        for response in client.text.embedding.create(
            model_id=model_id, inputs=inputs, parameters=parameters):
            if (len(response.results) > 0 and len(response.results[0]) > 0):
                embeddings.extend(response.results)
        return embeddings

    # Additional helper methods could be added here (e.g., to update document embeddings, 
    # retrieve document metadata, etc.), depending on the specific needs of your implementations. 
