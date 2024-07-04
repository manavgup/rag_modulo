#!/bin/bash

# Start dependent services
docker run -d --name es01 --net elastic -p 9200:9200 -m 1GB docker.elastic.co/elasticsearch/elasticsearch:8.13.4
docker run -d --name milvus-standalone \
  -p 19530:19530 -p 9091:9091 -p 2379:2379 \
  -v $(pwd)/volumes/milvus:/var/lib/milvus \
  -v $(pwd)/embedEtcd.yaml:/milvus/configs/embedEtcd.yaml \
  -e ETCD_USE_EMBED=true \
  -e ETCD_CONFIG_PATH=/milvus/configs/embedEtcd.yaml \
  -e COMMON_STORAGETYPE=local \
  milvusdb/milvus:v2.4.1 milvus run standalone

# Wait for services to be ready
sleep 30

# Build and run the main application and tests
docker-compose build
docker-compose up -d backend frontend
docker-compose run test

# Cleanup
docker-compose down
docker stop es01 milvus-standalone
docker rm es01 milvus-standalone