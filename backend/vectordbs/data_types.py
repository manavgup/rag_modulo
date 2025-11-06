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


class DocumentChunkWithScore(DocumentChunk):
    """A document chunk with an associated similarity score.

    Extends DocumentChunk to include the similarity score from vector search.
    Used in search results to maintain the score alongside the chunk content.

    Attributes:
        score: Similarity score from vector search (0.0 to 1.0)
    """

    score: float | None = None

    model_config = ConfigDict(from_attributes=True)


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


# Enhanced Pydantic Models for Vector Database Operations (Issue #211)


class EmbeddedChunk(BaseModel):
    """A document chunk with required embeddings for vector database operations.

    This model extends DocumentChunk to enforce that embeddings are present
    and valid before insertion into vector databases. Used to eliminate
    runtime errors from missing embeddings.

    Attributes:
        chunk_id: Unique identifier for the chunk
        text: The actual text content
        embeddings: Required vector embedding of the text (non-empty)
        metadata: Associated chunk-level metadata
        document_id: Reference to parent document
        parent_chunk_id: Reference to parent chunk (for hierarchical chunking)
        child_chunk_ids: References to child chunks (for hierarchical chunking)
        level: Hierarchy level (0=root, 1=parent, 2=child, etc.)
    """

    chunk_id: str
    text: str
    embeddings: Embeddings  # Required, not optional
    metadata: DocumentChunkMetadata | None = None
    document_id: str | None = None
    parent_chunk_id: str | None = None
    child_chunk_ids: list[str] | None = None
    level: int | None = None

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context: Any) -> None:
        """Validate embeddings after initialization."""
        if not self.embeddings or len(self.embeddings) == 0:
            raise ValueError("Embeddings must be non-empty for EmbeddedChunk")

    @classmethod
    def from_chunk(cls, chunk: DocumentChunk) -> "EmbeddedChunk":
        """Create EmbeddedChunk from DocumentChunk with validation.

        Args:
            chunk: Source DocumentChunk

        Returns:
            EmbeddedChunk instance

        Raises:
            ValueError: If chunk lacks embeddings or chunk_id
        """
        if not chunk.embeddings:
            raise ValueError(f"Cannot create EmbeddedChunk: chunk {chunk.chunk_id} has no embeddings")
        if not chunk.chunk_id:
            raise ValueError("Cannot create EmbeddedChunk: chunk has no chunk_id")

        return cls(
            chunk_id=chunk.chunk_id,
            text=chunk.text or "",
            embeddings=chunk.embeddings,
            metadata=chunk.metadata,
            document_id=chunk.document_id,
            parent_chunk_id=chunk.parent_chunk_id,
            child_chunk_ids=chunk.child_chunk_ids,
            level=chunk.level,
        )

    def to_vector_metadata(self) -> dict[str, Any]:
        """Convert to metadata dict suitable for vector database storage.

        Returns:
            Dictionary with flattened metadata for vector DB
        """
        result: dict[str, Any] = {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "document_id": self.document_id,
            "parent_chunk_id": self.parent_chunk_id,
            "level": self.level,
        }

        if self.metadata:
            result.update(
                {
                    "source": str(self.metadata.source) if self.metadata.source else None,
                    "page_number": self.metadata.page_number,
                    "chunk_number": self.metadata.chunk_number,
                    "start_index": self.metadata.start_index,
                    "end_index": self.metadata.end_index,
                    "author": self.metadata.author,
                }
            )

        # Remove None values
        return {k: v for k, v in result.items() if v is not None}

    def to_vector_db(self) -> tuple[Embeddings, dict[str, Any]]:
        """Prepare data for vector database insertion.

        Returns:
            Tuple of (embeddings, metadata_dict)
        """
        return self.embeddings, self.to_vector_metadata()


class CollectionConfig(BaseModel):
    """Configuration for vector database collections.

    Attributes:
        name: Collection name
        dimension: Vector dimension (embedding size)
        metric_type: Distance metric (COSINE, L2, IP)
        index_type: Index type (IVF_FLAT, HNSW, etc.)
        index_params: Additional index parameters
        metadata_schema: Optional metadata field definitions
    """

    name: str
    dimension: int
    metric_type: str = "COSINE"
    index_type: str = "IVF_FLAT"
    index_params: dict[str, Any] | None = None
    metadata_schema: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context: Any) -> None:
        """Validate configuration after initialization."""
        if self.dimension <= 0:
            raise ValueError("Dimension must be positive")
        if self.metric_type not in ["COSINE", "L2", "IP", "EUCLIDEAN"]:
            raise ValueError(f"Invalid metric_type: {self.metric_type}")


class DocumentIngestionRequest(BaseModel):
    """Request model for document ingestion into vector databases.

    Attributes:
        collection_name: Target collection name
        documents: Documents to ingest
        batch_size: Batch size for processing (default: 100)
        create_collection: Whether to create collection if not exists
        collection_config: Configuration if creating collection
    """

    collection_name: str
    documents: list[Document]
    batch_size: int = 100
    create_collection: bool = False
    collection_config: CollectionConfig | None = None

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context: Any) -> None:
        """Validate request after initialization."""
        if not self.documents:
            raise ValueError("Documents list cannot be empty")
        if self.batch_size <= 0:
            raise ValueError("Batch size must be positive")
        if self.create_collection and not self.collection_config:
            raise ValueError("collection_config required when create_collection=True")

    def extract_embedded_chunks(self) -> list[EmbeddedChunk]:
        """Extract all embedded chunks from documents.

        Returns:
            List of EmbeddedChunk instances

        Raises:
            ValueError: If any chunk lacks embeddings
        """
        embedded_chunks: list[EmbeddedChunk] = []
        for document in self.documents:
            for chunk in document.chunks:
                embedded_chunks.append(EmbeddedChunk.from_chunk(chunk))
        return embedded_chunks


class VectorSearchRequest(BaseModel):
    """Request model for vector database searches.

    Attributes:
        collection_name: Collection to search
        query: Query text or embedding
        number_of_results: Number of results to return (default: 10)
        metadata_filter: Optional metadata filtering
        include_embeddings: Whether to include embeddings in results
    """

    collection_name: str
    query: str | QueryWithEmbedding
    number_of_results: int = 10
    metadata_filter: DocumentMetadataFilter | None = None
    include_embeddings: bool = False

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context: Any) -> None:
        """Validate request after initialization."""
        if self.number_of_results <= 0:
            raise ValueError("number_of_results must be positive")

    def get_query_text(self) -> str:
        """Get query text from query field.

        Returns:
            Query text string
        """
        if isinstance(self.query, str):
            return self.query
        return self.query.text

    def get_query_embeddings(self) -> Embeddings | None:
        """Get query embeddings if available.

        Returns:
            Embeddings if query is QueryWithEmbedding, None otherwise
        """
        if isinstance(self.query, QueryWithEmbedding):
            return self.query.embeddings
        return None


class VectorDBResponse(BaseModel):
    """Generic response wrapper for vector database operations.

    Provides consistent response structure with success/error states
    and optional data payload.

    Attributes:
        success: Whether operation succeeded
        message: Optional status message
        data: Optional response data
        error: Optional error message
        metadata: Optional operation metadata (timing, counts, etc.)
    """

    success: bool
    message: str | None = None
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def success_response(
        cls, data: Any = None, message: str | None = None, metadata: dict[str, Any] | None = None
    ) -> "VectorDBResponse":
        """Create a success response.

        Args:
            data: Response data
            message: Optional success message
            metadata: Optional operation metadata

        Returns:
            VectorDBResponse with success=True
        """
        return cls(success=True, data=data, message=message, metadata=metadata)

    @classmethod
    def error_response(cls, error: str, data: Any = None, metadata: dict[str, Any] | None = None) -> "VectorDBResponse":
        """Create an error response.

        Args:
            error: Error message
            data: Optional partial data
            metadata: Optional operation metadata

        Returns:
            VectorDBResponse with success=False
        """
        return cls(success=False, error=error, data=data, metadata=metadata)


# Type aliases for common response types
IngestionResponse = VectorDBResponse
SearchResponse = VectorDBResponse
HealthCheckResponse = VectorDBResponse
CollectionStatsResponse = VectorDBResponse
