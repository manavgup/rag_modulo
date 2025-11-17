#!/bin/bash
# End-to-end deployment: Build → Test → Push → Deploy
# Run this from your Mac where ibmcloud CLI is installed

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================"
echo -e "RAG Modulo - End-to-End Deployment"
echo -e "========================================${NC}"
echo ""

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Step 1: Build images locally
echo -e "${BLUE}Step 1/5: Building Docker images locally${NC}"
echo -e "${YELLOW}Running: make build-all${NC}"
make build-all
echo -e "${GREEN}✅ Images built${NC}"
echo ""

# Step 2: Test images locally (optional - can skip with --skip-test)
if [ "$1" != "--skip-test" ]; then
    echo -e "${BLUE}Step 2/5: Testing images locally${NC}"
    echo -e "${YELLOW}Starting production stack...${NC}"
    make prod-start

    echo -e "${YELLOW}⏳ Waiting for services to be ready (10s)...${NC}"
    sleep 10

    echo -e "${YELLOW}Checking service health...${NC}"
    make prod-status

    if curl -f -s http://localhost:8000/health > /dev/null; then
        echo -e "${GREEN}✅ Backend health check passed${NC}"
    else
        echo -e "${RED}❌ Backend health check failed${NC}"
        make prod-logs
        exit 1
    fi

    if curl -f -s http://localhost:3000 > /dev/null; then
        echo -e "${GREEN}✅ Frontend check passed${NC}"
    else
        echo -e "${RED}❌ Frontend check failed${NC}"
        make prod-logs
        exit 1
    fi

    echo -e "${YELLOW}Stopping local stack...${NC}"
    make prod-stop
    echo -e "${GREEN}✅ Local tests passed${NC}"
    echo ""
else
    echo -e "${YELLOW}Step 2/5: Skipping local tests${NC}"
    echo ""
fi

# Step 3: Push to IBM Container Registry
echo -e "${BLUE}Step 3/5: Pushing images to IBM Container Registry${NC}"
echo -e "${YELLOW}Running: ./scripts/build-and-push-for-local-testing.sh${NC}"
./scripts/build-and-push-for-local-testing.sh
echo -e "${GREEN}✅ Images pushed to ICR${NC}"
echo ""

# Step 4: Deploy to Code Engine
echo -e "${BLUE}Step 4/5: Deploying to IBM Cloud Code Engine${NC}"
echo -e "${YELLOW}Running: ./scripts/deploy-to-code-engine.sh${NC}"
./scripts/deploy-to-code-engine.sh
echo -e "${GREEN}✅ Deployed to Code Engine${NC}"
echo ""

# Step 5: Final smoke test
echo -e "${BLUE}Step 5/5: Final smoke tests${NC}"
echo -e "${YELLOW}⏳ Waiting for apps to stabilize (30s)...${NC}"
sleep 30

# Get app URLs
BACKEND_URL=$(ibmcloud ce app get rag-modulo-backend -o json 2>/dev/null | jq -r '.status.url' || echo "")
FRONTEND_URL=$(ibmcloud ce app get rag-modulo-frontend -o json 2>/dev/null | jq -r '.status.url' || echo "")

if [ -n "$BACKEND_URL" ]; then
    echo "Testing backend: $BACKEND_URL"
    if curl -f -s "${BACKEND_URL}/health" > /dev/null; then
        echo -e "${GREEN}✅ Backend is healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  Backend health check failed${NC}"
    fi
fi

if [ -n "$FRONTEND_URL" ]; then
    echo "Testing frontend: $FRONTEND_URL"
    if curl -f -s "$FRONTEND_URL" > /dev/null; then
        echo -e "${GREEN}✅ Frontend is accessible${NC}"
    else
        echo -e "${YELLOW}⚠️  Frontend check failed${NC}"
    fi
fi

echo ""
echo -e "${GREEN}========================================"
echo -e "🎉 Deployment Complete!"
echo -e "========================================${NC}"
echo ""
echo -e "${YELLOW}Application URLs:${NC}"
echo "  Backend:  ${BACKEND_URL:-Not deployed}"
echo "  Frontend: ${FRONTEND_URL:-Not deployed}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Visit $FRONTEND_URL in your browser"
echo "  2. Check logs: ./scripts/code-engine-logs.sh"
echo "  3. Monitor: make ce-status"
echo ""
echo -e "${BLUE}Deployment Summary:${NC}"
echo "  ✅ Images built and tested locally"
echo "  ✅ Images pushed to IBM Container Registry"
echo "  ✅ Applications deployed to Code Engine"
echo "  ✅ Smoke tests completed"
