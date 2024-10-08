import os
import pytest
import psycopg2

def test_postgresql_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('COLLECTIONDB_NAME'),
            user=os.getenv('COLLECTIONDB_USER'),
            password=os.getenv('COLLECTIONDB_PASS'),
            host=os.getenv('COLLECTIONDB_HOST', 'postgres'),
            port=os.getenv('COLLECTIONDB_PORT', '5432')
        )
        assert conn is not None, "Connection is None"
        print("Connection successful")
        conn.close()
    except Exception as e:
        pytest.fail(f"Connection failed: {e}")

if __name__ == "__main__":
    pytest.main([__file__])
