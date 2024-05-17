from typing import List, Optional, Union, Dict, Any
from pymilvus import (
    connections,
    utility,
    FieldSchema, CollectionSchema, DataType,
    Collection, IndexType, MilvusClient, MilvusException
)
from data_types import (
    Document, DocumentChunk, DocumentMetadataFilter, QueryWithEmbedding,
    QueryResult, VectorStore, DocumentChunkWithScore, Source, DocumentChunkMetadata
)
from genai import Client
import logging
import json
import re
import os

MILVUS_COLLECTION: Optional[str] = os.environ.get("MILVUS_COLLECTION","DocumentChunk")
MILVUS_HOST = os.environ.get("MILVUS_HOST") or "localhost"
MILVUS_PORT = os.environ.get("MILVUS_PORT") or "19530"
MILVUS_USER = os.environ.get("MILVUS_USER")
MILVUS_PASSWORD = os.environ.get("MILVUS_PASSWORD")
MILVUS_USE_SECURITY = False if MILVUS_PASSWORD is None else True

MILVUS_COLLECTION_NAME = "DocumentChunk"
EMBEDDING_DIM = 4
UPSERT_BATCH_SIZE = 100

EMBEDDING_FIELD: str = "embedding"
EMBEDDING_MODEL = os.environ.get("TOKENIZER_MODEL") or "sentence-transformers/all-minilm-l6-v2"

MILVUS_INDEX_PARAMS = os.environ.get("MILVUS_INDEX_PARAMS")
MILVUS_SEARCH_PARAMS = os.environ.get("MILVUS_SEARCH_PARAMS")
MILVUS_CONSISTENCY_LEVEL = os.environ.get("MILVUS_CONSISTENCY_LEVEL")

SCHEMA = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name=EMBEDDING_FIELD, dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="source_id", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="url", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="author", dtype=DataType.VARCHAR, max_length=65535)
]

class MilvusStore(VectorStore):
    def __init__(self, host: str = MILVUS_HOST, port: str = MILVUS_PORT) -> None:
        self.collection_name = MILVUS_COLLECTION_NAME
        self.host = host
        self.port = port
        self.client: MilvusClient = None
        self._connect()
        self.collection: Collection = None

    def _connect(self) -> None:
        connections.connect(default={"host": self.host, "port": self.port})

    def create_collection(self, name: str, 
                          embedding_model_id: str, client: Client, 
                          create_new: bool = False) -> Collection:
        """
        Create a new Milvus collection.

        Args:
            name (str): The name of the collection to create.
            dim (int): The dimension of the vectors.
            index_file_size (int): The index file size (default: 1024).
            metric_type (str): The metric type (default: "L2").
        """
        try:
            if utility.has_collection(collection_name=name):
                utility.drop_collection(collection_name=name)
            
            # If the collection does not exist, create a new collection else load it
            if not utility.has_collection(name):
                schema = CollectionSchema(fields=SCHEMA)
                # use the schema to create a new collection
                self.collection = Collection(name=name, schema=schema)
                logging.info("Create Milvus collection '{}' with schema {}"
                                    .format(name, schema))
                print("Create Milvus collection '{}' with schema {}"
                                    .format(name, schema))
                self._create_index()
                self.collection.load()  # Load the collection
            else:
                self.collection = Collection(name=name)
                logging.info("Collection '{}' already exists".format(name))
                self.collection.load()
        except Exception as e:
            logging.error("Failed to create collection {},  error: {}".format(name, e))
        return self.collection
    
    def _create_index(self) -> None:
        """
        Create an index for the Milvus collection.
        """
        # TODO: verify index/search params passed by os.environ
        self.index_params = json.loads(MILVUS_INDEX_PARAMS) if MILVUS_INDEX_PARAMS else None
        self.search_params = json.loads(MILVUS_SEARCH_PARAMS) if MILVUS_SEARCH_PARAMS else None
        try:
            if len(self.collection.indexes) == 0:
                if self.index_params is not None:
                    # Convert the string format to JSON format parameters passed by MILVUS_INDEX_PARAMS
                    logging.debug("Create index for collection '{}' with params {}"
                                    .format(self.collection.name, self.index_params))
                    # Create an index on the 'embedding' field with the index params found in init
                    self.collection.create_index(field_name=EMBEDDING_FIELD, index_params=self.index_params)
                else:
                    # no index parameters supplied, create new index
                    try:
                        i_p = {
                            "metric_type": "IP",
                            "index_type": "HNSW",
                            "params": {"M": 8, "efConstruction": 64},
                        }
                        logging.info("Attempting creation of Milvus '{}' index".format(i_p["index_type"]))
                        self.collection.create_index(field_name=EMBEDDING_FIELD, index_params=i_p)
                        self.index_params = i_p
                        logging.info("Creation of Milvus '{}' index successful".format(i_p["index_type"]))
                    except MilvusException:
                        logging.info("Attempting creation of Milvus default index")
                        i_p = {"metric_type": "IP", "index_type": "AUTOINDEX", "params": {}}
                        self.collection.create_index(field_name=EMBEDDING_FIELD, index_params=i_p)
                        self.index_params=i_p
                        logging.debug("Created Milvus default index")
            else:
                logging.debug("Index already exists for collection '{}'".format(self.collection.name))
                for index in self.collection.indexes:
                    idx = index.to_dict()
                    if idx["field"] == EMBEDDING_FIELD:
                        logging.debug("Index already exists: {}".format(idx))
                        self.index_params=idx["index_param"]
                        break
                
                #self.collection.load()
                
                if self.search_params is not None:
                    # Convert the string format to JSON format parameters passed by MILVUS_SEARCH_PARAMS
                    self.search_params=json.loads(MILVUS_SEARCH_PARAMS) if MILVUS_SEARCH_PARAMS else None
                else:
                    # The default search params
                    metric_type = "IP"
                    if self.index_params is not None and "metric_type" in self.index_params:
                        metric_type = self.index_params["metric_type"]
                    default_search_params = {
                        "IVF_FLAT": {"metric_type": metric_type, "params": {"nprobe": 10}},
                        "IVF_SQ8": {"metric_type": metric_type, "params": {"nprobe": 10}},
                        "IVF_PQ": {"metric_type": metric_type, "params": {"nprobe": 10}},
                        "HNSW": {"metric_type": metric_type, "params": {"ef": 10}},
                        "RHNSW_FLAT": {"metric_type": metric_type, "params": {"ef": 10}},
                        "RHNSW_SQ": {"metric_type": metric_type, "params": {"ef": 10}},
                        "RHNSW_PQ": {"metric_type": metric_type, "params": {"ef": 10}},
                        "IVF_HNSW": {"metric_type": metric_type, "params": {"nprobe": 10, "ef": 10}},
                        "ANNOY": {"metric_type": metric_type, "params": {"search_k": 10}},
                        "AUTOINDEX": {"metric_type": metric_type, "params": {}},
                        }
                    # Set the search params
                    if self.index_params is not None and "index_type" in self.index_params:
                        self.search_params=default_search_params[self.index_params["index_type"]]
                    else:
                        self.search_params=default_search_params["AUTOINDEX"]
                    logging.info("Milvus search parameters: {}".format(self.search_params))
        except Exception as e:
            logging.debug("Failed to create index for collection '{}', error: {}".format(self.collection.name, e))

    def add_documents(self, collection_name: str, documents: List[Document]) -> List[str]:
        """
        Add a list of documents to the collection.

        Args:
            collection_name (str): The name of the collection to add documents to.
            documents (List[dict]): The list of documents to add.
                Each document should be a dictionary with 'text' and 'embedding' keys.
        """
        try:
            data = []
            for document in documents:
                for chunk in document.chunks:
                    chunk.document_id = document.document_id  # Ensure each chunk references its parent document
                    
                    data.append({
                        "document_id": chunk.document_id,
                        "embedding": chunk.vectors,
                        "text": chunk.text,
                        "chunk_id": chunk.chunk_id,
                        "source_id": chunk.metadata.source_id if chunk.metadata else "",
                        "source": chunk.metadata.source.value if chunk.metadata else "",
                        "url": chunk.metadata.url if chunk.metadata else "",
                        "created_at": chunk.metadata.created_at if chunk.metadata else "",
                        "author": chunk.metadata.author if chunk.metadata else ""
                    })
            
            logging.debug(f"Inserting data: {data}")
            self.collection.insert(data)
            logging.info(f"Successfully added documents to collection {collection_name}")
        except Exception as e:
            logging.error(f"Failed to add documents to collection {collection_name}: {e}", exc_info=True)
        return [doc.document_id for doc in documents]
    
    def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """Upsert chunks into the datastore.

        Args:
            chunks (Dict[str, List[DocumentChunk]]): A list of DocumentChunks to insert

        Raises:
            e: Error in upserting data.

        Returns:
            List[str]: The document_id's that were inserted.
        """
        try:
            # documents IDS to return
            document_ids: List[str] = []
            offset = 1 # offset for the primary key
            insert: List[List] = [[] for _ in range(len(self._get_schema()) - offset)]
            
            # Go through each document chunklist and grab the data
            for document_id, chunk_list in chunks.items():
                #Append document_id to the insert list
                document_ids.append(document_id)
                for chunk in chunk_list:
                    # Create a new list of data to insert
                    data = [chunk.get(field, None) for field, _, _ in self._get_schema()]
                    # Add the data to the insert list
                    for i, d in enumerate(data):
                        insert[i].append(d)
                    document_ids.append(document_id)
        except Exception as e:
            logging.debug(f"Failed to upsert data: {e}")
        return document_ids
    
    def _insert_chunk(self, chunk: DocumentChunk) -> None:
        data = [
            None,  # 'id' will be auto-generated
            chunk.document_id,
            chunk.vectors,
            chunk.text,
            chunk.chunk_id,
            chunk.metadata.source_id if chunk.metadata else "",
            chunk.metadata.source.value if chunk.metadata else "",
            chunk.metadata.url if chunk.metadata else "",
            chunk.metadata.created_at if chunk.metadata else "",
            chunk.metadata.author if chunk.metadata else ""
        ]
        print("\ndata=", data)
        self.collection.insert([data])
    
    def retrieve_documents(self, query: Union[str, QueryWithEmbedding], 
                          collection_name: Optional[str] = None, limit: int = 10) -> QueryResult:
        """
        Retrieve documents from the collection.

        Args:
            collection_name (str): The name of the collection to retrieve documents from.
            search_query (List[float]): The search query (vector) to filter documents.
            top_k (int): The maximum number of results to return (default: 10).

        Returns:
            List[dict]: The list of retrieved documents.
        """
        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        search_results = self.collection.search(
                            data=[query.vectors], 
                            anns_field="embedding", 
                            param=search_params,
                            output_fields=["chunk_id", "text", "document_id", "embedding", "source", "source_id", "url", "created_at", "author"], 
                            limit=limit)

        #search_results = collection.search(search_query, anns_field="embedding", params={"topk": top_k})
        return self._process_search_results(search_results)
    
    def delete_data(self, collection_name: str, document_ids: List[int]):
        """
        Delete documents from the collection by their IDs.

        Args:
            collection_name (str): The name of the collection to delete data from.
            document_ids (List[int]): The list of document IDs to delete.
        """
        collection = Collection(name=collection_name, client=self.client)
        collection.delete([document_ids])
        
    def _get_schema(self):
        return SCHEMA
        

    def query(self, query: QueryWithEmbedding, collection_name: Optional[str] = None, number_of_results: int = 10, filter: Optional[DocumentMetadataFilter] = None) -> QueryResult:
        search_params = {"metric_type": MetricType.L2, "params": {"nprobe": 10}}
        result = self.collection.search(data=[query.vectors], anns_field="embeddings", param=search_params, limit=number_of_results)
        return self._process_search_results(result)

    def delete_collection(self, name: str) -> None:
        """
        Delete an existing Milvus collection.

        Args:
            name (str): The name of the collection to delete.
        """
        if not utility.has_collection(collection_name=name):
            logging.debug(f"Collection {name} does not exist.")
        
        utility.drop_collection(name)
    
    def delete_documents(self, document_ids: List[str], collection_name: Optional[str] = None) -> None:
        expr = f"chunk_id in {tuple(document_ids)}"
        self.collection.delete(expr)
    
    def get_document(self, document_id: str, collection_name: Optional[str] = None) -> Optional[Document]:
        expr = f"document_id == '{document_id}'"
        results = self.collection.query(expr=expr, output_fields=["*"])
        if results:
            chunks = [self._convert_to_chunk(result) for result in results]
            return Document(document_id=document_id, name=document_id, chunks=chunks)
            #return self._convert_to_document(results[0])
        return None
    
    def _convert_to_chunk(self, data: Dict[str, Any]) -> DocumentChunk:
        return DocumentChunk(
            chunk_id=str(data["chunk_id"]),
            text=data["text"],
            vectors=data["embedding"],
            metadata=DocumentChunkMetadata(
                source=Source(data["source"]),
                source_id=data.get("source_id"),
                url=data.get("url"),
                created_at=data.get("created_at"),
                author=data.get("author")
            ),
            document_id=data["document_id"]
        )
        
    def _convert_to_document(self, data: Dict[str, Any]) -> Document:
        chunk = DocumentChunk(
            chunk_id=str(data["chunk_id"]),
            text=data["text"],
            vectors=data["embeddings"],
            metadata=DocumentChunkMetadata(
                source=Source(data["source"]),
                source_id=data.get("source_id"),
                url=data.get("url"),
                created_at=data.get("created_at"),
                author=data.get("author")
            )
        )
        return Document(document_id=data["chunk_id"], name=data["chunk_id"], chunks=[chunk])
    
    def _embed_text(self, text: str) -> List[float]:
        # Dummy embedding function, replace with actual model
        return [0.0] * EMBEDDING_DIM

    def _process_search_results(self, results: Any) -> QueryResult:
        chunks_with_scores = []
        similarities = []
        ids = []
        for result in results:
            for hit in result:
                chunks_with_scores.append(
                    DocumentChunkWithScore(
                        chunk_id=hit.entity.get("chunk_id"),
                        text=hit.entity.get("text"),
                        vectors=hit.entity.get("embedding"),
                        metadata=DocumentChunkMetadata(
                            source=Source(hit.entity.get("source")),
                            source_id=hit.entity.get("source_id"),
                            url=hit.entity.get("url"),
                            created_at=hit.entity.get("created_at"),
                            author=hit.entity.get("author")
                        ),
                        score=hit.distance
                    )
                )
                ids.append(hit.entity.get("chunk_id"))
            similarities.append(result.distances)

        return QueryResult(data=chunks_with_scores, similarities=similarities, ids=ids)

    async def __aenter__(self) -> "MilvusStore":
        return self

    async def __aexit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        if self.client:
            self.client.close()

if __name__ == "__main__":
    store = MilvusStore()
    print(store)
    store.delete_collection(MILVUS_COLLECTION_NAME)
    store.create_collection(MILVUS_COLLECTION_NAME, EMBEDDING_MODEL, store.client)
    print("Collection created", store.collection_name)
    document_chunks = [
        DocumentChunk(chunk_id="1", text="Hello world", vectors=[0.1, 0.2, 0.3, 0.4],
                      metadata=DocumentChunkMetadata(source=Source.WEBSITE)),
        DocumentChunk(chunk_id="2", text="This is different", vectors=[0.4, 0.4, 0.6, 0.7],
                      metadata=DocumentChunkMetadata(source=Source.WEBSITE)),
        DocumentChunk(chunk_id="3", text="A THIRD STATEMENT", vectors=[0.6, 0.7, 0.6, 0.7],
                      metadata=DocumentChunkMetadata(source=Source.WEBSITE))
    ]
    store.add_documents(MILVUS_COLLECTION_NAME, [Document(document_id="doc1", name="Doc 1", chunks=document_chunks)])
    results = store.retrieve_documents(collection_name=MILVUS_COLLECTION_NAME, 
                                       query=QueryWithEmbedding(text="world", vectors=[0.1, 0.2, 0.3, 0.4]), limit=2)
    print("Retrieved Documents:", results)
    store.delete_collection(MILVUS_COLLECTION_NAME)
