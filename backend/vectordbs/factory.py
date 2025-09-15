"""
This module provides a factory function for creating different VectorStore instances.

It supports various vector database backends such as Pinecone, Weaviate, Milvus,
and Elasticsearch. The primary function, `get_datastore`, abstracts the
instantiation process, allowing other parts of the application to
interact with different vector stores through a unified `VectorStore`
interface without needing to know the specific implementation details.
"""

import warnings

from core.config import Settings, get_settings

from .elasticsearch_store import ElasticSearchStore
from .milvus_store import MilvusStore
from .pinecone_store import PineconeStore
from .vector_store import VectorStore
from .weaviate_store import WeaviateDataStore


class VectorStoreFactory:
    """Factory class for creating vector store instances with dependency injection."""

    def __init__(self, settings: Settings) -> None:
        """Initialize factory with settings dependency.

        Args:
            settings: Configuration settings to inject into vector stores
        """
        self.settings = settings
        self._datastore_mapping: dict[str, type[VectorStore]] = {
            "pinecone": PineconeStore,
            "weaviate": WeaviateDataStore,
            "milvus": MilvusStore,
            "elasticsearch": ElasticSearchStore,
        }

    def get_datastore(self, datastore: str) -> VectorStore:
        """
        Create a vector store instance with injected configuration.

        Args:
            datastore (str): The name of the vector database to use.

        Returns:
            VectorStore: An instance of the requested vector store.

        Raises:
            ValueError: If the specified datastore is not supported.
        """
        try:
            store_class = self._datastore_mapping[datastore]
            return store_class(self.settings)  # Inject settings
        except KeyError as exc:
            raise ValueError(
                f"Unsupported vector database: {datastore}. "
                f"Supported databases are {list(self._datastore_mapping.keys())}"
            ) from exc

    def list_supported_stores(self) -> list[str]:
        """List all supported vector store types."""
        return list(self._datastore_mapping.keys())


# DEPRECATED: Legacy function for backward compatibility during migration
# This will be removed in a future version. Use VectorStoreFactory instead.
def get_datastore(datastore: str) -> VectorStore:
    """
    Factory function to get a vector store instance.

    DEPRECATED: This function accesses global settings directly.
    Use VectorStoreFactory with dependency injection instead.

    Args:
        datastore (str): The name of the vector database to use.

    Returns:
        VectorStore: An instance of the requested vector store.

    Raises:
        ValueError: If the specified datastore is not supported.
    """
    warnings.warn(
        "get_datastore() is deprecated and will be removed. Use VectorStoreFactory with dependency injection instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    factory = VectorStoreFactory(get_settings())
    return factory.get_datastore(datastore)
