from typing import List, Optional
from elasticsearch import Elasticsearch
import numpy as np
from data_types import VectorStore

class ElasticSearchDataStore(VectorStore):
    def __init__(self, hosts: List[str], index_name: str):
        self.es = Elasticsearch(hosts=hosts)
        self.index_name = index_name

    def create_collection(self, name: str, dim: int, mappings: Optional[dict] = None):
        """
        Create a new Elasticsearch index.

        Args:
            name (str): The name of the index to create.
            dim (int): The dimension of the vectors.
            mappings (Optional[dict]): Custom mappings for the index.
        """
        if not self.es.indices.exists(index=name):
            default_mappings = {
                "properties": {
                    "id": {"type": "text"},
                    "embedding": {"type": "dense_vector", "dims": dim},
                    "text": {"type": "text"}
                }
            }
            mappings = mappings or default_mappings
            self.es.indices.create(index=name, mappings=mappings)

    def delete_collection(self, name: str):
        """
        Delete an existing Elasticsearch index.

        Args:
            name (str): The name of the index to delete.
        """
        if self.es.indices.exists(index=name):
            self.es.indices.delete(index=name)

    def add_documents(self, collection_name: str, documents: List[dict]):
        """
        Add a list of documents to the index.

        Args:
            collection_name (str): The name of the index to add documents to.
            documents (List[dict]): The list of documents to add.
                Each document should be a dictionary with 'text' and 'embedding' keys.
        """
        bulk_data = []
        for doc in documents:
            bulk_data.append({
                "index": {
                    "_index": collection_name,
                }
            })
            bulk_data.append(doc)

        self.es.bulk(bulk_data)

    def retrieve_documents(self, collection_name: str, search_query: List[float], top_k: int = 10):
        """
        Retrieve documents from the index.

        Args:
            collection_name (str): The name of the index to retrieve documents from.
            search_query (List[float]): The search query (vector) to filter documents.
            top_k (int): The maximum number of results to return (default: 10).

        Returns:
            List[dict]: The list of retrieved documents.
        """
        query = {
            "script_score": {
                "query": {"match_all": {}},
                "script": {
                    "source": "cosineSimilarity(params.query_vector, doc['embedding']) + 1.0",
                    "params": {"query_vector": search_query}
                }
            }
        }
        results = self.es.search(index=collection_name, body={"size": top_k, "query": query})

        retrieved_documents = []
        for hit in results["hits"]["hits"]:
            retrieved_documents.append({
                "id": hit["_id"],
                "score": hit["_score"],
                "text": hit["_source"]["text"],
                "embedding": hit["_source"]["embedding"]
            })

        return retrieved_documents

    def delete_data(self, collection_name: str, document_ids: List[str]):
        """
        Delete documents from the index by their IDs.

        Args:
            collection_name (str): The name of the index to delete data from.
            document_ids (List[str]): The list of document IDs to delete.
        """
        if document_ids:
            query = {"ids": {"values": document_ids}}
            self.es.delete_by_query(index=collection_name, body=query)