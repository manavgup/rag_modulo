"""Core data types for the RAG system."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class EmbeddedChunk(DocumentChunk):
    """A DocumentChunk with mandatory (non-optional) embeddings.

    This class ensures that embeddings are always present, making it suitable
    for vector database operations that require embedded content.

    Attributes:
        embeddings: Required vector embedding (non-optional)
        All other attributes inherited from DocumentChunk
    """

    embeddings: Embeddings = Field(..., description="Required vector embedding for this chunk")

    @field_validator("embeddings")
    @classmethod
    def validate_embeddings_not_empty(cls, v: Embeddings) -> Embeddings:
        """Ensure embeddings list is not empty."""
        if not v:
            raise ValueError("Embeddings cannot be empty")
        return v

    @classmethod
    def from_chunk(cls, chunk: DocumentChunk, embeddings: Embeddings | None = None) -> EmbeddedChunk:
        """Convert a DocumentChunk to an EmbeddedChunk.

        Args:
            chunk: The source DocumentChunk
            embeddings: Optional embeddings to use (if not provided, uses chunk.embeddings)

        Returns:
            EmbeddedChunk with mandatory embeddings

        Raises:
            ValueError: If embeddings are not available
        """
        emb = embeddings or chunk.embeddings
        if not emb:
            raise ValueError("Cannot create EmbeddedChunk without embeddings")

        return cls(
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            embeddings=emb,
            metadata=chunk.metadata,
            document_id=chunk.document_id,
            parent_chunk_id=chunk.parent_chunk_id,
            child_chunk_ids=chunk.child_chunk_ids,
            level=chunk.level,
        )

    def to_vector_metadata(self) -> dict[str, Any]:
        """Convert to metadata dictionary suitable for vector database storage.

        Returns:
            Dictionary containing all metadata fields for vector DB
        """
        base_metadata = {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "document_id": self.document_id,
            "parent_chunk_id": self.parent_chunk_id,
            "child_chunk_ids": self.child_chunk_ids,
            "level": self.level,
        }

        # Add chunk metadata if present
        if self.metadata:
            base_metadata.update(self.metadata.model_dump(exclude_none=True))

        # Remove None values
        return {k: v for k, v in base_metadata.items() if v is not None}

    def to_vector_db(self) -> dict[str, Any]:
        """Convert to complete vector database record format.

        Returns:
            Dictionary containing embeddings and metadata for vector DB insertion
        """
        return {"id": self.chunk_id, "vector": self.embeddings, "metadata": self.to_vector_metadata()}


class DocumentIngestionRequest(BaseModel):
    """Request model for ingesting documents into a vector database.

    Handles batching and provides convenient access to embedded chunks.

    Attributes:
        chunks: List of document chunks to ingest
        collection_id: Target collection identifier
        batch_size: Number of chunks to process per batch (default: 100)
    """

    chunks: list[DocumentChunk] = Field(..., description="Document chunks to ingest")
    collection_id: str = Field(..., description="Target collection identifier")
    batch_size: int = Field(default=100, ge=1, le=1000, description="Batch size for processing")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("chunks")
    @classmethod
    def validate_chunks_not_empty(cls, v: list[DocumentChunk]) -> list[DocumentChunk]:
        """Ensure chunks list is not empty."""
        if not v:
            raise ValueError("Chunks list cannot be empty")
        return v

    def get_embedded_chunks(self) -> list[EmbeddedChunk]:
        """Extract chunks that have embeddings.

        Returns:
            List of EmbeddedChunk instances

        Raises:
            ValueError: If a chunk's embeddings are invalid
        """
        embedded_chunks = []
        for chunk in self.chunks:
            if chunk.embeddings:
                embedded_chunks.append(EmbeddedChunk.from_chunk(chunk))
        return embedded_chunks

    def get_batches(self) -> list[list[DocumentChunk]]:
        """Split chunks into batches based on batch_size.

        Returns:
            List of chunk batches
        """
        batches = []
        for i in range(0, len(self.chunks), self.batch_size):
            batches.append(self.chunks[i : i + self.batch_size])
        return batches


class VectorSearchRequest(BaseModel):
    """Request model for vector database searches.

    Standardizes search operations with support for both text and vector queries.

    Attributes:
        query_text: Text query to search for (optional if query_vector provided)
        query_vector: Pre-computed query embedding (optional if query_text provided)
        collection_id: Collection to search in
        top_k: Number of results to return (default: 10)
        metadata_filter: Optional metadata filtering criteria
        include_metadata: Whether to include metadata in results (default: True)
        include_vectors: Whether to include vectors in results (default: False)
    """

    query_text: str | None = Field(default=None, description="Text query to search for")
    query_vector: Embeddings | None = Field(default=None, description="Pre-computed query embedding")
    collection_id: str = Field(..., description="Collection to search in")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    metadata_filter: DocumentMetadataFilter | None = Field(default=None, description="Optional metadata filtering")
    include_metadata: bool = Field(default=True, description="Include metadata in results")
    include_vectors: bool = Field(default=False, description="Include vectors in results")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("query_text", "query_vector")
    @classmethod
    def validate_query_provided(cls, v: Any) -> Any:
        """Ensure at least one query type is provided."""
        # This validator runs for each field, so we'll do the cross-field validation in model_validator
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate that at least one query type is provided."""
        if not self.query_text and not self.query_vector:
            raise ValueError("Either query_text or query_vector must be provided")

    def to_vector_query(self) -> VectorQuery:
        """Convert to VectorQuery model.

        Returns:
            VectorQuery instance for backward compatibility
        """
        return VectorQuery(
            text=self.query_text or "",
            embeddings=self.query_vector,
            metadata_filter=self.metadata_filter,
            number_of_results=self.top_k,
        )


class CollectionConfig(BaseModel):
    """Configuration for a vector database collection.

    Manages collection settings with database-specific validation.

    Attributes:
        collection_name: Name of the collection
        dimension: Vector dimension size
        metric_type: Distance metric (L2, IP, COSINE)
        index_type: Index type (FLAT, IVF_FLAT, HNSW, etc.)
        index_params: Database-specific index parameters
        description: Optional collection description
    """

    collection_name: str = Field(..., min_length=1, max_length=255, description="Collection name")
    dimension: int = Field(..., ge=1, le=4096, description="Vector dimension size")
    metric_type: str = Field(default="L2", description="Distance metric type")
    index_type: str = Field(default="HNSW", description="Index type")
    index_params: dict[str, Any] = Field(default_factory=dict, description="Database-specific index parameters")
    description: str | None = Field(default=None, max_length=1000, description="Collection description")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("metric_type")
    @classmethod
    def validate_metric_type(cls, v: str) -> str:
        """Validate metric type is one of the supported types."""
        valid_metrics = ["L2", "IP", "COSINE", "HAMMING", "JACCARD"]
        v_upper = v.upper()
        if v_upper not in valid_metrics:
            raise ValueError(f"Invalid metric_type. Must be one of: {', '.join(valid_metrics)}")
        return v_upper

    @field_validator("index_type")
    @classmethod
    def validate_index_type(cls, v: str) -> str:
        """Validate index type is one of the supported types."""
        valid_indexes = ["FLAT", "IVF_FLAT", "IVF_SQ8", "IVF_PQ", "HNSW", "ANNOY"]
        v_upper = v.upper()
        if v_upper not in valid_indexes:
            raise ValueError(f"Invalid index_type. Must be one of: {', '.join(valid_indexes)}")
        return v_upper

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database-specific usage.

        Returns:
            Dictionary representation suitable for vector DB creation
        """
        return self.model_dump(exclude_none=True)


# Generic type variable for response data
T = TypeVar("T")


class VectorDBResponse[T](BaseModel):
    """Generic response wrapper for vector database operations.

    Provides consistent success/error handling across all vector DB operations.

    Attributes:
        success: Whether the operation succeeded
        data: Response data (type depends on operation)
        error: Error message if operation failed
        metadata: Optional metadata about the operation
    """

    success: bool = Field(..., description="Whether the operation succeeded")
    data: T | None = Field(default=None, description="Response data")
    error: str | None = Field(default=None, description="Error message if operation failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional operation metadata")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def create_success(cls, data: T, metadata: dict[str, Any] | None = None) -> VectorDBResponse[T]:
        """Create a success response.

        Args:
            data: The response data
            metadata: Optional metadata about the operation

        Returns:
            VectorDBResponse with success=True
        """
        return cls(success=True, data=data, error=None, metadata=metadata or {})

    @classmethod
    def create_error(cls, error: str, metadata: dict[str, Any] | None = None) -> VectorDBResponse[T]:
        """Create an error response.

        Args:
            error: Error message
            metadata: Optional metadata about the operation

        Returns:
            VectorDBResponse with success=False
        """
        return cls(success=False, data=None, error=error, metadata=metadata or {})

    def is_success(self) -> bool:
        """Check if the operation was successful.

        Returns:
            True if success, False otherwise
        """
        return self.success

    def is_error(self) -> bool:
        """Check if the operation failed.

        Returns:
            True if error, False otherwise
        """
        return not self.success

    def get_data_or_raise(self) -> T:
        """Get data or raise an exception if operation failed.

        Returns:
            The response data

        Raises:
            ValueError: If the operation failed
        """
        if self.is_error():
            raise ValueError(f"Operation failed: {self.error}")
        if self.data is None:
            raise ValueError("No data available in response")
        return self.data


# Type aliases for common response types
VectorDBIngestionResponse = VectorDBResponse[list[str]]  # List of ingested IDs
VectorDBSearchResponse = VectorDBResponse[list[QueryResult]]  # Search results
VectorDBCollectionResponse = VectorDBResponse[dict[str, Any]]  # Collection info
VectorDBDeleteResponse = VectorDBResponse[bool]  # Delete success status
HealthCheckResponse = VectorDBResponse[dict[str, Any]]  # Health check status
CollectionStatsResponse = VectorDBResponse[dict[str, Any]]  # Collection statistics
