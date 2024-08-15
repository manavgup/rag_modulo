from .vector_store import VectorStore


def get_datastore(datastore: str) -> VectorStore:
    if not datastore:
        raise ValueError("Datastore must not be None or empty")

    if datastore == "pinecone":
        from .pinecone_store import PineconeStore

        return PineconeStore()
    elif datastore == "weaviate":
        from .weaviate_store import WeaviateDataStore

        return WeaviateDataStore()
    elif datastore == "milvus":
        from .milvus_store import MilvusStore

        return MilvusStore()
    elif datastore == "elasticsearch":
        from .elasticsearch_store import ElasticSearchStore

        return ElasticSearchStore()
    else:
        raise ValueError(f"Unsupported vector database: {datastore}")
