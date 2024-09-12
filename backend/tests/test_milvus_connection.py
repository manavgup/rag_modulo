from pymilvus import connections, utility

def test_milvus_connection():
    try:
        connections.connect(
            alias="default", 
            host="localhost", 
            port="19530"
        )
        print("Successfully connected to Milvus")
        
        # Check if Milvus is healthy
        if utility.get_server_version():
            print(f"Milvus version: {utility.get_server_version()}")
        else:
            print("Failed to get Milvus version")
        
        # List collections
        collections = utility.list_collections()
        print(f"Existing collections: {collections}")
        
    except Exception as e:
        print(f"Failed to connect to Milvus: {e}")
    finally:
        connections.disconnect("default")

if __name__ == "__main__":
    test_milvus_connection()
