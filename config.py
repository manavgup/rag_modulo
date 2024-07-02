# rag_solution/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # BAM credentials
    genai_key: str
    api_endpoint: str
    genai_api: str

    # Data Directory
    data_dir: str

    # VectorDB settings
    vector_db: str

    # Default collection name
    collection_name: str

    # Chunking strategy and parameters
    chunking_strategy: str
    min_chunk_size: int
    max_chunk_size: int
    chunk_overlap: int
    semantic_threshold: float

    # Embedding settings
    embedding_model: str
    embedding_dim: int
    upsert_batch_size: int
    embedding_field: str = "embedding"

    # Logging Level
    log_level: str

    # ChromaDB credentials
    chromadb_host: str
    chromadb_port: int

    # Milvus credentials
    milvus_host: str
    milvus_port: str
    milvus_user: str
    milvus_password: str
    milvus_index_params: str
    milvus_search_params: str

    # Elasticsearch credentials
    elastic_host: str
    elastic_port: int
    elastic_password: str
    elastic_cacert_path: str
    elastic_cloud_id: str
    elastic_api_key: str

    # Pinecone credentials
    pinecone_api_key: str
    pinecone_cloud: str
    pinecone_region: str

    # Weaviate credentials
    weaviate_host: str
    weaviate_port: int
    weaviate_grpc_port: int
    weaviate_username: str
    weaviate_password: str
    weaviate_index: str
    weaviate_scopes: str

    # Tokenization settings
    tokenizer: str
    model: str

    class Config:
        env_file = ".env"

settings = Settings()
