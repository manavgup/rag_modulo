"""Enhanced VectorStore abstract base class with pydantic integration.

This module provides a modernized abstract base class for vector database
implementations with enhanced pydantic models, common utilities, consistent
error handling, and connection management (Issue #212).
"""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from core.config import Settings

from .data_types import (
    CollectionConfig,
    Document,
    DocumentMetadataFilter,
    EmbeddedChunk,
    HealthCheckResponse,
    QueryResult,
    QueryWithEmbedding,
    VectorDBResponse,
    VectorSearchRequest,
)
from .error_types import CollectionError, VectorStoreError

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """Enhanced abstract base class for vector stores with pydantic integration.

    This class provides:
    - Pydantic model integration for type safety and validation
    - Common utilities for batch processing and collection management
    - Standardized error handling and response structures
    - Connection management with context managers
    - Health check and statistics operations
    - Backward compatibility with existing implementations

    Subclasses must implement the abstract methods prefixed with '_' which
    accept pydantic models. Public methods provide standardized validation
    and error handling.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the vector store with settings.
        All subclasses must call this constructor to ensure proper dependency injection.

        Args:
            settings: Settings object containing configuration for the vector store
        """
        self.settings = settings
        self._connected = False
        self._connection_metadata: dict[str, Any] = {}

    # Connection Management

    def connect(self) -> None:
        """Establish connection to the vector database.

        Subclasses should override this method to implement connection logic.
        Default implementation marks connection as established.
        """
        self._connected = True
        self._connection_metadata["connected_at"] = time.time()
        logger.info("Connected to vector store")

    def disconnect(self) -> None:
        """Close connection to the vector database.

        Subclasses should override this method to implement disconnection logic.
        Default implementation marks connection as closed.
        """
        self._connected = False
        self._connection_metadata["disconnected_at"] = time.time()
        logger.info("Disconnected from vector store")

    @property
    def is_connected(self) -> bool:
        """Check if connected to the vector database.

        Returns:
            True if connected, False otherwise
        """
        return self._connected

    @contextmanager
    def connection_context(self) -> Iterator[None]:
        """Context manager for database connections.

        Usage:
            with vector_store.connection_context():
                vector_store.add_documents(...)
        """
        try:
            if not self._connected:
                self.connect()
            yield
        finally:
            if self._connected:
                self.disconnect()

    @asynccontextmanager
    async def async_connection_context(self) -> AsyncIterator[None]:
        """Async context manager for database connections.

        Usage:
            async with vector_store.async_connection_context():
                await vector_store.async_add_documents(...)
        """
        try:
            if not self._connected:
                self.connect()
            yield
        finally:
            if self._connected:
                self.disconnect()

    # Health Check and Statistics

    def health_check(self, timeout: float = 5.0) -> HealthCheckResponse:
        """Check health of the vector database connection.

        Args:
            timeout: Maximum time to wait for health check (seconds)

        Returns:
            HealthCheckResponse with status and metadata
        """
        start_time = time.time()
        try:
            # Default implementation - subclasses should override
            health_data = self._health_check_impl(timeout)
            elapsed = time.time() - start_time

            return VectorDBResponse.create_success(data=health_data)
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("Health check failed: %s", str(e))
            return VectorDBResponse.create_error(
                error=str(e), metadata={"elapsed_seconds": elapsed, "timeout": timeout}
            )

    @abstractmethod
    def _health_check_impl(self, timeout: float) -> dict[str, Any]:
        """Implementation-specific health check.

        Args:
            timeout: Maximum time to wait

        Returns:
            Dictionary with health status information

        Raises:
            VectorStoreError: If health check fails
        """

    def get_collection_stats(self, collection_name: str) -> VectorDBResponse:
        """Get statistics for a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            VectorDBResponse with collection statistics
        """
        try:
            stats = self._get_collection_stats_impl(collection_name)
            return VectorDBResponse.create_success(data=stats)
        except Exception as e:
            logger.error("Failed to get stats for collection %s: %s", collection_name, str(e))
            return VectorDBResponse.create_error(error=str(e), metadata={"collection_name": collection_name})

    @abstractmethod
    def _get_collection_stats_impl(self, collection_name: str) -> dict[str, Any]:
        """Implementation-specific collection statistics.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with statistics (count, dimensions, etc.)

        Raises:
            CollectionError: If collection doesn't exist or stats unavailable
        """

    # Common Utilities

    def _collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection exists, False otherwise
        """
        try:
            self._get_collection_stats_impl(collection_name)
            return True
        except (CollectionError, VectorStoreError):
            return False

    def _batch_chunks(self, chunks: list[EmbeddedChunk], batch_size: int) -> list[list[EmbeddedChunk]]:
        """Batch chunks for efficient processing.

        Args:
            chunks: List of embedded chunks
            batch_size: Size of each batch

        Returns:
            List of chunk batches
        """
        if batch_size <= 0:
            raise ValueError("Batch size must be positive")

        batches: list[list[EmbeddedChunk]] = []
        for i in range(0, len(chunks), batch_size):
            batches.append(chunks[i : i + batch_size])

        logger.debug("Created %d batches from %d chunks (batch_size=%d)", len(batches), len(chunks), batch_size)
        return batches

    def _validate_collection_config(self, config: CollectionConfig) -> None:
        """Validate collection configuration.

        Args:
            config: Collection configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        # Basic validation is done by pydantic, add extra checks here
        if config.dimension != self.settings.embedding_dim:
            logger.warning(
                "Collection dimension (%d) doesn't match settings (%d)", config.dimension, self.settings.embedding_dim
            )

    # Implementation Methods (to be overridden by subclasses)

    @abstractmethod
    def _create_collection_impl(self, config: CollectionConfig) -> dict[str, Any]:
        """Implementation-specific collection creation.

        Args:
            config: Collection configuration

        Returns:
            Dictionary with creation result metadata

        Raises:
            CollectionError: If creation fails
        """

    @abstractmethod
    def _add_documents_impl(self, collection_name: str, chunks: list[EmbeddedChunk]) -> list[str]:
        """Implementation-specific document addition.

        Args:
            collection_name: Target collection
            chunks: List of embedded chunks to add

        Returns:
            List of document IDs that were added

        Raises:
            DocumentError: If addition fails
        """

    @abstractmethod
    def _search_impl(self, request: VectorSearchRequest) -> list[QueryResult]:
        """Implementation-specific search.

        Args:
            request: Search request

        Returns:
            List of query results

        Raises:
            VectorStoreError: If search fails
        """

    @abstractmethod
    def _delete_collection_impl(self, collection_name: str) -> None:
        """Implementation-specific collection deletion.

        Args:
            collection_name: Name of collection to delete

        Raises:
            CollectionError: If deletion fails
        """

    # Public API Methods (existing implementations must override these)

    @abstractmethod
    def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:
        """Creates a collection in the vector store.

        Args:
            collection_name: Name of the collection to create
            metadata: Optional metadata for the collection

        Note:
            Implementations can use _create_collection_impl() internally with
            CollectionConfig for enhanced validation and type safety.
        """

    @abstractmethod
    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Adds documents to the vector store.

        Args:
            collection_name: Name of the collection
            documents: List of documents to add

        Returns:
            List[str]: List of document IDs that were added

        Note:
            Implementations can use _add_documents_impl() internally with
            EmbeddedChunk for enhanced validation and batch processing.
        """

    @abstractmethod
    def retrieve_documents(self, query: str, collection_name: str, number_of_results: int = 10) -> list[QueryResult]:
        """Retrieves documents based on a query or query embedding.

        Args:
            query: Either a text string or a QueryWithEmbedding object.
            collection_name: Name of the collection to search in.
            number_of_results: Number of top results to return. (Default: 10)

        Returns:
            A list of QueryResult objects containing the retrieved documents and their scores.

        Note:
            Implementations can use _search_impl() internally with
            VectorSearchRequest for enhanced validation.
        """

    @abstractmethod
    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        filter: DocumentMetadataFilter | None = None,
    ) -> list[QueryResult]:
        """Queries the vector store with filtering and query mode options.

        Args:
            collection_name: Name of the collection to search in.
            query: Either a text string or a QueryWithEmbedding object.
            number_of_results: Number of top results to return. (Default: 10)
            filter: Optional metadata filter to apply to the search.

        Returns:
            A list of QueryResult objects containing the retrieved documents and their scores.

        Note:
            Implementations can use _search_impl() internally with
            VectorSearchRequest for enhanced validation.
        """

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """Deletes a collection from the vector store.

        Args:
            collection_name: Name of the collection to delete

        Note:
            Implementations can use _delete_collection_impl() for consistency.
        """

    @abstractmethod
    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Deletes documents by their IDs from the vector store.

        Args:
            collection_name: Name of the collection
            document_ids: List of document IDs to delete
        """

    @abstractmethod
    def count_document_chunks(self, collection_name: str, document_id: str) -> int:
        """Count the number of chunks for a specific document.

        Args:
            collection_name: Name of the collection to search in.
            document_id: The document ID to count chunks for.

        Returns:
            Number of chunks found for the document.
        """
