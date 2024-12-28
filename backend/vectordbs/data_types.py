"""Core data types for the RAG system."""

from __future__ import annotations

from typing import List, Optional, Any, Dict
from enum import Enum, auto
from pydantic import BaseModel, ConfigDict
from datetime import datetime

# Simplified embedding type
Embedding = float
Embeddings = List[float]
EmbeddingsList = List[Embeddings] # List of embeddings

class Source(str, Enum):
    """Source types for documents."""
    WEBSITE = "website"
    PDF = "pdf"
    WORD_DOCUMENT = "word"
    POWERPOINT = "ppt"
    OTHER = "other"

class DocumentMetadata(BaseModel):
    """Comprehensive metadata for documents and files.
    
    Contains all metadata fields needed for both document processing
    and file management.
    
    Attributes:
        document_name: Name of the document/file
        title: Document title
        author: Document author
        subject: Document subject
        keywords: Keywords/topics
        creator: Document creator
        producer: Document producer
        creation_date: Document creation date
        mod_date: Last modification date
        total_pages: Number of pages (for paginated documents)
        total_chunks: Number of chunks from processing
        content_type: MIME type of the document
    """
    document_name: Optional[str] = None 
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[Dict[str, Any]] = None  # Allow structured keyword data
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[datetime] = None
    mod_date: Optional[datetime] = None
    total_pages: Optional[int] = None
    total_chunks: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    def to_json_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for JSON storage."""
        return {
            k: v.isoformat() if isinstance(v, datetime) else v
            for k, v in self.model_dump(exclude_none=True).items()
        }

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> DocumentMetadata:
        """Create instance from JSON dictionary."""
        # Convert string dates back to datetime if present
        if data.get('creation_date'):
            data['creation_date'] = datetime.fromisoformat(data['creation_date'])
        if data.get('mod_date'):
            data['mod_date'] = datetime.fromisoformat(data['mod_date'])
        return cls(**data)

# Type alias for use in file-related contexts
FileMetadata = DocumentMetadata

class DocumentChunkMetadata(BaseModel):
    """Chunk-level metadata containing position and content information.
    
    Contains information about the chunk's location within the document
    and its relationship to the source document. Used for maintaining
    document structure and enabling accurate reconstruction of content.

    Attributes:
        source: Type of document source
        document_id: Reference to parent document
        page_number: Page number in original document
        chunk_number: Sequential number of this chunk
        start_index: Starting position in original text
        end_index: Ending position in original text
        table_index: Index if chunk is from a table
        image_index: Index if chunk is from an image
    """
    source: Source 
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    chunk_number: Optional[int] = None
    start_index: Optional[int] = None  # Added
    end_index: Optional[int] = None    # Added
    table_index: Optional[int] = None
    image_index: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentChunk(BaseModel):
    """A chunk of text from a document with associated metadata and embeddings.
    
    Attributes:
        chunk_id: Unique identifier for the chunk
        text: The actual text content
        embedding: Optional vector embedding of the text
        metadata: Associated chunk-level metadata
        document_id: Reference to parent document
    """
    chunk_id: str
    text: str
    embeddings: Optional[Embeddings] = None
    metadata: Optional[DocumentChunkMetadata] = None
    document_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    def dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "embeddings": self.embeddings,
            "metadata": self.metadata.model_dump() if self.metadata else None,
            "document_id": self.document_id
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentChunk:
        """Create instance from dictionary data."""
        return cls(
            chunk_id=data["chunk_id"],
            text=data["text"],
            embeddings=data.get("embeddings"),
            metadata=DocumentChunkMetadata.model_validate(data["metadata"]) if data.get("metadata") else None,
            document_id=data.get("document_id")
        )

class Document(BaseModel):
    """A document with its chunks and metadata.
    
    Attributes:
        name: Document name
        document_id: Unique identifier
        chunks: List of document chunks
        path: Optional file path
        metadata: Document-level metadata
    """
    name: str
    document_id: str
    chunks: List[DocumentChunk]
    path: Optional[str] = ""
    metadata: Optional[DocumentMetadata] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        """Create instance from dictionary data."""
        return cls(
            name=data["name"],
            document_id=data["document_id"],
            chunks=[DocumentChunk.from_dict(chunk) for chunk in data["chunks"]],
            path=data.get("path", ""),
            metadata=DocumentMetadata.model_validate(data["metadata"]) if data.get("metadata") else None
        )

class DocumentMetadataFilter(BaseModel):
    """Filter criteria for document metadata.
    
    Attributes:
        field_name: Name of the metadata field to filter on
        operator: Comparison operator
        value: Value to compare against
    """
    field_name: str
    operator: str = ""
    value: Any = None

    model_config = ConfigDict(from_attributes=True)

class VectorQuery(BaseModel):
    """Query for vector database searches.
    
    Provides a unified interface for querying vector databases with either 
    text or pre-computed embeddings, along with filtering and results control.
    
    Attributes:
        text: Query text to search for
        embedding: Optional pre-computed embedding for the query
        metadata_filter: Optional metadata-based filtering
        number_of_results: Maximum number of results to return (defaults to 10)
    """
    text: str
    embeddings: Optional[Embeddings] = None  # Pre-computed if available
    metadata_filter: Optional[DocumentMetadataFilter] = None
    number_of_results: int = 10  # Default to 10 results

    model_config = ConfigDict(from_attributes=True)

class QueryResult(BaseModel):
    """Results from a vector store query.
    
    Attributes:
        chunk: Retrieved document chunks
        score: Similarity scores for each chunk
        embeddings: Vector embeddings for each chunk
    """
    chunk: DocumentChunk
    score: float
    embeddings: Embeddings

    model_config = ConfigDict(from_attributes=True)

    def __repr__(self) -> str:
        """Readable string representation."""
        return f"QueryResult(chunk_id={self.chunk.chunk_id}, score={self.score:.3f}, text={self.chunk.text[:50]}...)"

    @property
    def chunk_id(self) -> str:
        """Convenience accessor for chunk's ID."""
        return self.chunk.chunk_id

    @property
    def document_id(self) -> Optional[str]:
        """Convenience accessor for document's ID."""
        return self.chunk.document_id

    def __len__(self) -> int:
        """Return number of results."""
        return len(self.chunk)

class QueryWithEmbedding(BaseModel):
    """A query with its vector embedding.
    
    Attributes:
        text: Query text
        embedding: Vector embedding of the text
    """
    text: str
    embeddings: Embeddings

    model_config = ConfigDict(from_attributes=True)

