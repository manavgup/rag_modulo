import logging
import os
from typing import Any, Dict, List, Optional 

from dotenv import load_dotenv
from elasticsearch import AsyncElasticsearch, NotFoundError

from vectordbs.data_types import (Document, DocumentChunk,
                                  DocumentChunkMetadata,
                                  DocumentMetadataFilter, QueryResult,
                                  QueryWithEmbedding, Source)
from vectordbs.utils.watsonx import get_embeddings
from vectordbs.vector_store import VectorStore
from vectordbs.error_types import CollectionError, DocumentError

load_dotenv()

ELASTICSEARCH_HOST = os.environ.get("ELASTICSEARCH_HOST", "localhost")
ELASTICSEARCH_PORT = os.environ.get("ELASTICSEARCH_PORT", "9200")
ELASTICSEARCH_INDEX = os.environ.get("ELASTICSEARCH_INDEX", "document_chunks")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL",
                                 "sentence-transformers/all-minilm-l6-v2")

ELASTIC_PASSWORD = os.environ.get("ELASTIC_PASSWORD", "changeme")
ELASTIC_CACERT_PATH = os.environ.get("ELASTIC_CACERT_PATH", 
                                     "/path/to/http_ca.crt")
ELASTIC_CLOUD_ID = os.environ.get("ELASTIC_CLOUD_ID", "")
ELASTIC_API_KEY = os.environ.get("ELASTIC_API_KEY", "")

EMBEDDING_DIM = 384
UPSERT_BATCH_SIZE = 100


class ElasticSearchStore(VectorStore):
    def __init__(
        self, host: str = ELASTICSEARCH_HOST, port: str = ELASTICSEARCH_PORT
    ) -> None:
        self.index_name = ELASTICSEARCH_INDEX
        if ELASTIC_CLOUD_ID:
            self.client = AsyncElasticsearch(ELASTIC_CLOUD_ID, api_key=ELASTIC_API_KEY)
        else:
            self.client = AsyncElasticsearch(
                hosts=[{"host": host, "port": port}],
                ca_certs=ELASTIC_CACERT_PATH,
                basic_auth=("elastic", ELASTIC_PASSWORD)
            )

    async def create_collection_async(self, collection_name: str, metadata: Optional[dict] = None) -> None:
        """
        Create a new Elasticsearch index.

        Args:
            name (str): The name of the index to create.
            embedding_model_id (str): The ID of the embedding model.
            client (Optional[Elasticsearch]): The Elasticsearch client
            instance.
        """
        if await self.client.indices.exists(index=collection_name):
            logging.info(f"Elasticsearch index '{collection_name}' already exists.")
            raise CollectionError(f"Elasticsearch index '{collection_name}' already exists.")
        else:
            mappings = {
                "mappings": {
                    "properties": {
                        "document_id": {"type": "keyword"},
                        "embedding": {
                            "type": "dense_vector",
                            "index": "true",
                            "dims": 384,
                            "similarity": "l2_norm",
                        },
                        "text": {"type": "text"},
                        "chunk_id": {"type": "text"},
                        "source_id": {"type": "text"},
                        "source": {"type": "text"},
                        "url": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "author": {"type": "text"},
                    }
                }
            }
            try:
                response = await self.client.indices.create(index=collection_name, body=mappings)
                if response.get("acknowledged"):
                    logging.info(f"Created index '{collection_name}' with {mappings}.")
                else:
                    logging.error(f"Failed to create index '{collection_name}': {response}")
            except Exception as e:
                logging.error(f"Failed to create index '{collection_name}':{e}")
                raise CollectionError(f"Failed to create index '{collection_name}': {e}")

    async def add_documents_async(
        self, collection_name: str, documents: List[Document]
    ) -> List[str]:
        """Add a list of documents to the Elasticsearch index."""
        if not documents:
            logging.warning(f"No documents to add to '{collection_name}'")
            return []

        if not await self.client.indices.exists(index=collection_name):
            logging.error(f"Index '{collection_name}' does not exist")
            raise DocumentError(f"Elasticsearch index '{collection_name}' does not exist")

        document_ids = []
        try:
            actions = []
            for document in documents:
                for chunk in document.chunks:
                    chunk_data = {
                        "document_id": document.document_id,
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "embedding": chunk.vectors,
                        "source_id": chunk.metadata.source_id if chunk.metadata else "",
                        "source": chunk.metadata.source.value if chunk.metadata else "",
                        "url": chunk.metadata.url if chunk.metadata else "",
                        "created_at": (
                            chunk.metadata.created_at if chunk.metadata else ""
                        ),
                        "author": chunk.metadata.author if chunk.metadata else "",
                    }
                    actions.append({"index": {"_id": chunk.chunk_id}})
                    actions.append(chunk_data)
                    document_ids.append(
                        chunk.chunk_id
                    )  # Store the UUIDs of the documents
            await self.client.bulk(index=collection_name, body=actions, refresh=True)
            print("collection: ", collection_name)
            logging.info(f"Successfully added documents to index '{collection_name}'")
        except Exception as e:
            logging.error(
                f"Failed to add documents to index '{collection_name}': {e}",
                exc_info=True,
            )
            raise DocumentError(f"Failed to add documents to index '{collection_name}': {e}")
        return document_ids

    async def retrieve_documents_async(self, query: str, collection_name: Optional[str] = None,
                                 limit: int = 10) -> List[QueryResult]:
        """Retrieve documents from the Elasticsearch index."""
        embeddings = get_embeddings(query)
        if not embeddings:
            raise DocumentError("Failed to generate embeddings for the query string.")
        query_embedding = QueryWithEmbedding(query, embeddings)
        collection_name = (collection_name or self.index_name)  # Use the default index name if not provided
        return await self.query_async(collection_name, query_embedding, number_of_results=limit)

    async def delete_collection_async(self, name: str) -> None:
        """Delete an Elasticsearch index."""
        try:
            await self.client.indices.delete(index=name)
            logging.info(f"Deleted Elasticsearch index '{name}'")
        except NotFoundError:
            logging.warning(f"Elasticsearch index '{name}' does not exist")
        except Exception as e:
            logging.error(f"Failed to delete Elasticsearch index '{name}': {e}", exc_info=True)
            raise CollectionError(f"Failed to delete Elasticsearch index '{name}': {e}")

    async def delete_documents_async(
        self, document_ids: List[str], collection_name: Optional[str] = None
    ) -> int:
        """Delete documents from the Elasticsearch index by their chunk IDs."""
        collection_name = (collection_name or self.index_name)  # Use the default index name if not provided
        if not document_ids:
            logging.info(f"No document IDs provided for deletion in index '{collection_name}'")
            return 0

        try:
            actions = [
                {"delete": {"_index": collection_name, "_id": doc_id}}
                for doc_id in document_ids
            ]
            response = self.client.bulk(body=actions, refresh=True)

            # Handle partial failures
            deleted_count = 0
            for item in response["items"]:
                delete_result = item.get("delete", {})
                if delete_result.get("result") == "deleted":
                    deleted_count += 1
                elif delete_result.get("status") == 404:
                    logging.warning(
                        f"Document with ID '{delete_result.get('_id')}' not found in index '{collection_name}'"
                    )
                else:
                    logging.error(
                        f"Failed to delete document '{delete_result.get('_id')}': {delete_result.get('error', {})}"
                    )

            return deleted_count
        except Exception as e:
            logging.error(
                f"Failed to delete documents from index '{collection_name}': {e}",
                exc_info=True,
            )
            raise DocumentError(f"Failed to delete documents from index '{collection_name}': {e}")

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
                author=data.get("author"),
            ),
            document_id=data["document_id"],
        )

    def _process_search_results(self, response):
        """Helper function to process search results."""
        hits = response["hits"]["hits"]
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
                    author=source.get("author", ""),
                ),
                document_id=source["document_id"],
            )
            results.append(
                QueryResult(
                    data=[chunk],
                    similarities=[[hit["_score"]]],
                    ids=[source["chunk_id"]],
                )
            )
        return results

    async def query_async(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        filter: Optional[DocumentMetadataFilter] = None,
    ) -> List[QueryResult]:
        """Queries the Elasticsearch index with filtering and query mode options."""
        try:
            response = await self.client.search(
                index=collection_name,
                knn={
                    "field": "embedding",
                    "query_vector": query.vectors,
                    "k": number_of_results,
                    "num_candidates": 100,
                },
                fields=[
                    "text",
                    "source",
                    "url",
                    "created_at",
                    "author",
                    "document_id",
                    "chunk_id",
                ],
            )
            return self._process_search_results(response)
        except Exception as e:
            logging.error(f"Failed to query documents from index '{collection_name}': {e}", exc_info=True)
            raise DocumentError(f"Failed to query documents from index '{collection_name}': {e}")

    def _build_filters(
        self, filter: Optional[DocumentMetadataFilter]
    ) -> Dict[str, Any]:
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

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        await self.client.close()
