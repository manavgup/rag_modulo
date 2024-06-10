import logging
import os
from chromadb import ClientAPI, chromadb
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-minilm-l6-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

print("CHROMADB_HOST: ", CHROMADB_HOST)
print("CHROMADB_PORT: ", CHROMADB_PORT)

logging.basicConfig(level=logging.INFO)

client: ClientAPI = chromadb.HttpClient(
    host=CHROMADB_HOST, port=CHROMADB_PORT
)

print("client: ", client)

# Example method to verify the connection
def verify_connection():
    try:
        tenant_info = client._admin_client.get_tenant(name="default_tenant")
        print("Tenant Info: ", tenant_info)
    except Exception as e:
        logging.error(f"Failed to connect to ChromaDB: {e}")

verify_connection()
