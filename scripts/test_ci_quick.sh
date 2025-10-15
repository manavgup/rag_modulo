#!/bin/bash
# Quick test to verify CI environment fixes

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo "Quick CI Environment Test"
echo "========================================="
echo ""

# Set CI environment variables
export TESTING=true
export SKIP_AUTH=true
export DEVELOPMENT_MODE=true

echo -e "${YELLOW}ℹ${NC} Environment variables set:"
echo "  TESTING=$TESTING"
echo "  SKIP_AUTH=$SKIP_AUTH"
echo "  DEVELOPMENT_MODE=$DEVELOPMENT_MODE"
echo ""

# Test 1: Check if backend is currently healthy
echo -e "${YELLOW}ℹ${NC} Test 1: Checking current backend health..."
if docker inspect rag_modulo-backend-1 --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC} Backend is currently healthy"
else
    echo -e "${YELLOW}ℹ${NC} Backend not healthy, will restart with CI env"
fi

# Test 2: Restart backend with CI environment
echo ""
echo -e "${YELLOW}ℹ${NC} Test 2: Restarting backend with CI environment variables..."
docker compose up -d backend

echo "Waiting for backend to start (30s)..."
sleep 30

# Test 3: Check environment variables in container
echo ""
echo -e "${YELLOW}ℹ${NC} Test 3: Verifying environment variables in container..."
TESTING_VAR=$(docker exec rag_modulo-backend-1 printenv TESTING 2>/dev/null || echo "not set")
SKIP_AUTH_VAR=$(docker exec rag_modulo-backend-1 printenv SKIP_AUTH 2>/dev/null || echo "not set")
DEV_MODE_VAR=$(docker exec rag_modulo-backend-1 printenv DEVELOPMENT_MODE 2>/dev/null || echo "not set")

if [ "$TESTING_VAR" = "true" ] && [ "$SKIP_AUTH_VAR" = "true" ] && [ "$DEV_MODE_VAR" = "true" ]; then
    echo -e "${GREEN}✓${NC} Environment variables correctly set in container"
    echo "    TESTING=$TESTING_VAR"
    echo "    SKIP_AUTH=$SKIP_AUTH_VAR"
    echo "    DEVELOPMENT_MODE=$DEV_MODE_VAR"
else
    echo -e "${RED}✗${NC} Environment variables not correctly set:"
    echo "    TESTING=$TESTING_VAR (expected: true)"
    echo "    SKIP_AUTH=$SKIP_AUTH_VAR (expected: true)"
    echo "    DEVELOPMENT_MODE=$DEV_MODE_VAR (expected: true)"
fi

# Test 4: Check health endpoint
echo ""
echo -e "${YELLOW}ℹ${NC} Test 4: Testing health endpoint..."
HEALTH_STATUS=$(curl -s http://localhost:8000/api/health 2>/dev/null | jq -r '.status' || echo "failed")
if [ "$HEALTH_STATUS" = "healthy" ]; then
    echo -e "${GREEN}✓${NC} Health endpoint returned: $HEALTH_STATUS"
else
    echo -e "${RED}✗${NC} Health endpoint failed or returned: $HEALTH_STATUS"
    echo "Backend logs (last 20 lines):"
    docker logs rag_modulo-backend-1 --tail 20
fi

# Test 5: Check for OIDC errors
echo ""
echo -e "${YELLOW}ℹ${NC} Test 5: Checking for OIDC connection errors..."
if docker logs rag_modulo-backend-1 2>&1 | grep -i "failed to connect\|connection refused" | grep -i "oidc\|oauth\|mock-oidc"; then
    echo -e "${RED}✗${NC} Found OIDC connection errors in logs"
    docker logs rag_modulo-backend-1 2>&1 | grep -i "oidc" | tail -5
else
    echo -e "${GREEN}✓${NC} No OIDC connection errors found"
fi

# Test 6: Check backend health status
echo ""
echo -e "${YELLOW}ℹ${NC} Test 6: Checking Docker health status..."
HEALTH_STATUS=$(docker inspect rag_modulo-backend-1 --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
if [ "$HEALTH_STATUS" = "healthy" ]; then
    echo -e "${GREEN}✓${NC} Backend container is healthy"
else
    echo -e "${YELLOW}ℹ${NC} Backend health status: $HEALTH_STATUS"
    echo "Waiting another 30s for health check..."
    sleep 30
    HEALTH_STATUS=$(docker inspect rag_modulo-backend-1 --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        echo -e "${GREEN}✓${NC} Backend container is now healthy"
    else
        echo -e "${RED}✗${NC} Backend still not healthy: $HEALTH_STATUS"
    fi
fi

# Test 7: Try accessing a protected endpoint
echo ""
echo -e "${YELLOW}ℹ${NC} Test 7: Testing protected endpoint without auth (should work in CI mode)..."
RESPONSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/collections 2>/dev/null || echo "000")
if [ "$RESPONSE_CODE" = "200" ] || [ "$RESPONSE_CODE" = "404" ]; then
    echo -e "${GREEN}✓${NC} Protected endpoint accessible (HTTP $RESPONSE_CODE) - auth properly skipped"
elif [ "$RESPONSE_CODE" = "401" ]; then
    echo -e "${RED}✗${NC} Got 401 Unauthorized - auth not properly skipped"
else
    echo -e "${YELLOW}ℹ${NC} Got HTTP $RESPONSE_CODE"
fi

# Summary
echo ""
echo "========================================="
echo "Test Complete"
echo "========================================="
echo ""
echo "If all tests passed, the CI environment fixes are working correctly!"
echo "You can now run: ./test_ci_environment.sh for a full test suite"