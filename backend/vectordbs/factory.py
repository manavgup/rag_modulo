"""
This module provides a factory function for creating different VectorStore instances.

It supports various vector database backends such as Pinecone, Weaviate, Milvus,
and Elasticsearch. The primary function, `get_datastore`, abstracts the
instantiation process, allowing other parts of the application to
interact with different vector stores through a unified `VectorStore`
interface without needing to know the specific implementation details.
"""


from .elasticsearch_store import ElasticSearchStore
from .milvus_store import MilvusStore
from .pinecone_store import PineconeStore
from .vector_store import VectorStore
from .weaviate_store import WeaviateDataStore


def get_datastore(datastore: str) -> VectorStore:
    """
    Factory function to get a vector store instance.

    Args:
        datastore (str): The name of the vector database to use.

    Returns:
        VectorStore: An instance of the requested vector store.

    Raises:
        ValueError: If the specified datastore is not supported.
    """
    datastore_mapping: dict[str, type[VectorStore]] = {
        "pinecone": PineconeStore,
        "weaviate": WeaviateDataStore,
        "milvus": MilvusStore,
        "elasticsearch": ElasticSearchStore,
    }

    try:
        store_class = datastore_mapping[datastore]
        return store_class()
    except KeyError as exc:
        raise ValueError(f"Unsupported vector database: {datastore}. " f"Supported databases are {list(datastore_mapping.keys())}") from exc
