#!/bin/bash
# Helper script for testing GitHub Actions workflows locally with 'act'
# This script simplifies the process of building, deploying, and tearing down
# the RAG Modulo application using local workflow testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration files
VARS_FILE="${PROJECT_ROOT}/.vars"
SECRETS_FILE="${PROJECT_ROOT}/.secrets"
ACT_PLATFORM="linux/amd64"

# Print banner
print_banner() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"
    
    # Check act is installed
    if ! command -v act &> /dev/null; then
        echo -e "${RED}❌ 'act' is not installed${NC}"
        echo "Install with: brew install act"
        exit 1
    fi
    echo -e "${GREEN}  ✅ act is installed${NC}"
    
    # Check Docker is running
    if ! docker ps &> /dev/null; then
        echo -e "${RED}❌ Docker is not running${NC}"
        echo "Start Docker and try again"
        exit 1
    fi
    echo -e "${GREEN}  ✅ Docker is running${NC}"
    
    # Check .vars file exists
    if [ ! -f "$VARS_FILE" ]; then
        echo -e "${RED}❌ .vars file not found${NC}"
        echo "Expected location: $VARS_FILE"
        exit 1
    fi
    echo -e "${GREEN}  ✅ .vars file found${NC}"
    
    # Check .secrets file exists
    if [ ! -f "$SECRETS_FILE" ]; then
        echo -e "${RED}❌ .secrets file not found${NC}"
        echo ""
        echo "Create .secrets file with IBM Cloud credentials:"
        echo "  cp .secrets.example .secrets"
        echo "  # Edit .secrets with your actual credentials"
        exit 1
    fi
    echo -e "${GREEN}  ✅ .secrets file found${NC}"
    
    echo -e "${GREEN}✅ All prerequisites OK${NC}"
    echo ""
}

# Build and push images
build_and_push() {
    print_banner "Building and Pushing Images to ICR"
    
    if [ ! -f "$SCRIPT_DIR/build-and-push-for-local-testing.sh" ]; then
        echo -e "${RED}❌ Build script not found${NC}"
        exit 1
    fi
    
    # IMPORTANT: Ensure the build script uses 'docker buildx build --load' for Mac compatibility
    bash "$SCRIPT_DIR/build-and-push-for-local-testing.sh"
}

# Test deploy workflow
test_deploy() {
    print_banner "Testing Deploy Workflow with act"
    
    echo -e "${YELLOW}Running deployment workflow...${NC}"
    echo "This will:"
    echo "  1. Create/select Code Engine project"
    echo "  2. Deploy backend application"
    echo "  3. Deploy frontend application"
    echo ""
    
    act workflow_dispatch \
        -W .github/workflows/deploy_complete_app.yml \
        --var-file "$VARS_FILE" \
        --secret-file "$SECRETS_FILE" \
        --container-architecture "$ACT_PLATFORM" \
        --input environment=dev \
        --input skip_security_scan=true \
        --input deploy_after_build=true
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ Deploy workflow completed successfully${NC}"
    else
        echo ""
        echo -e "${RED}❌ Deploy workflow failed${NC}"
        exit 1
    fi
}

# Direct deploy using IBM Cloud CLI (bypasses act)
deploy_direct() {
    print_banner "Direct Deployment via IBM Cloud CLI"
    
    # Source ALL configuration files needed for deployment
    if [ -f "$SECRETS_FILE" ]; then
        source "$SECRETS_FILE"
    fi
    if [ -f "$VARS_FILE" ]; then
        source "$VARS_FILE"
    fi
    
    if [ -z "$IBM_CLOUD_API_KEY" ]; then
        echo -e "${RED}❌ IBM_CLOUD_API_KEY not set in .secrets${NC}"
        exit 1
    fi
    
    # Get configuration (using defaults if not set)
    IBM_CLOUD_REGION="${IBM_CLOUD_REGION:-us-south}"
    IBM_CLOUD_RESOURCE_GROUP="${IBM_CLOUD_RESOURCE_GROUP:-rag-modulo-deployment}"
    PROJECT_NAME="rag-modulo-dev"
    CR_NAMESPACE="${IBM_CR_NAMESPACE:-rag_modulo}"
    
    # Convert region to ICR format
    if [ "$IBM_CLOUD_REGION" = "us-south" ] || [ "$IBM_CLOUD_REGION" = "us-east" ]; then
        ICR_REGION="us"
    elif [ "$IBM_CLOUD_REGION" = "eu-gb" ]; then
        ICR_REGION="uk"
    else
        ICR_REGION="$IBM_CLOUD_REGION"
    fi
    
    # Get git SHA
    GIT_SHA=$(git rev-parse HEAD)
    
    echo -e "${YELLOW}🔐 Logging into IBM Cloud...${NC}"
    ibmcloud login --apikey "$IBM_CLOUD_API_KEY" --no-region
    ibmcloud target -r "$IBM_CLOUD_REGION" -g "$IBM_CLOUD_RESOURCE_GROUP"
    
    echo ""
    echo -e "${YELLOW}📦 Setting up Code Engine project...${NC}"
    
    # Check project status BEFORE trying to select (matches workflow logic)
    PROJECT_STATUS=$(ibmcloud ce project get --name "$PROJECT_NAME" 2>&1 || echo "")
    
    if echo "$PROJECT_STATUS" | grep -q "soft deleted"; then
        echo -e "${YELLOW}  ⚠️  Project is soft deleted. Creating new project...${NC}"
        PROJECT_NAME="${PROJECT_NAME}-$(date +%s)"
        echo -e "${YELLOW}  Using new project name: $PROJECT_NAME${NC}"
        ibmcloud ce project create --name "$PROJECT_NAME" || { echo -e "${RED}❌ Failed to create project${NC}"; exit 1; }
        ibmcloud ce project select --name "$PROJECT_NAME" || { echo -e "${RED}❌ Failed to select new project${NC}"; exit 1; }
        echo -e "${GREEN}  ✅ Using new project: $PROJECT_NAME${NC}"
    elif ibmcloud ce project get --name "$PROJECT_NAME" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✅ Project exists - selecting...${NC}"
        ibmcloud ce project select --name "$PROJECT_NAME" || { echo -e "${RED}❌ Failed to select project${NC}"; exit 1; }
    else
        echo -e "${YELLOW}  🆕 Creating new project...${NC}"
        ibmcloud ce project create --name "$PROJECT_NAME" || { echo -e "${RED}❌ Failed to create project${NC}"; exit 1; }
        ibmcloud ce project select --name "$PROJECT_NAME" || { echo -e "${RED}❌ Failed to select project${NC}"; exit 1; }
    fi
    
    echo ""
    echo -e "${YELLOW}🔑 Creating registry secret...${NC}"
    if ibmcloud ce secret get --name icr-secret > /dev/null 2>&1; then
        echo -e "${GREEN}  ✅ Registry secret already exists${NC}"
    else
        ibmcloud ce secret create --name icr-secret \
            --format registry \
            --server ${ICR_REGION}.icr.io \
            --username iamapikey \
            --password "$IBM_CLOUD_API_KEY"
        echo -e "${GREEN}  ✅ Registry secret created${NC}"
    fi
    
    # Derive app names from project name
    BACKEND_APP="rag-modulo-backend"
    FRONTEND_APP="rag-modulo-frontend"
    
    echo ""
    echo -e "${YELLOW}🚀 Deploying backend application...${NC}"
    BACKEND_IMAGE="${ICR_REGION}.icr.io/${CR_NAMESPACE}/rag-modulo-backend:${GIT_SHA}"
    
    if ibmcloud ce app get --name "$BACKEND_APP" > /dev/null 2>&1; then
        echo "  Updating existing backend..."
        ibmcloud ce app update --name "$BACKEND_APP" \
            --image "$BACKEND_IMAGE" \
            --registry-secret icr-secret \
            --min-scale 1 --max-scale 5 \
            --cpu 1 --memory 4G
    else
        echo "  Creating new backend..."
        # Note: All ENV vars here rely on .secrets and .vars being sourced above.
        ibmcloud ce app create --name "$BACKEND_APP" \
            --image "$BACKEND_IMAGE" \
            --registry-secret icr-secret \
            --min-scale 1 --max-scale 5 \
            --cpu 1 --memory 4G --port 8000 \
            --env DATABASE_URL="postgresql://${COLLECTIONDB_USER}:${COLLECTIONDB_PASS}@rag-modulo-postgres:5432/${COLLECTIONDB_NAME}?sslmode=require" \
            --env MILVUS_HOST="rag-modulo-milvus" \
            --env MILVUS_PORT="19530" \
            --env MINIO_ENDPOINT="rag-modulo-minio:9000" \
            --env MINIO_ACCESS_KEY="${MINIO_ROOT_USER:-minioadmin}" \
            --env MINIO_SECRET_KEY="${MINIO_ROOT_PASSWORD:-minioadmin}" \
            --env WATSONX_APIKEY="${WATSONX_APIKEY}" \
            --env WATSONX_INSTANCE_ID="${WATSONX_INSTANCE_ID}" \
            --env JWT_SECRET_KEY="${JWT_SECRET_KEY}" \
            --env LOG_LEVEL="INFO"
    fi
    
    echo ""
    echo -e "${YELLOW}🚀 Deploying frontend application...${NC}"
    FRONTEND_IMAGE="${ICR_REGION}.icr.io/${CR_NAMESPACE}/rag-modulo-frontend:${GIT_SHA}"
    
    # Get backend URL for frontend nginx config
    echo -e "${YELLOW}  📡 Getting backend URL...${NC}"
    BACKEND_URL=$(ibmcloud ce app get --name "$BACKEND_APP" --output json 2>/dev/null | jq -r '.status.url // empty' | head -1)
    if [ -z "$BACKEND_URL" ] || [ "$BACKEND_URL" = "null" ] || [ "$BACKEND_URL" = "" ]; then
        echo -e "${YELLOW}  ⚠️  Backend URL not available yet, using default${NC}"
        BACKEND_URL="http://localhost:8000"
    else
        echo -e "${GREEN}  ✅ Backend URL: $BACKEND_URL${NC}"
    fi
    
    # Set REACT_APP_API_URL if not already set
    REACT_APP_API_URL="${REACT_APP_API_URL:-$BACKEND_URL}"
    BACKEND_URL_FOR_NGINX="$REACT_APP_API_URL"
    
    if ibmcloud ce app get --name "$FRONTEND_APP" > /dev/null 2>&1; then
        echo "  Updating existing frontend..."
        ibmcloud ce app update --name "$FRONTEND_APP" \
            --image "$FRONTEND_IMAGE" \
            --registry-secret icr-secret \
            --min-scale 1 --max-scale 3 \
            --cpu 0.5 --memory 1G \
            --env REACT_APP_API_URL="$REACT_APP_API_URL" \
            --env BACKEND_URL="$BACKEND_URL_FOR_NGINX"
    else
        echo "  Creating new frontend..."
        ibmcloud ce app create --name "$FRONTEND_APP" \
            --image "$FRONTEND_IMAGE" \
            --registry-secret icr-secret \
            --min-scale 1 --max-scale 3 \
            --cpu 0.5 --memory 1G --port 8080 \
            --env REACT_APP_API_URL="$REACT_APP_API_URL" \
            --env BACKEND_URL="$BACKEND_URL_FOR_NGINX"
    fi
    
    echo ""
    echo -e "${GREEN}✅ Deployment complete!${NC}"
    echo ""
    echo -e "${YELLOW}📊 Application Status:${NC}"
    ibmcloud ce app get --name "$BACKEND_APP"
    echo ""
    ibmcloud ce app get --name "$FRONTEND_APP"
}

# Test teardown workflow
test_teardown() {
    print_banner "Testing Teardown Workflow with act"
    
    echo -e "${YELLOW}Running teardown workflow...${NC}"
    echo "This will:"
    echo "  1. Select Code Engine project"
    echo "  2. Delete backend application"
    echo "  3. Delete frontend application"
    echo "  4. Optionally delete the project"
    echo ""
    
    act workflow_dispatch \
        -W .github/workflows/teardown_code_engine.yml \
        --var-file "$VARS_FILE" \
        --secret-file "$SECRETS_FILE" \
        --container-architecture "$ACT_PLATFORM" \
        --input confirmation=DELETE \
        --input environment=dev \
        --input delete_project=false
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ Teardown workflow completed successfully${NC}"
    else
        echo ""
        echo -e "${RED}❌ Teardown workflow failed${NC}"
        exit 1
    fi
}

# Cleanup IBM Cloud resources manually
cleanup_resources() {
    print_banner "Cleaning Up IBM Cloud Resources"
    
    # Source IBM Cloud API key
    if [ -f "$SECRETS_FILE" ]; then
        source "$SECRETS_FILE"
    fi
    
    if [ -z "$IBM_CLOUD_API_KEY" ]; then
        echo -e "${RED}❌ IBM_CLOUD_API_KEY not set in .secrets${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}🔐 Logging into IBM Cloud...${NC}"
    ibmcloud login --apikey "$IBM_CLOUD_API_KEY" --no-region
    # Note: Assuming default region/group here for simplicity, but user can change
    # this to match their configured environment if needed.
    ibmcloud target -r us-south -g rag-modulo-deployment
    
    echo ""
    echo -e "${YELLOW}📋 Current Code Engine projects:${NC}"
    ibmcloud ce project list
    
    echo ""
    read -p "Delete project 'rag-modulo-dev'? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}🗑️  Deleting project...${NC}"
        ibmcloud ce project delete --name rag-modulo-dev --force --hard
        echo -e "${GREEN}✅ Project deleted${NC}"
    else
        echo -e "${YELLOW}ℹ️  Skipping project deletion${NC}"
    fi
}

# Show help
show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build         - Build and push images to IBM Cloud Container Registry"
    echo "  deploy        - Test deployment workflow with act"
    echo "  deploy-direct - Deploy directly via IBM Cloud CLI (bypasses act)"
    echo "  teardown      - Test teardown workflow with act"
    echo "  cleanup       - Manually cleanup IBM Cloud resources"
    echo "  full          - Run complete test cycle (build + deploy + teardown)"
    echo "  help          - Show this help message"
    echo ""
    echo "Prerequisites:"
    echo "  - .vars file with IBM Cloud configuration"
    echo "  - .secrets file with IBM Cloud API key and secrets"
    echo "  - act installed (brew install act)"
    echo "  - Docker running"
    echo ""
    echo "Examples:"
    echo "  $0 build              # Build and push images"
    echo "  $0 deploy             # Test deployment with act"
    echo "  $0 deploy-direct      # Deploy directly (no act, no Docker Hub rate limits)"
    echo "  $0 full               # Complete test cycle"
    echo ""
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    case "${1:-help}" in
        build)
            check_prerequisites
            build_and_push
            ;;
        deploy)
            check_prerequisites
            test_deploy
            ;;
        deploy-direct)
            deploy_direct
            ;;
        teardown)
            check_prerequisites
            test_teardown
            ;;
        cleanup)
            cleanup_resources
            ;;
        full)
            check_prerequisites
            
            print_banner "Complete Test Cycle"
            
            echo -e "${BLUE}Step 1/3: Build and push images${NC}"
            build_and_push
            
            echo ""
            echo -e "${BLUE}Step 2/3: Deploy applications${NC}"
            test_deploy
            
            echo ""
            read -p "Deploy complete. Test teardown? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo -e "${BLUE}Step 3/3: Teardown applications${NC}"
                test_teardown
            else
                echo -e "${YELLOW}ℹ️  Skipping teardown${NC}"
            fi
            
            echo ""
            print_banner "Test Cycle Complete"
            ;;
        help|*)
            show_help
            ;;
    esac
}

main "$@"

# Made with Bob