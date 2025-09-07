#!/bin/bash
# .github/scripts/wait-for-services.sh
#
# Waits for the main backend service to become healthy by polling its health endpoint.
# This is the single source of truth, as the backend should only report itself
# as healthy once it has successfully connected to its database and other dependencies.

set -euo pipefail

# --- Configuration ---
# The URL of the backend's health check endpoint
API_HEALTH_URL="http://localhost:8000/api/health"
# Maximum time to wait in seconds
TIMEOUT=180
# Interval between retries in seconds
INTERVAL=5

# --- Color Codes ---
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Main Logic ---
echo -e "${BLUE}[INFO]${NC} Starting health check for backend service at: ${API_HEALTH_URL}"
echo -e "${BLUE}[INFO]${NC} Timeout set to ${TIMEOUT} seconds."

start_time=$(date +%s)

while true; do
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))

    # Check for timeout
    if [ $elapsed_time -ge $TIMEOUT ]; then
        echo -e "${RED}[ERROR]${NC} Timeout reached after ${elapsed_time}s. Backend service did not become healthy."
        exit 1
    fi

    # Use curl to get the HTTP status code from the health endpoint
    # -s: silent mode
    # -o /dev/null: discard the body
    # -w "%{http_code}": print only the status code to stdout
    http_status=$(curl -s -o /dev/null -w "%{http_code}" "$API_HEALTH_URL" || echo "000")

    if [ "$http_status" -eq 200 ]; then
        echo -e "${GREEN}[SUCCESS]${NC} Backend service is healthy! Responded with HTTP 200 after ${elapsed_time}s."
        exit 0
    else
        echo -e "${BLUE}[INFO]${NC} Backend not ready yet (HTTP status: $http_status). Retrying in $INTERVAL seconds..."
        sleep $INTERVAL
    fi
done
