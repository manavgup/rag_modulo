#!/bin/bash
# Deploy to IBM Cloud Code Engine
# Run this from your Mac where ibmcloud CLI is installed
# Prerequisites: Images already pushed to ICR (run build-and-push-for-local-testing.sh first)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deploy to IBM Cloud Code Engine${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load configuration
SECRETS_FILE="${PROJECT_ROOT}/.secrets"
VARS_FILE="${PROJECT_ROOT}/.vars"

if [ -f "$SECRETS_FILE" ]; then
    source "$SECRETS_FILE"
fi

if [ -f "$VARS_FILE" ]; then
    source "$VARS_FILE"
fi

# Configuration
IBM_CLOUD_REGION="${IBM_CLOUD_REGION:-ca-tor}"
RESOURCE_GROUP="${IBM_CLOUD_RESOURCE_GROUP:-Default}"
PROJECT_NAME="${CODE_ENGINE_PROJECT:-rag-modulo}"
CR_NAMESPACE="${IBM_CR_NAMESPACE:-rag_modulo}"

# Get git SHA or use provided tag
if [ -n "$1" ]; then
    IMAGE_TAG="$1"
    echo -e "${YELLOW}📝 Using provided image tag: ${IMAGE_TAG}${NC}"
else
    IMAGE_TAG=$(git rev-parse HEAD)
    echo -e "${YELLOW}📝 Using git SHA as tag: ${IMAGE_TAG}${NC}"
fi

# Convert region to ICR format
if [ "$IBM_CLOUD_REGION" = "us-south" ] || [ "$IBM_CLOUD_REGION" = "us-east" ]; then
    ICR_REGION="us"
elif [ "$IBM_CLOUD_REGION" = "eu-gb" ]; then
    ICR_REGION="uk"
elif [ "$IBM_CLOUD_REGION" = "ca-tor" ]; then
    ICR_REGION="ca"
else
    ICR_REGION="$IBM_CLOUD_REGION"
fi

BACKEND_IMAGE="${ICR_REGION}.icr.io/${CR_NAMESPACE}/rag-modulo-backend:${IMAGE_TAG}"
FRONTEND_IMAGE="${ICR_REGION}.icr.io/${CR_NAMESPACE}/rag-modulo-frontend:${IMAGE_TAG}"

echo -e "${YELLOW}🌍 Region: ${IBM_CLOUD_REGION}${NC}"
echo -e "${YELLOW}📦 ICR Region: ${ICR_REGION}${NC}"
echo -e "${YELLOW}🏗️  Project: ${PROJECT_NAME}${NC}"
echo -e "${YELLOW}📦 Namespace: ${CR_NAMESPACE}${NC}"
echo ""

# Check if IBM Cloud CLI is installed
if ! command -v ibmcloud &> /dev/null; then
    echo -e "${RED}❌ IBM Cloud CLI not found${NC}"
    echo "Install from: https://cloud.ibm.com/docs/cli"
    exit 1
fi

# Check for API key
if [ -z "$IBM_CLOUD_API_KEY" ]; then
    echo -e "${RED}❌ IBM_CLOUD_API_KEY not set in .secrets${NC}"
    exit 1
fi

# Login to IBM Cloud
echo -e "${YELLOW}🔐 Logging into IBM Cloud...${NC}"
ibmcloud login --apikey "$IBM_CLOUD_API_KEY" -r "$IBM_CLOUD_REGION" -g "$RESOURCE_GROUP"
echo -e "${GREEN}✅ Logged in${NC}"
echo ""

# Install Code Engine plugin if needed
if ! ibmcloud plugin list | grep -q code-engine; then
    echo -e "${YELLOW}📦 Installing Code Engine plugin...${NC}"
    ibmcloud plugin install code-engine -f
    echo -e "${GREEN}✅ Plugin installed${NC}"
fi

# Setup Code Engine project
echo -e "${YELLOW}🏗️  Setting up Code Engine project...${NC}"

# Check if project exists and is soft-deleted
PROJECT_STATUS=$(ibmcloud ce project get --name "$PROJECT_NAME" 2>&1 || echo "not_found")

if echo "$PROJECT_STATUS" | grep -q "soft_deleted"; then
    echo -e "${YELLOW}⚠️  Project '$PROJECT_NAME' is soft-deleted${NC}"
    echo -e "${YELLOW}Creating new project with timestamp...${NC}"
    NEW_PROJECT="${PROJECT_NAME}-$(date +%s)"
    ibmcloud ce project create --name "$NEW_PROJECT"
    PROJECT_NAME="$NEW_PROJECT"
    echo -e "${GREEN}✅ Created new project: $PROJECT_NAME${NC}"
elif echo "$PROJECT_STATUS" | grep -q "not_found"; then
    echo -e "${YELLOW}Creating new project...${NC}"
    ibmcloud ce project create --name "$PROJECT_NAME"
    echo -e "${GREEN}✅ Project created${NC}"
else
    echo -e "${YELLOW}Using existing project...${NC}"
    ibmcloud ce project select --name "$PROJECT_NAME"
    echo -e "${GREEN}✅ Project selected${NC}"
fi
echo ""

# Verify images exist in ICR
echo -e "${YELLOW}🔍 Verifying images in ICR...${NC}"
if ! docker manifest inspect "$BACKEND_IMAGE" > /dev/null 2>&1; then
    echo -e "${RED}❌ Backend image not found: $BACKEND_IMAGE${NC}"
    echo -e "${YELLOW}💡 Run: ./scripts/build-and-push-for-local-testing.sh${NC}"
    exit 1
fi

if ! docker manifest inspect "$FRONTEND_IMAGE" > /dev/null 2>&1; then
    echo -e "${RED}❌ Frontend image not found: $FRONTEND_IMAGE${NC}"
    echo -e "${YELLOW}💡 Run: ./scripts/build-and-push-for-local-testing.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Images verified${NC}"
echo ""

# Deploy Backend
echo -e "${YELLOW}🚀 Deploying backend...${NC}"
if ibmcloud ce app get --name rag-modulo-backend > /dev/null 2>&1; then
    echo "Updating existing backend app..."
    ibmcloud ce app update rag-modulo-backend \
        --image "$BACKEND_IMAGE" \
        --port 8000 \
        --cpu 2 \
        --memory 4G \
        --min-scale 1 \
        --max-scale 5 \
        --env-from-secret rag-modulo-secrets 2>/dev/null || {
            echo -e "${YELLOW}No secrets found, deploying without secrets${NC}"
            ibmcloud ce app update rag-modulo-backend \
                --image "$BACKEND_IMAGE" \
                --port 8000 \
                --cpu 2 \
                --memory 4G \
                --min-scale 1 \
                --max-scale 5
        }
else
    echo "Creating new backend app..."
    ibmcloud ce app create rag-modulo-backend \
        --image "$BACKEND_IMAGE" \
        --port 8000 \
        --cpu 2 \
        --memory 4G \
        --min-scale 1 \
        --max-scale 5 \
        --env-from-secret rag-modulo-secrets 2>/dev/null || {
            echo -e "${YELLOW}No secrets found, deploying without secrets${NC}"
            ibmcloud ce app create rag-modulo-backend \
                --image "$BACKEND_IMAGE" \
                --port 8000 \
                --cpu 2 \
                --memory 4G \
                --min-scale 1 \
                --max-scale 5
        }
fi

# Get backend URL
BACKEND_URL=$(ibmcloud ce app get rag-modulo-backend -o json | jq -r '.status.url')
echo -e "${GREEN}✅ Backend deployed: $BACKEND_URL${NC}"
echo ""

# Deploy Frontend
echo -e "${YELLOW}🚀 Deploying frontend...${NC}"
if ibmcloud ce app get --name rag-modulo-frontend > /dev/null 2>&1; then
    echo "Updating existing frontend app..."
    ibmcloud ce app update rag-modulo-frontend \
        --image "$FRONTEND_IMAGE" \
        --port 8080 \
        --cpu 1 \
        --memory 2G \
        --min-scale 1 \
        --max-scale 3 \
        --env BACKEND_URL="$BACKEND_URL"
else
    echo "Creating new frontend app..."
    ibmcloud ce app create rag-modulo-frontend \
        --image "$FRONTEND_IMAGE" \
        --port 8080 \
        --cpu 1 \
        --memory 2G \
        --min-scale 1 \
        --max-scale 3 \
        --env BACKEND_URL="$BACKEND_URL"
fi

# Get frontend URL
FRONTEND_URL=$(ibmcloud ce app get rag-modulo-frontend -o json | jq -r '.status.url')
echo -e "${GREEN}✅ Frontend deployed: $FRONTEND_URL${NC}"
echo ""

# Wait for apps to be ready
echo -e "${YELLOW}⏳ Waiting for apps to be ready (30s)...${NC}"
sleep 30

# Check app status
echo -e "${YELLOW}📊 Application Status:${NC}"
ibmcloud ce app list
echo ""

# Smoke test
echo -e "${YELLOW}🔥 Running smoke tests...${NC}"

echo "Testing backend health..."
if curl -f -s "${BACKEND_URL}/health" > /dev/null; then
    echo -e "${GREEN}✅ Backend health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Backend health check failed (may still be starting)${NC}"
fi

echo "Testing frontend..."
if curl -f -s "$FRONTEND_URL" > /dev/null; then
    echo -e "${GREEN}✅ Frontend check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend check failed (may still be starting)${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Application URLs:${NC}"
echo "  Backend:  $BACKEND_URL"
echo "  Frontend: $FRONTEND_URL"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Visit $FRONTEND_URL in your browser"
echo "  2. Check logs: ./scripts/code-engine-logs.sh"
echo "  3. Monitor: ibmcloud ce app list"
