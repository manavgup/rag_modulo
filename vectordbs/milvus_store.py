from typing import List, Dict, Any, Optional
from pymilvus import (
    MilvusClient, 
    DataType, 
    FieldSchema, 
    CollectionSchema, 
    utility, 
    Collection, 
    MilvusException
)
from vector_store import VectorStore
from data_types import DocumentChunk
import os
from genai import Client
from uuid import uuid4
import json

MILVUS_COLLECTION: Optional[str] = os.environ.get("MILVUS_COLLECTION") or "c" + uuid4().hex
MILVUS_HOST = os.environ.get("MILVUS_HOST") or "localhost"
MILVUS_PORT = os.environ.get("MILVUS_PORT") or 19530
MILVUS_USER = os.environ.get("MILVUS_USER")
MILVUS_PASSWORD = os.environ.get("MILVUS_PASSWORD")
MILVUS_USE_SECURITY = False if MILVUS_PASSWORD is None else True

MILVUS_INDEX_PARAMS = os.environ.get("MILVUS_INDEX_PARAMS")
MILVUS_SEARCH_PARAMS = os.environ.get("MILVUS_SEARCH_PARAMS")
MILVUS_CONSISTENCY_LEVEL = os.environ.get("MILVUS_CONSISTENCY_LEVEL")

UPSERT_BATCH_SIZE = 100
OUTPUT_DIM = 1536

EMBEDDING_FIELD: str = "embedding"

SCHEMA = [
    ("id", FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True)),
    (EMBEDDING_FIELD, FieldSchema(name=EMBEDDING_FIELD, dtype=DataType.FLOAT_VECTOR, dim=OUTPUT_DIM)),
    ("text", FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535)),
    ("document_id", FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=65535)),
    ("source_id", FieldSchema(name="source_id", dtype=DataType.VARCHAR, max_length=65535)),
    ("source", FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=65535)),
    ("url", FieldSchema(name="url", dtype=DataType.VARCHAR, max_length=65535), ""),
    ("created_at", FieldSchema(name="created_at", dtype=DataType.INT64), -1),
    ("author", FieldSchema(name="author", dtype=DataType.VARCHAR, max_length=65535))
]

class MilvusStore(VectorStore):
    def __init__(self) -> None:
        self.client: MilvusClient = None
        self.index_params: Optional[Dict[str, Any]] = None
        self.search_params: Optional[Dict[str, Any]] = None
        try:
            self.client = MilvusClient(
                uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}",
                user=MILVUS_USER, 
                password=MILVUS_PASSWORD)
        except Exception as e:
            print(f"Failed to connect to Milvus: {e}")

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
        self.collection: Collection = None
        try:
            if utility.has_collection(collection_name=name):
                utility.drop_collection(collection_name=name)
            
            # If the collection does not exist, create a new collection
            if not utility.has_collection(name):
                schema = CollectionSchema(fields=SCHEMA)
                # use the schema to create a new collection
                self.collection = Collection(name=name, schema=schema)
                self._print_info("Create Milvus collection '{}' with schema {}"
                                    .format(name, schema))
                self._create_index()
            else:
                self.collection = Collection(name=name)
                self._print_info("Collection '{}' already exists".format(name))
                self.collection.load()
        except Exception as e:
            self._print_err("Failed to create collection {},  error: {}".format(name, e))
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
                    self._print_info("Create index for collection '{}' with params {}"
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
                        self._print_info("Attempting creation of Milvus '{}' index".format(i_p["index_type"]))
                        self.collection.create_index(field_name=EMBEDDING_FIELD, index_params=i_p)
                        self.index_params = i_p
                        self._print_info("Creation of Milvus '{}' index successful".format(i_p["index_type"]))
                    except MilvusException:
                        self._print_info("Attempting creation of Milvus default index")
                        i_p = {"metric_type": "IP", "index_type": "AUTOINDEX", "params": {}}
                        self.collection.create_index(field_name=EMBEDDING_FIELD, index_params=i_p)
                        self.index_params=i_p
                        self._print_info("Created Milvus default index")
            else:
                self._print_info("Index already exists for collection '{}'".format(self.collection.name))
                for index in self.collection.indexes:
                    idx = index.to_dict()
                    if idx["field"] == EMBEDDING_FIELD:
                        self._print_info("Index already exists: {}".format(idx))
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
                    self._print_info("Milvus search parameters: {}".format(self.search_params))
        except Exception as e:
            self._print_err("Failed to create index for collection '{}', error: {}".format(self.collection.name, e))
    
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
            self._print_err(f"Failed to upsert data: {e}")
        return document_ids
         
    def delete_collection(self, name: str) -> None:
        """
        Delete an existing Milvus collection.

        Args:
            name (str): The name of the collection to delete.
        """
        if not self.client.has_collection(collection_name=name):
            raise ValueError(f"Collection {name} does not exist.")
        
        self.client.drop_collection(name)

    def add_documents(self, collection_name: str, documents: List[dict]):
        """
        Add a list of documents to the collection.

        Args:
            collection_name (str): The name of the collection to add documents to.
            documents (List[dict]): The list of documents to add.
                Each document should be a dictionary with 'text' and 'embedding' keys.
        """
        try:
            self.collection.insert(documents)
        except Exception as e:
            self._print_err(f"Failed to add documents to collection {collection_name}: {e}")

    def retrieve_documents(self, collection_name: str, search_query: List[float], top_k: int = 10):
        """
        Retrieve documents from the collection.

        Args:
            collection_name (str): The name of the collection to retrieve documents from.
            search_query (List[float]): The search query (vector) to filter documents.
            top_k (int): The maximum number of results to return (default: 10).

        Returns:
            List[dict]: The list of retrieved documents.
        """
        collection = Collection(name=collection_name, client=self.client)
        search_results = collection.search(search_query, anns_field="embedding", params={"topk": top_k})

        retrieved_documents = []
        for hit in search_results:
            retrieved_documents.append({
                'id': hit.id,
                'score': hit.score,
                'embedding': hit.entity.get('embedding')
            })

        return retrieved_documents

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
    
    def _get_values(self, chunk: DocumentChunk) -> List[any] | None:  # type: ignore
        """Convert the chunk into a list of values to insert whose indexes align with fields.

        Args:
            chunk (DocumentChunk): The chunk to convert.

        Returns:
            List (any): The values to insert.
        """
        #convert DocumentChunk to dict
        chunk_dict = chunk.dict()
        