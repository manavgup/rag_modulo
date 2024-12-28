#!/bin/bash

# Load environment variables
source .env

# Start dependent services based on VECTOR_DB
if [ "$VECTOR_DB" == "elastic" ]; then
    docker-compose up -d elasticsearch
elif [ "$VECTOR_DB" == "milvus" ]; then
    docker-compose up -d milvus
elif [ "$VECTOR_DB" == "chroma" ]; then
    docker-compose up -d chroma
elif [ "$VECTOR_DB" == "weaviate" ]; then
    docker-compose up -d weaviate
elif [ "$VECTOR_DB" == "pinecone" ]; then
    echo "Pinecone does not require a local Docker container."
else
    echo "Unknown VECTOR_DB value: $VECTOR_DB"
    exit 1
fi

# Wait for services to be ready
sleep 30

# Build and run the main application and tests
docker-compose build
docker-compose up -d backend frontend
docker-compose exec backend poetry run pytest --cov=rag_solution tests/

# Cleanup
docker-compose down
