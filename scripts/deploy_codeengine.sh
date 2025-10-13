#!/bin/bash
set -e

# This script deploys the application to IBM Cloud Code Engine.
# It assumes the following environment variables are set:
# - IBM_CLOUD_API_KEY: Your IBM Cloud API key.
# - IMAGE_URL: The full URL of the Docker image to deploy (e.g., us.icr.io/namespace/image:tag).
# - APP_NAME: The name of the Code Engine application.
# - All other application-specific environment variables (e.g., SKIP_AUTH, DB_HOST, etc.)

# --- Configuration (can be overridden by environment variables) ---
IBM_CLOUD_REGION=${IBM_CLOUD_REGION:-"us-south"}
IBM_CLOUD_RESOURCE_GROUP=${IBM_CLOUD_RESOURCE_GROUP:-"Default"}

# --- Validation ---
REQUIRED_VARS=(
    "IBM_CLOUD_API_KEY" "IMAGE_URL" "APP_NAME" "SKIP_AUTH" "OIDC_DISCOVERY_ENDPOINT"
    "IBM_CLIENT_ID" "IBM_CLIENT_SECRET" "FRONTEND_URL" "WATSONX_APIKEY"
    "WATSONX_INSTANCE_ID" "COLLECTIONDB_USER" "COLLECTIONDB_PASS" "COLLECTIONDB_HOST"
    "COLLECTIONDB_PORT" "COLLECTIONDB_NAME" "VECTOR_DB" "MILVUS_HOST" "MILVUS_PORT"
    "MILVUS_USER" "MILVUS_PASSWORD" "JWT_SECRET_KEY" "LOG_LEVEL"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: Required environment variable $var is not set." >&2
        exit 1
    fi
done

# --- Deployment ---
echo "Logging in to IBM Cloud..."
if ! ibmcloud login --apikey "$IBM_CLOUD_API_KEY" -r "$IBM_CLOUD_REGION" -g "$IBM_CLOUD_RESOURCE_GROUP"; then
    echo "Error: Failed to login to IBM Cloud" >&2
    exit 1
fi
echo "Login successful."

# Set the Code Engine project
PROJECT_NAME="rag-modulo"
echo "Setting Code Engine project to: $PROJECT_NAME"
if ! ibmcloud ce project select --name "$PROJECT_NAME"; then
    echo "Error: Failed to select Code Engine project" >&2
    exit 1
fi

# Check if the application already exists
if ibmcloud ce app get --name "$APP_NAME" > /dev/null 2>&1; then
    echo "Application '$APP_NAME' already exists. Updating..."
    ACTION="update"
else
    echo "Application '$APP_NAME' does not exist. Creating..."
    ACTION="create"
fi

# Build command array to prevent command injection
        declare -a CMD_ARGS=(
            "ibmcloud" "ce" "app" "$ACTION"
            "--name" "$APP_NAME"
            "--image" "$IMAGE_URL"
            "--memory" "4Gi"
            "--cpu" "1"
            "--min-scale" "1"
            "--max-scale" "5"
        )

# Add port only for create action
if [ "$ACTION" == "create" ]; then
    CMD_ARGS+=("--port" "8000")
fi

# Add all environment variables from the current environment
for var in "${REQUIRED_VARS[@]}"; do
    # Skip the API key as it is not needed by the application itself
    if [ "$var" != "IBM_CLOUD_API_KEY" ]; then
        CMD_ARGS+=("--env" "$var=${!var}")
    fi
done

# Add other optional env vars
CMD_ARGS+=("--env" "PYTHONPATH=/app" "--env" "CONTAINER_ENV=1")

echo "Executing Code Engine command..."
echo "Command: ${CMD_ARGS[*]}"

# Execute the command safely using array expansion
if ! "${CMD_ARGS[@]}"; then
    echo "Error: Deployment command failed" >&2
    exit 1
fi

echo "Deployment to IBM Cloud Code Engine finished successfully."

# Post-deployment verification
echo "Verifying deployment..."
if ! ibmcloud ce app get --name "$APP_NAME" > /dev/null 2>&1; then
    echo "Error: Application verification failed" >&2
    exit 1
fi

echo "Deployment verification successful."
