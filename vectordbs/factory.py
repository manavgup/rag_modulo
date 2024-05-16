import os
from types import VectorStore

def get_datastore(datastore: str) -> VectorStore:
    assert datastore is not None

    match datastore:
        case "pinecone":
            from vectordbs.pinecone_store import PineconeDataStore

            return PineconeDataStore()
        case "weaviate":
            from vectordbs.weaviate_store import WeaviateDataStore

            return WeaviateDataStore()
        case "milvus":
            from vectordbs.milvus_store import MilvusDataStore

            return MilvusDataStore()
        case "elasticsearch":
            from vectordbs.elasticsearch_store import ElasticSearchDataStore

            return ElasticSearchDataStore()
        case _:
            raise ValueError(f"Unsupported vector database: {datastore}")