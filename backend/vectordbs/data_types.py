"""Core data types for the RAG system."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict

# Simplified embedding type
Embedding = float
Embeddings = list[float]
EmbeddingsList = list[Embeddings]  # List of embeddings


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

    document_name: str | None = None
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: dict[str, Any] | list[str] | None = None  # Allow structured keyword data or list of strings
    creator: str | None = None
    producer: str | None = None
    creation_date: datetime | None = None
    mod_date: datetime | None = None
    total_pages: int | None = None
    total_chunks: int | None = None

    model_config = ConfigDict(from_attributes=True)

    def to_json_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for JSON storage."""
        return {
            k: v.isoformat() if isinstance(v, datetime) else v for k, v in self.model_dump(exclude_none=True).items()
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> DocumentMetadata:
        """Create instance from JSON dictionary."""
        # Convert string dates back to datetime if present
        if data.get("creation_date"):
            data["creation_date"] = datetime.fromisoformat(data["creation_date"])
        if data.get("mod_date"):
            data["mod_date"] = datetime.fromisoformat(data["mod_date"])
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
        parent_chunk_id: Reference to parent chunk (for hierarchical chunking)
        child_chunk_ids: References to child chunks (for hierarchical chunking)
        level: Hierarchy level (0=root, 1=parent, 2=child, etc.)
    """

    source: Source
    document_id: str | None = None
    page_number: int | None = None
    chunk_number: int | None = None
    start_index: int | None = None  # Added
    end_index: int | None = None  # Added
    table_index: int | None = None
    image_index: int | None = None
    source_id: str | None = None
    url: str | None = None
    created_at: str | None = None
    author: str | None = None
    parent_chunk_id: str | None = None  # Hierarchical chunking support
    child_chunk_ids: list[str] | None = None  # Hierarchical chunking support
    level: int | None = None  # Hierarchy level

    model_config = ConfigDict(from_attributes=True)

    def to_vector_db(self) -> dict[str, Any]:
        """Convert metadata to vector database format.

        Returns dict with non-None values, converting Source enum to string.
        """
        data = self.model_dump(exclude_none=True)
        # Convert Source enum to string for vector DB storage
        if "source" in data:
            data["source"] = str(data["source"]) if isinstance(data["source"], Source) else data["source"]
        return data

    @classmethod
    def from_vector_db(cls, data: dict[str, Any]) -> DocumentChunkMetadata:
        """Create instance from vector database format.

        Args:
            data: Dictionary from vector database

        Returns:
            DocumentChunkMetadata instance
        """
        # Convert string source back to Source enum
        if "source" in data and isinstance(data["source"], str):
            try:
                data["source"] = Source(data["source"])
            except ValueError:
                data["source"] = Source.OTHER
        return cls.model_validate(data)


class DocumentChunk(BaseModel):
    """A chunk of text from a document with associated metadata and embeddings.

    Attributes:
        chunk_id: Unique identifier for the chunk
        text: The actual text content
        embedding: Optional vector embedding of the text
        metadata: Associated chunk-level metadata
        document_id: Reference to parent document
        parent_chunk_id: Reference to parent chunk (for hierarchical chunking)
        child_chunk_ids: References to child chunks (for hierarchical chunking)
        level: Hierarchy level (0=root, 1=parent, 2=child, etc.)
    """

    chunk_id: str | None = None
    text: str | None = None
    embeddings: Embeddings | None = None
    vectors: Embeddings | None = None  # Alias for embeddings
    metadata: DocumentChunkMetadata | None = None
    document_id: str | None = None
    parent_chunk_id: str | None = None  # Hierarchical chunking support
    child_chunk_ids: list[str] | None = None  # Hierarchical chunking support
    level: int | None = None  # Hierarchy level

    model_config = ConfigDict(from_attributes=True)

    def to_vector_db(self) -> dict[str, Any]:
        """Convert chunk to vector database format.

        Returns a dict suitable for insertion into vector databases,
        with metadata flattened and non-None values.
        """
        data: dict[str, Any] = {
            "id": self.chunk_id,
            "text": self.text or "",
            "embeddings": self.embeddings,
            "document_id": self.document_id or "",
        }

        # Add metadata fields as top-level entries
        if self.metadata:
            metadata_dict = self.metadata.to_vector_db()
            data["metadata"] = metadata_dict
            # Also add commonly used fields at top level for easy filtering
            data["source"] = metadata_dict.get("source", "OTHER")
            data["page_number"] = metadata_dict.get("page_number", 0)
            data["chunk_number"] = metadata_dict.get("chunk_number", 0)

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentChunk:
        """Create instance from dictionary data."""
        return cls(
            chunk_id=data["chunk_id"],
            text=data["text"],
            embeddings=data.get("embeddings"),
            metadata=DocumentChunkMetadata.model_validate(data["metadata"]) if data.get("metadata") else None,
            document_id=data.get("document_id"),
            parent_chunk_id=data.get("parent_chunk_id"),
            child_chunk_ids=data.get("child_chunk_ids"),
            level=data.get("level"),
        )

    @classmethod
    def from_vector_db(cls, data: dict[str, Any]) -> DocumentChunk:
        """Create instance from vector database format.

        Args:
            data: Dictionary from vector database with potentially flattened metadata

        Returns:
            DocumentChunk instance
        """
        # Extract metadata from either nested 'metadata' dict or top-level fields
        metadata_dict = data.get("metadata", {})
        if not metadata_dict:
            # Build metadata from top-level fields
            metadata_dict = {
                "source": data.get("source", "OTHER"),
                "document_id": data.get("document_id", ""),
                "page_number": data.get("page_number", 0),
                "chunk_number": data.get("chunk_number", 0),
            }

        return cls(
            chunk_id=data.get("id") or data.get("chunk_id"),
            text=data.get("text", ""),
            embeddings=data.get("embeddings"),
            metadata=DocumentChunkMetadata.from_vector_db(metadata_dict),
            document_id=data.get("document_id", ""),
            parent_chunk_id=data.get("parent_chunk_id"),
            child_chunk_ids=data.get("child_chunk_ids"),
            level=data.get("level"),
        )


class DocumentChunkWithScore(DocumentChunk):
    """A document chunk with an associated similarity score.

    Extends DocumentChunk to include the similarity score from vector search.
    Used in search results to maintain the score alongside the chunk content.

    Attributes:
        score: Similarity score from vector search (0.0 to 1.0)
    """

    score: float | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_vector_db(cls, data: dict[str, Any], score: float | None = None) -> DocumentChunkWithScore:
        """Create instance from vector database format with score.

        Args:
            data: Dictionary from vector database with potentially flattened metadata
            score: Similarity score from search results

        Returns:
            DocumentChunkWithScore instance
        """
        # Extract metadata from either nested 'metadata' dict or top-level fields
        metadata_dict = data.get("metadata", {})
        if not metadata_dict:
            # Build metadata from top-level fields
            metadata_dict = {
                "source": data.get("source", "OTHER"),
                "document_id": data.get("document_id", ""),
                "page_number": data.get("page_number", 0),
                "chunk_number": data.get("chunk_number", 0),
            }

        return cls(
            chunk_id=data.get("id") or data.get("chunk_id"),
            text=data.get("text", ""),
            embeddings=data.get("embeddings"),
            metadata=DocumentChunkMetadata.from_vector_db(metadata_dict),
            document_id=data.get("document_id", ""),
            parent_chunk_id=data.get("parent_chunk_id"),
            child_chunk_ids=data.get("child_chunk_ids"),
            level=data.get("level"),
            score=score or data.get("score"),
        )


class Document(BaseModel):
    """A document with its chunks and metadata.

    Attributes:
        name: Document name
        document_id: Unique identifier
        id: Alias for document_id
        chunks: List of document chunks
        path: Optional file path
        metadata: Document-level metadata
    """

    name: str | None = None
    document_id: str | None = None
    chunks: list[DocumentChunk]
    path: str | None = ""
    metadata: DocumentMetadata | None = None

    @property
    def id(self) -> str | None:
        """Alias for document_id."""
        return self.document_id

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        """Create instance from dictionary data."""
        return cls(
            name=data["name"],
            document_id=data["document_id"],
            chunks=[DocumentChunk.from_dict(chunk) for chunk in data["chunks"]],
            path=data.get("path", ""),
            metadata=DocumentMetadata.model_validate(data["metadata"]) if data.get("metadata") else None,
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
    embeddings: Embeddings | None = None  # Pre-computed if available
    metadata_filter: DocumentMetadataFilter | None = None
    number_of_results: int = 10  # Default to 10 results

    model_config = ConfigDict(from_attributes=True)


class QueryResult(BaseModel):
    """Results from a vector store query.

    Attributes:
        chunk: Retrieved document chunks
        score: Similarity scores for each chunk
        embeddings: Vector embeddings for each chunk
        data: List of chunks (for backward compatibility)
    """

    chunk: DocumentChunkWithScore | None = None
    score: float | None = None
    embeddings: Embeddings | None = None

    @property
    def data(self) -> list[DocumentChunkWithScore]:
        """List of chunks for backward compatibility."""
        return [self.chunk] if self.chunk else []

    @property
    def document(self) -> DocumentChunkWithScore | None:
        """Alias for chunk (for backward compatibility)."""
        return self.chunk

    @property
    def document_id(self) -> str | None:
        """Get document ID from the chunk."""
        return self.chunk.document_id if self.chunk else None

    model_config = ConfigDict(from_attributes=True)

    def __repr__(self) -> str:
        """Readable string representation."""
        if self.chunk:
            score_str = f"{self.score:.3f}" if self.score else "None"
            text_preview = self.chunk.text[:50] if self.chunk.text else ""
            return f"QueryResult(chunk_id={self.chunk.chunk_id}, score={score_str}, text={text_preview}...)"
        return "QueryResult(chunk=None)"


class QueryWithEmbedding(BaseModel):
    """A query with its vector embedding.

    Attributes:
        text: Query text
        embeddings: Vector embedding of the text
        vectors: Alias for embeddings
    """

    text: str
    embeddings: Embeddings

    model_config = ConfigDict(from_attributes=True)

    @property
    def vectors(self) -> Embeddings:
        """Alias for embeddings."""
        return self.embeddings

    @vectors.setter
    def vectors(self, value: Embeddings) -> None:
        """Set vectors (updates embeddings)."""
        self.embeddings = value
