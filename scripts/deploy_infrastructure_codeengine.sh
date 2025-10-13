#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# These variables are expected to be set in the GitHub Actions workflow or local environment
# IBM_CLOUD_API_KEY: IBM Cloud API Key for authentication
# IBM_CLOUD_REGION: IBM Cloud region (e.g., 'us-south')
# IBM_CLOUD_RESOURCE_GROUP: IBM Cloud resource group (e.g., 'rag-modulo-deployment')

# Infrastructure specific environment variables
# COLLECTIONDB_USER: PostgreSQL username
# COLLECTIONDB_PASS: PostgreSQL password
# COLLECTIONDB_NAME: PostgreSQL database name
# MINIO_ROOT_USER: MinIO root user
# MINIO_ROOT_PASSWORD: MinIO root password

# Required environment variables for this script
REQUIRED_VARS=(
    "IBM_CLOUD_API_KEY"
    "IBM_CLOUD_REGION"
    "IBM_CLOUD_RESOURCE_GROUP"
    "COLLECTIONDB_USER"
    "COLLECTIONDB_PASS"
    "COLLECTIONDB_NAME"
    "MINIO_ROOT_USER"
    "MINIO_ROOT_PASSWORD"
)

# Check if all required environment variables are set
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: Required environment variable $var is not set." >&2
        exit 1
    fi
done

echo "Environment variables loaded. Testing script syntax..."
# Basic syntax check (can be expanded)
bash -n "$0"
echo "Script syntax is valid!"

# --- Deployment ---
echo "Logging in to IBM Cloud..."
if ! ibmcloud login --apikey "$IBM_CLOUD_API_KEY" -r "$IBM_CLOUD_REGION" -g "$IBM_CLOUD_RESOURCE_GROUP"; then
    echo "Error: Failed to login to IBM Cloud" >&2
    exit 1
fi
echo "Login successful."

# Set the Code Engine project
PROJECT_NAME="rag-modulo-test-project"
echo "Setting Code Engine project to: $PROJECT_NAME"
if ! ibmcloud ce project select --name "$PROJECT_NAME"; then
    echo "Error: Failed to select Code Engine project" >&2
    exit 1
fi

# Deploy PostgreSQL
echo "Deploying PostgreSQL..."
POSTGRES_APP_NAME="rag-modulo-postgres"
POSTGRES_IMAGE="postgres:13"

# Check if PostgreSQL app already exists
if ibmcloud ce app get --name "$POSTGRES_APP_NAME" > /dev/null 2>&1; then
    echo "PostgreSQL application '$POSTGRES_APP_NAME' already exists. Updating..."
    ACTION="update"
else
    echo "PostgreSQL application '$POSTGRES_APP_NAME' does not exist. Creating..."
    ACTION="create"
fi

# Build command array for PostgreSQL
declare -a POSTGRES_CMD_ARGS=(
    "ibmcloud" "ce" "app" "$ACTION"
    "--name" "$POSTGRES_APP_NAME"
    "--image" "$POSTGRES_IMAGE"
    "--memory" "2Gi"
    "--cpu" "0.5"
    "--min-scale" "1"
    "--max-scale" "1"
    "--env" "POSTGRES_DB=$COLLECTIONDB_NAME"
    "--env" "POSTGRES_USER=$COLLECTIONDB_USER"
    "--env" "POSTGRES_PASSWORD=$COLLECTIONDB_PASS"
)

# Add port only for create action
if [ "$ACTION" == "create" ]; then
    POSTGRES_CMD_ARGS+=("--port" "5432")
fi

echo "Executing PostgreSQL deployment command..."
echo "Command: ${POSTGRES_CMD_ARGS[*]}"

if ! "${POSTGRES_CMD_ARGS[@]}"; then
    echo "Error: PostgreSQL deployment command failed" >&2
    exit 1
fi

# Deploy MinIO
echo "Deploying MinIO..."
MINIO_APP_NAME="rag-modulo-minio"
MINIO_IMAGE="minio/minio:latest"

# Check if MinIO app already exists
if ibmcloud ce app get --name "$MINIO_APP_NAME" > /dev/null 2>&1; then
    echo "MinIO application '$MINIO_APP_NAME' already exists. Updating..."
    ACTION="update"
else
    echo "MinIO application '$MINIO_APP_NAME' does not exist. Creating..."
    ACTION="create"
fi

# Build command array for MinIO
declare -a MINIO_CMD_ARGS=(
    "ibmcloud" "ce" "app" "$ACTION"
    "--name" "$MINIO_APP_NAME"
    "--image" "$MINIO_IMAGE"
    "--memory" "1Gi"
    "--cpu" "0.25"
    "--min-scale" "1"
    "--max-scale" "1"
    "--env" "MINIO_ROOT_USER=$MINIO_ROOT_USER"
    "--env" "MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD"
    "--cmd" "server /data --console-address :9001"
)

# Add port only for create action
if [ "$ACTION" == "create" ]; then
    MINIO_CMD_ARGS+=("--port" "9000")
fi

echo "Executing MinIO deployment command..."
echo "Command: ${MINIO_CMD_ARGS[*]}"

if ! "${MINIO_CMD_ARGS[@]}"; then
    echo "Error: MinIO deployment command failed" >&2
    exit 1
fi

# Deploy etcd
echo "Deploying etcd..."
ETCD_APP_NAME="rag-modulo-etcd"
ETCD_IMAGE="quay.io/coreos/etcd:v3.5.9"

# Check if etcd app already exists
if ibmcloud ce app get --name "$ETCD_APP_NAME" > /dev/null 2>&1; then
    echo "etcd application '$ETCD_APP_NAME' already exists. Updating..."
    ACTION="update"
else
    echo "etcd application '$ETCD_APP_NAME' does not exist. Creating..."
    ACTION="create"
fi

# Build command array for etcd
declare -a ETCD_CMD_ARGS=(
    "ibmcloud" "ce" "app" "$ACTION"
    "--name" "$ETCD_APP_NAME"
    "--image" "$ETCD_IMAGE"
    "--memory" "1Gi"
    "--cpu" "0.25"
    "--min-scale" "1"
    "--max-scale" "1"
    "--env" "ETCD_NAME=etcd"
    "--env" "ETCD_DATA_DIR=/etcd-data"
    "--env" "ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379"
    "--env" "ETCD_ADVERTISE_CLIENT_URLS=http://$ETCD_APP_NAME:2379"
    "--env" "ETCD_LISTEN_PEER_URLS=http://0.0.0.0:2380"
    "--env" "ETCD_INITIAL_ADVERTISE_PEER_URLS=http://$ETCD_APP_NAME:2380"
    "--env" "ETCD_INITIAL_CLUSTER=etcd=http://$ETCD_APP_NAME:2380"
    "--env" "ETCD_INITIAL_CLUSTER_TOKEN=etcd-cluster"
    "--env" "ETCD_INITIAL_CLUSTER_STATE=new"
)

# Add port only for create action
if [ "$ACTION" == "create" ]; then
    ETCD_CMD_ARGS+=("--port" "2379")
fi

echo "Executing etcd deployment command..."
echo "Command: ${ETCD_CMD_ARGS[*]}"

if ! "${ETCD_CMD_ARGS[@]}"; then
    echo "Error: etcd deployment command failed" >&2
    exit 1
fi

# Deploy Milvus
echo "Deploying Milvus..."
MILVUS_APP_NAME="rag-modulo-milvus"
MILVUS_IMAGE="milvusdb/milvus:v2.4.4"

# Check if Milvus app already exists
if ibmcloud ce app get --name "$MILVUS_APP_NAME" > /dev/null 2>&1; then
    echo "Milvus application '$MILVUS_APP_NAME' already exists. Updating..."
    ACTION="update"
else
    echo "Milvus application '$MILVUS_APP_NAME' does not exist. Creating..."
    ACTION="create"
fi

# Build command array for Milvus
declare -a MILVUS_CMD_ARGS=(
    "ibmcloud" "ce" "app" "$ACTION"
    "--name" "$MILVUS_APP_NAME"
    "--image" "$MILVUS_IMAGE"
    "--memory" "2Gi"
    "--cpu" "0.5"
    "--min-scale" "1"
    "--max-scale" "1"
    "--env" "ETCD_ENDPOINTS=$ETCD_APP_NAME:2379"
    "--env" "MINIO_ADDRESS=$MINIO_APP_NAME:9000"
    "--env" "MINIO_ACCESS_KEY_ID=$MINIO_ROOT_USER"
    "--env" "MINIO_SECRET_ACCESS_KEY=$MINIO_ROOT_PASSWORD"
    "--env" "COMMON_STORAGETYPE=minio"
    "--env" "MINIO_USE_SSL=false"
    "--env" "ETCD_USE_SSL=false"
    "--cmd" "milvus run standalone"
)

# Add port only for create action
if [ "$ACTION" == "create" ]; then
    MILVUS_CMD_ARGS+=("--port" "19530")
fi

echo "Executing Milvus deployment command..."
echo "Command: ${MILVUS_CMD_ARGS[*]}"

if ! "${MILVUS_CMD_ARGS[@]}"; then
    echo "Error: Milvus deployment command failed" >&2
    exit 1
fi

echo "Infrastructure deployment to IBM Cloud Code Engine finished successfully."

# Post-deployment verification
echo "Verifying infrastructure deployment..."
for app in "$POSTGRES_APP_NAME" "$MINIO_APP_NAME" "$ETCD_APP_NAME" "$MILVUS_APP_NAME"; do
    if ! ibmcloud ce app get --name "$app" > /dev/null 2>&1; then
        echo "Error: Infrastructure application '$app' verification failed" >&2
        exit 1
    fi
done

echo "Infrastructure deployment verification successful."
echo ""
echo "Infrastructure Applications Deployed:"
echo "- PostgreSQL: $POSTGRES_APP_NAME"
echo "- MinIO: $MINIO_APP_NAME"
echo "- etcd: $ETCD_APP_NAME"
echo "- Milvus: $MILVUS_APP_NAME"
echo ""
echo "Note: These applications will be accessible within the Code Engine project."
echo "The backend application will need to be configured to use these service URLs."
