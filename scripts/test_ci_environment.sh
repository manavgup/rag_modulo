#!/bin/bash
# Test script to validate CI environment fixes before pushing to GitHub
# This simulates the exact conditions that occur in GitHub Actions

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "CI Environment Test Suite"
echo "========================================="
echo ""

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Track overall test status
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name=$1
    local test_command=$2

    echo ""
    echo "Running: $test_name"
    echo "----------------------------------------"

    if eval "$test_command"; then
        print_status 0 "$test_name passed"
        ((TESTS_PASSED++))
    else
        print_status 1 "$test_name failed"
        ((TESTS_FAILED++))
    fi
}

# Clean up function
cleanup() {
    print_info "Cleaning up test environment..."
    docker compose down
    unset TESTING
    unset SKIP_AUTH
    unset DEVELOPMENT_MODE
}

# Set up trap to cleanup on exit
trap cleanup EXIT

# Test 1: Environment Variable Setup
test_env_setup() {
    print_info "Setting CI environment variables..."
    export TESTING=true
    export SKIP_AUTH=true
    export DEVELOPMENT_MODE=true

    # Verify they're set
    [ "$TESTING" = "true" ] && \
    [ "$SKIP_AUTH" = "true" ] && \
    [ "$DEVELOPMENT_MODE" = "true" ]
}

# Test 2: Docker Compose Configuration
test_docker_compose_config() {
    print_info "Validating docker-compose configuration..."
    docker compose config > /dev/null 2>&1
}

# Test 3: Start Infrastructure Services
test_start_infrastructure() {
    print_info "Starting infrastructure services (postgres, milvus)..."
    docker compose up -d postgres milvus-etcd milvus-standalone minio

    print_info "Waiting for infrastructure to be ready..."
    sleep 30

    # Check if services are healthy
    docker compose ps | grep -E "postgres|milvus-standalone" | grep -v "Exited"
}

# Test 4: Start Backend with CI Environment
test_backend_startup() {
    print_info "Starting backend with CI environment variables..."

    # Copy .env.ci to .env to simulate CI
    cp .env.ci .env

    # Start backend with CI environment
    TESTING=true SKIP_AUTH=true DEVELOPMENT_MODE=true \
        docker compose up -d backend

    print_info "Waiting for backend to start (60s)..."
    sleep 60

    # Check if backend is running
    docker ps | grep "rag_modulo-backend" | grep -v "Exited"
}

# Test 5: Backend Health Check
test_backend_health() {
    print_info "Checking backend health status..."

    local max_retries=10
    local retry_count=0

    while [ $retry_count -lt $max_retries ]; do
        if docker inspect rag_modulo-backend-1 --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
            return 0
        fi

        print_info "Waiting for backend to be healthy... ($((retry_count+1))/$max_retries)"
        sleep 5
        ((retry_count++))
    done

    # If we get here, health check failed
    print_info "Backend logs:"
    docker logs rag_modulo-backend-1 --tail 50
    return 1
}

# Test 6: Health Endpoint Accessibility
test_health_endpoint() {
    print_info "Testing /api/health endpoint..."

    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health)

    if [ "$response" = "200" ]; then
        print_info "Health endpoint returned: $(curl -s http://localhost:8000/api/health | jq -r '.status')"
        return 0
    else
        print_info "Health endpoint returned HTTP $response"
        return 1
    fi
}

# Test 7: OIDC Skip Verification
test_oidc_skip() {
    print_info "Verifying OIDC registration was skipped..."

    # Check logs for OIDC skip message
    if docker logs rag_modulo-backend-1 2>&1 | grep -q "OIDC registration skipped"; then
        return 0
    fi

    # Also check that there are no OIDC connection errors
    if docker logs rag_modulo-backend-1 2>&1 | grep -i "connection refused\|failed to connect" | grep -i "oidc\|oauth"; then
        print_info "Found OIDC connection errors in logs"
        return 1
    fi

    # If no skip message but also no errors, that's okay
    print_info "No OIDC errors detected"
    return 0
}

# Test 8: Authentication Middleware Skip
test_auth_skip() {
    print_info "Testing authentication skip for protected endpoints..."

    # Try to access a normally protected endpoint
    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/collections)

    if [ "$response" = "200" ] || [ "$response" = "404" ]; then
        print_info "Protected endpoint accessible without auth (expected in CI mode)"
        return 0
    elif [ "$response" = "401" ]; then
        print_info "Got 401 Unauthorized (auth not properly skipped)"
        return 1
    else
        print_info "Got HTTP $response"
        return 1
    fi
}

# Test 9: Run a Simple Integration Test
test_integration_sample() {
    print_info "Running sample integration test..."

    # Run a simple test through docker compose
    docker compose run --rm \
        -e TESTING=true \
        -e SKIP_AUTH=true \
        -e DEVELOPMENT_MODE=true \
        test python -c "import requests; r = requests.get('http://backend:8000/api/health'); assert r.status_code == 200; print('Integration test passed')" 2>/dev/null
}

# Test 10: Container Environment Variables
test_container_env() {
    print_info "Verifying environment variables in container..."

    local testing_var=$(docker exec rag_modulo-backend-1 printenv TESTING 2>/dev/null)
    local skip_auth_var=$(docker exec rag_modulo-backend-1 printenv SKIP_AUTH 2>/dev/null)
    local dev_mode_var=$(docker exec rag_modulo-backend-1 printenv DEVELOPMENT_MODE 2>/dev/null)

    if [ "$testing_var" = "true" ] && [ "$skip_auth_var" = "true" ] && [ "$dev_mode_var" = "true" ]; then
        print_info "Environment variables correctly set in container"
        return 0
    else
        print_info "Environment variables not correctly set:"
        print_info "  TESTING=$testing_var (expected: true)"
        print_info "  SKIP_AUTH=$skip_auth_var (expected: true)"
        print_info "  DEVELOPMENT_MODE=$dev_mode_var (expected: true)"
        return 1
    fi
}

# Main test execution
main() {
    echo "Starting CI environment tests..."
    echo ""

    # Stop any existing containers
    print_info "Stopping existing containers..."
    docker compose down

    # Run all tests
    run_test "Environment Variable Setup" test_env_setup
    run_test "Docker Compose Configuration" test_docker_compose_config
    run_test "Infrastructure Startup" test_start_infrastructure
    run_test "Backend Startup with CI Environment" test_backend_startup
    run_test "Backend Health Check" test_backend_health
    run_test "Health Endpoint Accessibility" test_health_endpoint
    run_test "OIDC Registration Skip" test_oidc_skip
    run_test "Authentication Middleware Skip" test_auth_skip
    run_test "Container Environment Variables" test_container_env
    run_test "Sample Integration Test" test_integration_sample

    # Print summary
    echo ""
    echo "========================================="
    echo "Test Summary"
    echo "========================================="
    echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
    echo -e "${RED}Failed:${NC} $TESTS_FAILED"
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed! ✓${NC}"
        echo "The CI environment fixes are working correctly."
        echo "It should be safe to push to GitHub."
        exit 0
    else
        echo -e "${RED}Some tests failed! ✗${NC}"
        echo "Please review the failures before pushing to GitHub."
        exit 1
    fi
}

# Run main function
main
