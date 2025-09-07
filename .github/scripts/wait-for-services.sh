#!/bin/bash
# .github/scripts/wait-for-services.sh

set -e

# Timeout duration in seconds
TIMEOUT=180
# Interval between checks in seconds
INTERVAL=5

# Health check endpoints
API_HEALTH_URL="http://localhost:8000/api/health"

echo "Waiting for backend service to be healthy..."
start_time=$(date +%s)

while true; do
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))

    if [ $elapsed_time -ge $TIMEOUT ]; then
        echo "Error: Timed out waiting for services to become healthy."
        exit 1
    fi

    # Use curl to check the API health endpoint
    # -s for silent, -o /dev/null to discard output, -w "%{http_code}" to print only the status code
    http_status=$(curl -s -o /dev/null -w "%{http_code}" "$API_HEALTH_URL")

    if [ "$http_status" -eq 200 ]; then
        echo "Success: Backend service is healthy and responded with HTTP 200."
        break
    else
        echo "Backend service not ready yet (HTTP status: $http_status). Retrying in $INTERVAL seconds..."
        sleep $INTERVAL
    fi
done

echo "All services are ready!"
exit 0
