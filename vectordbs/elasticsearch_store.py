from typing import List, Optional, Union, Dict, Any
from elasticsearch import Elasticsearch, NotFoundError
from vectordbs.data_types import (
    Document, DocumentChunk, DocumentMetadataFilter, QueryWithEmbedding, 
    QueryResult, Source, DocumentChunkMetadata
)
from vectordbs.vector_store import VectorStore  
import logging
import os
from vectordbs.utils.watsonx import get_embeddings
import uuid

ELASTICSEARCH_HOST = os.environ.get("ELASTICSEARCH_HOST", "localhost")
ELASTICSEARCH_PORT = os.environ.get("ELASTICSEARCH_PORT", "9200")
ELASTICSEARCH_INDEX = os.environ.get("ELASTICSEARCH_INDEX", "document_chunks")
EMBEDDING_MODEL="sentence-transformers/all-minilm-l6-v2"

ELASTIC_PASSWORD = "PKK+lq3MUjqrr1ZYscfw"
ELASTIC_CACERT_PATH = "/Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/http_ca.crt"
ELASTIC_CLOUD_ID = "c8ec8bb47d0546b29198093091119041:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvJGM0YTkyMzQxZGVjNDRlNGJiODUyNDRiNDA4NjVhYjBhJDEyZGFjMmM5ZTQ1ODQ4ODQ4YjM2ZDJlNjkzYjBlNGYy"
ELASTIC_API_KEY = "ckpIaHZJOEIzYTN3TVByUm9oYUU6Mi1OX2JBenpTcm1TMXRXZnlyU3gzZw=="

EMBEDDING_DIM = 384
UPSERT_BATCH_SIZE = 100

class ElasticSearchStore(VectorStore):
    def __init__(self, host: str = ELASTICSEARCH_HOST, port: str = ELASTICSEARCH_PORT) -> None:
        self.index_name = ELASTICSEARCH_INDEX
        self.host = host
        self.port = port
        if ELASTIC_CLOUD_ID:
            self.client = Elasticsearch(
                cloud_id=ELASTIC_CLOUD_ID,
                api_key=ELASTIC_API_KEY
            )
        else:
            self.client = Elasticsearch(
                "https://{host}:{port}".format(host=host, port=port),
                ca_certs=ELASTIC_CACERT_PATH,
                basic_auth=("elastic", ELASTIC_PASSWORD)
            )
        print ("**** ElasticSearchStore: ", self.client.info())
        #self._create_index(self.index_name, EMBEDDING_MODEL)

    def create_collection(self, name: str, embedding_model_id: str, client: Optional[Elasticsearch] = None) -> None:
        """
        Create a new Elasticsearch index.

        Args:
            name (str): The name of the index to create.
            embedding_model_id (str): The ID of the embedding model.
            client (Optional[Elasticsearch]): The Elasticsearch client instance.
        """
        if self.client.indices.exists(index=name):
            logging.info(f"Elasticsearch index '{name}' already exists.")
        else:
            mappings = {
                "mappings": {
                    "properties": {
                        "document_id": {
                            "type": "keyword"
                        },
                        "embedding": {
                            "type": "dense_vector", 
                            "index": "true", 
                            "dims": 384, 
                            "similarity": "l2_norm"
                        },
                        "text": {
                            "type": "text"
                        },
                        "chunk_id": {
                            "type": "text"
                        },
                        "source_id": {
                            "type": "text"
                        },
                        "source": {
                            "type": "text"
                        },
                        "url": {
                            "type": "keyword"
                        },
                        "created_at": {
                            "type": "date"
                        },
                        "author": {
                            "type": "text"
                        }
                    }
                }
            }
            try:
                response = self.client.indices.create(index=name, body=mappings)
                print("****-> INDEX: ", self.client.indices.get(index=name))
                print ("FIELD MAPPING", self.client.indices.get_field_mapping(index=name, fields="embedding"))
                if response.get("acknowledged"):
                    logging.info(f"Created Elasticsearch index '{name}' with mappings {mappings}.")
                else:
                    logging.error(f"Failed to create Elasticsearch index '{name}': {response}")
            except Exception as e:
                logging.error(f"Failed to create Elasticsearch index '{name}': {e}")

       
    def add_documents(self, collection_name: str, documents: List[Document]) -> List[str]:
        """Add a list of documents to the Elasticsearch index."""
        if not documents:
            logging.warning(f"No documents to add to the index '{collection_name}'")
            return []
        
        if not self.client.indices.exists(index=collection_name):
            logging.error(f"Elasticsearch index '{collection_name}' does not exist")
            return []
        
        document_ids = []
        try:
            actions = []
            for document in documents:
                for chunk in document.chunks:
                    chunk_data = {
                            "document_id": chunk.document_id,
                            "chunk_id": chunk.chunk_id,
                            "text": chunk.text,
                            "embedding": chunk.vectors,
                            "source_id": chunk.metadata.source_id if chunk.metadata else "",
                            "source": chunk.metadata.source.value if chunk.metadata else "",
                            "url": chunk.metadata.url if chunk.metadata else "",
                            "created_at": chunk.metadata.created_at if chunk.metadata else "",
                            "author": chunk.metadata.author if chunk.metadata else ""
                    }
                    actions.append({"index": {"_id": chunk.chunk_id}})
                    actions.append(chunk_data)
                    document_ids.append(chunk.chunk_id) # Store the UUIDs of the documents
            self.client.bulk(index=collection_name, body=actions, refresh=True)
            print ("collection: ", collection_name)
            logging.info(f"Successfully added documents to index '{collection_name}'")
        except Exception as e:
            logging.error(f"Failed to add documents to index '{collection_name}': {e}", exc_info=True)
            raise
        return document_ids

    def retrieve_documents(self, query: Union[str, QueryWithEmbedding], collection_name: Optional[str] = None, limit: int = 10) -> List[QueryResult]:
        """Retrieve documents from the Elasticsearch index."""
        if isinstance(query, str):
            query_embeddings = get_embeddings(query)
            if not query_embeddings:
                raise ValueError("Failed to generate embeddings for the query string.")
            query = QueryWithEmbedding(text=query, vectors=query_embeddings)
        
        return self.query(collection_name, query, number_of_results=limit)

    def delete_collection(self, name: str) -> None:
        """Delete an Elasticsearch index."""
        try:
            self.client.indices.delete(index=name)
            logging.info(f"Deleted Elasticsearch index '{name}'")
        except NotFoundError:
            logging.warning(f"Elasticsearch index '{name}' does not exist")
        except Exception as e:
            logging.error(f"Failed to delete Elasticsearch index '{name}': {e}", exc_info=True)
            raise

    def delete_documents(self, document_ids: List[str], collection_name: Optional[str] = None) -> int:
        """Delete documents from the Elasticsearch index by their chunk IDs."""
        try:
            actions = [{"delete": {"_index": collection_name, "_id": doc_id}} for doc_id in document_ids]
            response = self.client.bulk(body=actions, refresh=True)
            return sum(1 for item in response['items'] if item.get('delete', {}).get('result') == 'deleted')
        except Exception as e:
            logging.error(f"Failed to delete documents from index '{collection_name}': {e}", exc_info=True)
            raise

    def get_document(self, document_id: str, collection_name: Optional[str] = None) -> Optional[Document]:
        """Retrieve a single document from the Elasticsearch index by its document ID."""
        try:
            response = self.client.search(
                index=self.index_name,
                body={"query": {"term": {"document_id": document_id}}}
            )
            if response['hits']['total']['value'] > 0:
                chunks = [self._convert_to_chunk(hit['_source']) for hit in response['hits']['hits']]
                return Document(document_id=document_id, name=document_id, chunks=chunks)
        except NotFoundError:
            logging.warning(f"Document '{document_id}' not found in index '{self.index_name}'")
        except Exception as e:
            logging.error(f"Failed to get document '{document_id}' from index '{self.index_name}': {e}", exc_info=True)
            raise
        return None

    def _convert_to_chunk(self, data: Dict[str, Any]) -> DocumentChunk:
        """Convert Elasticsearch document data to a DocumentChunk."""
        return DocumentChunk(
            chunk_id=data["chunk_id"],
            text=data["text"],
            vectors=data["embedding"],
            metadata=DocumentChunkMetadata(
                source=Source(data["source"]) if data["source"] else Source.OTHER,
                source_id=data.get("source_id"),
                url=data.get("url"),
                created_at=data.get("created_at"),
                author=data.get("author")
            ),
            document_id=data["document_id"]
        )

    def _process_search_results(self, response):
        """Helper function to process search results."""
        hits = response['hits']['hits']
        results = []
        for hit in hits:
            source = hit["_source"]
            chunk = DocumentChunk(
                chunk_id=source["chunk_id"],
                text=source["text"],
                vectors=source["embedding"],
                metadata=DocumentChunkMetadata(
                    source=Source(source.get("source", "OTHER")),
                    source_id=source.get("source_id", ""),
                    url=source.get("url", ""),
                    created_at=source.get("created_at", ""),
                    author=source.get("author", "")
                ),
                document_id=source["document_id"]
            )
            results.append(QueryResult(data=[chunk], similarities=[[hit["_score"]]], ids=[source["chunk_id"]]))
        return results

    def query(self, 
          collection_name: str, 
          query: QueryWithEmbedding,
          number_of_results: int = 10, 
          filter: Optional[DocumentMetadataFilter] = None) -> List[QueryResult]:
        """Queries the Elasticsearch index with filtering and query mode options."""
        print("****-> Query TEXT: %s", query.text, "query vectors length: ", len(query.vectors))
        print ("****** COLLECTION NAME: ", collection_name)
        print ("in Query. FIELD MAPPING: ", self.client.indices.get_field_mapping(index=collection_name, fields="embedding"))
        if isinstance(query, str):
            query_embeddings = get_embeddings(query)
            if not query_embeddings:
                raise ValueError("Failed to generate embeddings for the query string.")
            query = QueryWithEmbedding(text=query, vectors=query_embeddings)
        try:
            response = self.client.search(
                index=collection_name,
                knn={
                    "field": "embedding",
                    "query_vector": query.vectors,
                    "k": number_of_results,
                    "num_candidates": 100,
                },
                fields=[ "text", "source", "url", "created_at", "author", "document_id", "chunk_id" ]
            )
            return self._process_search_results(response)
        except Exception as e:
            logging.error(f"Failed to query documents from index '{collection_name}': {e}", exc_info=True)
            raise


    def _build_filters(self, filter: Optional[DocumentMetadataFilter]) -> Dict[str, Any]:
        """Build Elasticsearch filters from a DocumentMetadataFilter."""
        if not filter:
            return {}
        filters = []
        if filter.operator.lower() in ["eq", "equals", "term"]:
            field_filter = {"term": {filter.field_name: filter.value}}
            filters.append(field_filter)
        elif filter.operator.lower() == "gte":
            range_filter = {"range": {filter.field_name: {"gte": filter.value}}}
            filters.append(range_filter)
        elif filter.operator.lower() == "lte":
            range_filter = {"range": {filter.field_name: {"lte": filter.value}}}
            filters.append(range_filter)
        return {"bool": {"filter": filters}}

    async def __aenter__(self) -> "ElasticSearchStore":
        return self

    async def __aexit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        self.client.close()

if __name__ == "__main__":
    store = ElasticSearchStore()
    print(store)
    store.delete_collection(ELASTICSEARCH_INDEX)
    print("Collection created", store.index_name)
    document_chunks = [
        DocumentChunk(chunk_id="1", text="Hello world", vectors=[0.1, 0.2, 0.3, 0.4],
                      metadata=DocumentChunkMetadata(source=Source.WEBSITE)),
        DocumentChunk(chunk_id="2", text="This is different", vectors=[0.4, 0.4, 0.6, 0.7],
                      metadata=DocumentChunkMetadata(source=Source.WEBSITE)),
        DocumentChunk(chunk_id="3", text="A THIRD STATEMENT", vectors=[0.6, 0.7, 0.6, 0.7],
                      metadata=DocumentChunkMetadata(source=Source.WEBSITE))
    ]
    store.add_documents(ELASTICSEARCH_INDEX, [Document(document_id="doc1", name="Doc 1", chunks=document_chunks)])
    results = store.retrieve_documents(collection_name=ELASTICSEARCH_INDEX, 
                                       query=QueryWithEmbedding(text="world", vectors=[0.1, 0.2, 0.3, 0.4]), limit=2)
    print("Retrieved Documents:", results)
    store.delete_collection(ELASTICSEARCH_INDEX)
