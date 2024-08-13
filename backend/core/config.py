# config.py
import tempfile
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # BAM credentials
    genai_key: Optional[str] = "None"
    api_endpoint: Optional[str] = None
    genai_api: Optional[str] = None

    # Data Directory
    data_dir: Optional[str] = None

    # VectorDB settings
    vector_db: str = "None"

    # Default collection name
    collection_name: Optional[str] = None

    # Chunking strategy and parameters
    chunking_strategy: Optional[str] = None
    min_chunk_size: Optional[int] = None
    max_chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    semantic_threshold: Optional[float] = None

    # Embedding settings
    embedding_model: Optional[str] = None
    embedding_dim: Optional[int] = None
    embedding_field: Optional[str] = None
    upsert_batch_size: Optional[int] = None

    # Frontend settings
    react_app_api_url: str

    # Logging Level
    log_level: Optional[str] = None

    # File storage path
    file_storage_path: str = tempfile.gettempdir()

    # ChromaDB credentials
    chromadb_host: Optional[str] = None
    chromadb_port: Optional[int] = None

    # Milvus credentials
    milvus_host: Optional[str] = None
    milvus_port: Optional[str] = None
    milvus_user: Optional[str] = None
    milvus_password: Optional[str] = None
    milvus_index_params: Optional[str] = None
    milvus_search_params: Optional[str] = None

    # Elasticsearch credentials
    elastic_host: Optional[str] = None
    elastic_port: Optional[int] = None
    elastic_password: Optional[str] = None
    elastic_cacert_path: Optional[str] = None
    elastic_cloud_id: Optional[str] = None
    elastic_api_key: Optional[str] = None

    # Pinecone credentials
    pinecone_api_key: Optional[str] = None
    pinecone_cloud: Optional[str] = None
    pinecone_region: Optional[str] = None

    # Weaviate credentials
    weaviate_host: Optional[str] = None
    weaviate_port: Optional[int] = None
    weaviate_grpc_port: Optional[int] = None
    weaviate_username: Optional[str] = None
    weaviate_password: Optional[str] = None
    weaviate_index: Optional[str] = None
    weaviate_scopes: Optional[str] = None

    # Tokenization settings
    tokenizer: Optional[str] = None
    tokenizer_model: Optional[str] = None

    # Project settings
    project_name: Optional[str] = None
    python_version: Optional[str] = None

    # Collection database settings
    collectiondb_user: Optional[str] = None
    collectiondb_pass: Optional[str] = None
    collectiondb_host: Optional[str] = None
    collectiondb_port: Optional[str] = None
    collectiondb_name: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings(
    react_app_api_url="http://localhost:3000",
)
