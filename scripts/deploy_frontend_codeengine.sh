#!/bin/bash

# Deploy Frontend to IBM Cloud Code Engine
# This script deploys the React frontend application to IBM Cloud Code Engine

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check required environment variables
REQUIRED_VARS=(
    "IBM_CLOUD_API_KEY"
    "IMAGE_URL"
    "APP_NAME"
    "IBM_CLOUD_REGION"
    "IBM_CLOUD_RESOURCE_GROUP"
)

print_status "Checking required environment variables..."
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required environment variable $var is not set."
        exit 1
    fi
done

print_status "All required environment variables are set."

# --- IBM Cloud Login ---
print_status "Logging in to IBM Cloud..."
if ! ibmcloud login --apikey "$IBM_CLOUD_API_KEY" -r "$IBM_CLOUD_REGION" -g "$IBM_CLOUD_RESOURCE_GROUP"; then
    print_error "Failed to login to IBM Cloud"
    exit 1
fi
print_status "Login successful."

# --- Deployment ---
print_status "Checking if the frontend application already exists..."
if ibmcloud ce app get --name "$APP_NAME" > /dev/null 2>&1; then
    print_status "Application '$APP_NAME' already exists. Updating..."
    ACTION="update"
else
    print_status "Application '$APP_NAME' does not exist. Creating..."
    ACTION="create"
fi

# Build command array to prevent command injection
declare -a CMD_ARGS=(
    "ibmcloud" "ce" "app" "$ACTION"
    "--name" "$APP_NAME"
    "--image" "$IMAGE_URL"
    "--memory" "1Gi"
    "--cpu" "0.5"
    "--min-scale" "1"
    "--max-scale" "3"
)

# Add port only for create action
if [ "$ACTION" == "create" ]; then
    CMD_ARGS+=("--port" "3000")
fi

# Add environment variables
if [ -n "$REACT_APP_API_URL" ]; then
    CMD_ARGS+=("--env" "REACT_APP_API_URL=$REACT_APP_API_URL")
fi

if [ -n "$REACT_APP_WS_URL" ]; then
    CMD_ARGS+=("--env" "REACT_APP_WS_URL=$REACT_APP_WS_URL")
fi

# Add other environment variables
CMD_ARGS+=("--env" "NODE_ENV=production")

print_status "Executing Code Engine command..."
print_status "Command: ${CMD_ARGS[*]}"

# Execute the command safely using array expansion
if ! "${CMD_ARGS[@]}"; then
    print_error "Deployment command failed"
    exit 1
fi

print_status "Frontend deployment to IBM Cloud Code Engine finished successfully."

# Post-deployment verification
print_status "Verifying deployment..."
if ! ibmcloud ce app get --name "$APP_NAME" > /dev/null 2>&1; then
    print_error "Application verification failed"
    exit 1
fi

print_status "Frontend deployment verification successful."
print_status "Frontend application '$APP_NAME' is now deployed and ready!"
