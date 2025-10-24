#!/usr/bin/env python3
"""List all collections in Milvus"""

from pymilvus import connections, utility

from core.config import get_settings

settings = get_settings()

# Connect to Milvus
connections.connect(alias="default", host=settings.milvus_host, port=settings.milvus_port)

collections = utility.list_collections()
print("\n📚 Collections in Milvus:")
for col in collections:
    print(f"  - {col}")

connections.disconnect("default")
