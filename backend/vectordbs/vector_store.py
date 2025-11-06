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
    CollectionStatsResponse,
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

        This method provides a lifecycle hook for connection management. The default
        implementation only sets the connection flag. Subclasses should override this
        method to establish actual database connections.

        Note:
            The default implementation is intentionally minimal to avoid breaking
            existing implementations. Subclasses that manage connection state should
            override both connect() and disconnect() to handle actual connection logic.

        Warning:
            This default implementation does NOT establish a real connection. It only
            sets internal state flags. Implementations must override this method to
            create actual database connections.

        Example:
            >>> class MyVectorStore(VectorStore):
            ...     def connect(self) -> None:
            ...         super().connect()  # Set base class flags
            ...         self.client = MyClient(self.settings.db_url)
            ...         self.client.connect()
        """
        self._connected = True
        self._connection_metadata["connected_at"] = time.time()
        logger.debug(
            "Connection flag set for %s (base implementation - override for real connections)", self.__class__.__name__
        )

    def disconnect(self) -> None:
        """Close connection to the vector database.

        This method provides a lifecycle hook for connection cleanup. The default
        implementation only clears the connection flag. Subclasses should override
        this method to close actual database connections and release resources.

        Note:
            The default implementation is intentionally minimal to avoid breaking
            existing implementations. Subclasses that manage connection state should
            override both connect() and disconnect() to handle actual connection logic.

        Warning:
            This default implementation does NOT close a real connection. It only
            clears internal state flags. Implementations must override this method to
            properly close database connections and release resources.

        Example:
            >>> class MyVectorStore(VectorStore):
            ...     def disconnect(self) -> None:
            ...         if hasattr(self, 'client'):
            ...             self.client.close()
            ...         super().disconnect()  # Clear base class flags
        """
        self._connected = False
        self._connection_metadata["disconnected_at"] = time.time()
        logger.debug(
            "Connection flag cleared for %s (base implementation - override for real disconnections)",
            self.__class__.__name__,
        )

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

        This context manager ensures proper connection lifecycle management by only
        disconnecting connections that IT created. If a connection already exists,
        it leaves it intact on exit to avoid breaking calling code.

        Usage:
            with vector_store.connection_context():
                vector_store.add_documents(...)

        Example with existing connection:
            >>> store = VectorStore(settings)
            >>> store.connect()  # Manual connection
            >>> with store.connection_context():
            ...     store.query(...)  # Uses existing connection
            >>> # Connection still active after context exit
            >>> store.is_connected
            True

        Example without existing connection:
            >>> store = VectorStore(settings)
            >>> with store.connection_context():
            ...     store.query(...)  # Creates connection
            >>> # Connection cleaned up after context exit
            >>> store.is_connected
            False
        """
        # Track if WE created the connection
        needs_disconnect = False
        try:
            if not self._connected:
                self.connect()
                needs_disconnect = True  # Only disconnect what we connected
            yield
        finally:
            if needs_disconnect:
                self.disconnect()

    @asynccontextmanager
    async def async_connection_context(self) -> AsyncIterator[None]:
        """Async context manager for database connections.

        This context manager ensures proper connection lifecycle management by only
        disconnecting connections that IT created. If a connection already exists,
        it leaves it intact on exit to avoid breaking calling code.

        Warning:
            The default implementation calls synchronous connect()/disconnect() methods,
            which WILL BLOCK THE EVENT LOOP if your connect() performs I/O operations.

            If your implementation performs ANY I/O in connect() (database connections,
            network calls, file operations), you MUST override this method with async
            connection methods. Failure to do so will cause performance degradation
            and potential deadlocks in async code paths.

        Usage:
            async with vector_store.async_connection_context():
                await vector_store.async_add_documents(...)

        Example for implementations with async clients (override recommended):
            >>> @asynccontextmanager
            ... async def async_connection_context(self):
            ...     needs_disconnect = False
            ...     try:
            ...         if not self._connected:
            ...             await self.async_connect()  # Async method
            ...             needs_disconnect = True
            ...         yield
            ...     finally:
            ...         if needs_disconnect:
            ...             await self.async_disconnect()  # Async method
        """
        # Track if WE created the connection
        needs_disconnect = False
        try:
            if not self._connected:
                # Default uses sync methods - override if using async client
                self.connect()
                needs_disconnect = True  # Only disconnect what we connected
            yield
        finally:
            if needs_disconnect:
                self.disconnect()

    # Health Check and Statistics

    def health_check(self, timeout: float = 5.0) -> HealthCheckResponse:
        """Check health of the vector database connection.

        This method provides a consistent interface for health checks across all
        vector store implementations. Subclasses can override _health_check_impl()
        to provide implementation-specific health check logic.

        Args:
            timeout: Maximum time to wait for health check in seconds (default: 5.0)

        Returns:
            HealthCheckResponse: Response object containing:
                - success: True if health check passed, False otherwise
                - data: Dictionary with health status information (if successful)
                - error: Error message (if failed)
                - metadata: Additional context (elapsed_seconds, timeout)

        Example:
            >>> response = vector_store.health_check(timeout=10.0)
            >>> if response.success:
            ...     print(f"Status: {response.data['status']}")
        """
        start_time = time.time()
        try:
            health_data = self._health_check_impl(timeout)
            elapsed = time.time() - start_time

            return VectorDBResponse.create_success(
                data=health_data, metadata={"elapsed_seconds": elapsed, "timeout": timeout}
            )
        except VectorStoreError as e:
            # Expected vector store errors
            elapsed = time.time() - start_time
            logger.error("Health check failed after %.2fs: %s", elapsed, str(e), exc_info=True)
            return VectorDBResponse.create_error(
                error=str(e),
                metadata={"elapsed_seconds": elapsed, "timeout": timeout, "error_type": "VectorStoreError"},
            )
        except TimeoutError:
            # Timeout errors
            elapsed = time.time() - start_time
            logger.error("Health check timed out after %.2fs (timeout: %.2fs)", elapsed, timeout, exc_info=True)
            return VectorDBResponse.create_error(
                error=f"Health check timed out after {elapsed:.2f}s",
                metadata={"elapsed_seconds": elapsed, "timeout": timeout, "error_type": "TimeoutError"},
            )
        except Exception as e:
            # Unexpected errors - log with full context
            elapsed = time.time() - start_time
            logger.exception(
                "Unexpected error during health check after %.2fs: %s (type: %s)", elapsed, str(e), type(e).__name__
            )
            return VectorDBResponse.create_error(
                error=f"Unexpected error: {e!s}",
                metadata={"elapsed_seconds": elapsed, "timeout": timeout, "error_type": type(e).__name__},
            )

    def _health_check_impl(self, timeout: float) -> dict[str, Any]:  # noqa: ARG002
        """Implementation-specific health check.

        Default implementation returns basic connection status. Subclasses should
        override this method to provide more detailed health information specific
        to their vector database implementation (e.g., cluster status, node health,
        memory usage, query latency).

        Args:
            timeout: Maximum time to wait for health check in seconds.
                Note: The default implementation does not enforce this timeout.
                Subclasses should implement timeout handling for actual health checks.

        Returns:
            Dictionary with health status information. Default keys:
                - status: "healthy" if connected, "unknown" otherwise
                - connected: Boolean connection status
                - store_type: Name of the vector store implementation

        Raises:
            VectorStoreError: If health check fails due to connection issues
            TimeoutError: If health check exceeds timeout duration

        Example with timeout enforcement:
            >>> import signal
            >>> def _health_check_impl(self, timeout: float) -> dict[str, Any]:
            ...     def timeout_handler(signum, frame):
            ...         raise TimeoutError(f"Health check exceeded {timeout}s")
            ...
            ...     # Set timeout (Unix-like systems only)
            ...     signal.signal(signal.SIGALRM, timeout_handler)
            ...     signal.alarm(int(timeout))
            ...     try:
            ...         # Perform actual health check
            ...         result = self.client.health_check()
            ...         signal.alarm(0)  # Cancel alarm
            ...         return {"status": "healthy", "nodes": result.nodes}
            ...     except Exception:
            ...         signal.alarm(0)  # Cancel alarm
            ...         raise

        Example without timeout (simple):
            >>> def _health_check_impl(self, timeout: float) -> dict[str, Any]:
            ...     return {
            ...         "status": "healthy",
            ...         "connected": self.is_connected,
            ...         "nodes": 3,
            ...         "cluster_status": "green"
            ...     }
        """
        return {
            "status": "healthy" if self.is_connected else "unknown",
            "connected": self.is_connected,
            "store_type": self.__class__.__name__,
        }

    def get_collection_stats(self, collection_name: str) -> CollectionStatsResponse:
        """Get statistics for a collection.

        This method provides a consistent interface for retrieving collection statistics
        across all vector store implementations. Subclasses can override _get_collection_stats_impl()
        to provide implementation-specific statistics.

        Args:
            collection_name: Name of the collection to get statistics for

        Returns:
            VectorDBResponse: Response object containing:
                - success: True if stats retrieved successfully, False otherwise
                - data: Dictionary with collection statistics (if successful)
                - error: Error message (if failed)
                - metadata: Additional context (collection_name, error_type)

        Example:
            >>> response = vector_store.get_collection_stats("my_collection")
            >>> if response.success:
            ...     print(f"Document count: {response.data['count']}")
        """
        try:
            stats = self._get_collection_stats_impl(collection_name)
            return VectorDBResponse.create_success(data=stats, metadata={"collection_name": collection_name})
        except CollectionError as e:
            # Expected error - collection doesn't exist or is inaccessible
            logger.error("Collection '%s' not found or inaccessible: %s", collection_name, str(e), exc_info=True)
            return VectorDBResponse.create_error(
                error=str(e), metadata={"collection_name": collection_name, "error_type": "CollectionError"}
            )
        except NotImplementedError as e:
            # Implementation doesn't support collection stats
            logger.warning("Collection stats not implemented for %s: %s", self.__class__.__name__, str(e))
            return VectorDBResponse.create_error(
                error=str(e), metadata={"collection_name": collection_name, "error_type": "NotImplementedError"}
            )
        except VectorStoreError as e:
            # Expected vector store errors
            logger.error(
                "Vector store error getting stats for collection '%s': %s", collection_name, str(e), exc_info=True
            )
            return VectorDBResponse.create_error(
                error=str(e), metadata={"collection_name": collection_name, "error_type": "VectorStoreError"}
            )
        except Exception as e:
            # Unexpected errors - log with full context
            logger.exception(
                "Unexpected error getting stats for collection '%s': %s (type: %s)",
                collection_name,
                str(e),
                type(e).__name__,
            )
            return VectorDBResponse.create_error(
                error=f"Unexpected error: {e!s}",
                metadata={"collection_name": collection_name, "error_type": type(e).__name__},
            )

    def _get_collection_stats_impl(self, collection_name: str) -> dict[str, Any]:
        """Implementation-specific collection statistics.

        Default implementation raises NotImplementedError. Subclasses should override
        this method to provide actual statistics from their vector database implementation.

        Args:
            collection_name: Name of the collection to get statistics for

        Returns:
            Dictionary with statistics. Common keys should include:
                - count: Number of vectors/documents in the collection
                - dimension: Dimensionality of vectors
                - index_type: Type of index used (e.g., "HNSW", "IVF_FLAT")
                - metric_type: Distance metric (e.g., "L2", "IP", "COSINE")

        Raises:
            CollectionError: If collection doesn't exist or is inaccessible
            VectorStoreError: If statistics cannot be retrieved
            NotImplementedError: If subclass doesn't implement this method

        Example:
            >>> def _get_collection_stats_impl(self, collection_name: str) -> dict[str, Any]:
            ...     collection = self.client.get_collection(collection_name)
            ...     return {
            ...         "count": collection.num_entities,
            ...         "dimension": collection.schema.dimension,
            ...         "index_type": "HNSW",
            ...         "metric_type": "L2"
            ...     }
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _get_collection_stats_impl() to provide collection statistics"
        )

    # Common Utilities

    def _collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists.

        This utility method attempts to retrieve collection statistics to determine
        if a collection exists. It only catches expected errors (CollectionError)
        that indicate a missing collection. Other errors (network issues, timeouts,
        permission errors) are logged and re-raised to avoid masking real problems.

        Args:
            collection_name: Name of the collection to check

        Returns:
            True if collection exists and is accessible, False if collection
            does not exist (CollectionError raised by implementation)

        Raises:
            VectorStoreError: For unexpected errors (network, timeout, permissions)
            that should not be silently caught

        Example:
            >>> if vector_store._collection_exists("my_collection"):
            ...     print("Collection exists")
            ... else:
            ...     print("Collection not found")
        """
        try:
            self._get_collection_stats_impl(collection_name)
            return True
        except CollectionError:
            # Expected error for non-existent collections
            logger.debug("Collection '%s' does not exist", collection_name)
            return False
        except NotImplementedError as e:
            # Implementation hasn't implemented required method - this is a critical gap
            logger.error(
                "Cannot check collection existence: %s doesn't implement _get_collection_stats_impl(). "
                "This is a required implementation for production use.",
                self.__class__.__name__,
            )
            raise NotImplementedError(
                f"{self.__class__.__name__} must implement _get_collection_stats_impl() "
                "to support collection existence checking. This is required for production use."
            ) from e
        except Exception as e:
            # Unexpected errors should not be silently swallowed
            logger.error(
                "Unexpected error checking if collection '%s' exists: %s (type: %s)",
                collection_name,
                str(e),
                type(e).__name__,
                exc_info=True,
            )
            raise VectorStoreError(f"Failed to check collection existence: {e!s}") from e

    def _batch_chunks(self, chunks: list[EmbeddedChunk], batch_size: int) -> list[list[EmbeddedChunk]]:
        """Batch chunks for efficient bulk processing.

        This utility method splits a list of embedded chunks into smaller batches
        for efficient bulk insertion into vector databases. Most vector databases
        have optimal batch sizes (typically 100-1000) for bulk operations.

        Args:
            chunks: List of embedded chunks to batch. Each chunk should contain:
                - embedding: Vector representation
                - document_id: Source document identifier
                - metadata: Additional metadata
            batch_size: Maximum number of chunks per batch. Must be positive.
                Common values: 100 (conservative), 500 (balanced), 1000 (aggressive)

        Returns:
            List of chunk batches, where each batch is a list of EmbeddedChunk objects.
            The last batch may contain fewer chunks than batch_size.

        Raises:
            ValueError: If batch_size is not positive (<=0)

        Example:
            >>> chunks = [chunk1, chunk2, chunk3, chunk4, chunk5]
            >>> batches = vector_store._batch_chunks(chunks, batch_size=2)
            >>> len(batches)
            3
            >>> len(batches[0])  # First batch
            2
            >>> len(batches[-1])  # Last batch (partial)
            1
        """
        if batch_size <= 0:
            raise ValueError(
                f"Batch size must be positive, got: {batch_size}. "
                "Common batch sizes: 100 (conservative), 500 (balanced), 1000 (aggressive)"
            )

        # Warn about very large batch sizes that may cause memory issues
        if batch_size > 10000:
            logger.warning(
                "Batch size %d is very large and may cause memory issues. "
                "Consider using smaller batches (100-1000 recommended). "
                "Chunk count: %d",
                batch_size,
                len(chunks),
            )

        batches: list[list[EmbeddedChunk]] = []
        for i in range(0, len(chunks), batch_size):
            batches.append(chunks[i : i + batch_size])

        logger.debug(
            "Created %d batches from %d chunks (batch_size=%d, last_batch_size=%d)",
            len(batches),
            len(chunks),
            batch_size,
            len(batches[-1]) if batches else 0,
        )
        return batches

    def _validate_collection_config(self, config: CollectionConfig) -> None:
        """Validate collection configuration against system settings.

        This method provides additional validation beyond Pydantic's base validation
        to ensure collection configurations are compatible with the vector store settings.

        Note:
            Pydantic's CollectionConfig model already validates:
            - collection_name has min_length=1 (prevents empty strings)
            - dimension has ge=1 (prevents non-positive values)

            This method adds:
            - Whitespace-only collection name detection (Pydantic doesn't catch this)
            - Dimension compatibility with embedding model

        Args:
            config: Collection configuration to validate. Must include:
                - dimension: Vector dimensionality
                - collection_name: Name of the collection
                - Additional implementation-specific fields

        Raises:
            ValueError: If configuration is invalid or incompatible with settings.
                Common issues:
                - Whitespace-only collection name
                - Dimension mismatch with embedding model

        Example:
            >>> config = CollectionConfig(
            ...     collection_name="my_collection",
            ...     dimension=768,
            ...     metric="cosine"
            ... )
            >>> vector_store._validate_collection_config(config)
        """
        # Validate collection name is not whitespace-only
        # Note: Pydantic ensures non-empty, but doesn't check for whitespace-only
        if not config.collection_name.strip():
            error_msg = "Collection name cannot be whitespace-only"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate dimension matches embedding model
        if config.dimension != self.settings.embedding_dim:
            error_msg = (
                f"Collection dimension ({config.dimension}) doesn't match "
                f"embedding model dimension ({self.settings.embedding_dim}). "
                f"This will cause insertion failures. "
                f"Collection: {config.collection_name}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Additional validation can be added by subclasses
        logger.debug("Collection config validated: name=%s, dimension=%d", config.collection_name, config.dimension)

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
