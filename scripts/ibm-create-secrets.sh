#!/bin/bash
# Create IBM Code Engine secrets from .env file
#
# Usage: ./scripts/ibm-create-secrets.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔐 Creating IBM Code Engine Secrets from .env${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo "Please create .env file first"
    exit 1
fi

# Load .env
set -a
source .env
set +a

echo -e "${YELLOW}📋 Loaded environment variables from .env${NC}"
echo ""

# Check if logged in to IBM Cloud
if ! ibmcloud target &> /dev/null; then
    echo -e "${RED}❌ Not logged in to IBM Cloud${NC}"
    echo "Please run: ibmcloud login --sso"
    exit 1
fi

# Check if Code Engine project is selected
if ! ibmcloud code-engine project current &> /dev/null; then
    echo -e "${RED}❌ No Code Engine project selected${NC}"
    echo "Please run: ibmcloud code-engine project select --name <project-name>"
    exit 1
fi

echo -e "${BLUE}Creating application secrets...${NC}"
echo ""

# Create or update the secret
ibmcloud code-engine secret create \
  --name rag-modulo-secrets \
  --from-literal COLLECTIONDB_HOST="${COLLECTIONDB_HOST}" \
  --from-literal COLLECTIONDB_PORT="${COLLECTIONDB_PORT}" \
  --from-literal COLLECTIONDB_NAME="${COLLECTIONDB_NAME}" \
  --from-literal COLLECTIONDB_USER="${COLLECTIONDB_USER}" \
  --from-literal COLLECTIONDB_PASSWORD="${COLLECTIONDB_PASS}" \
  --from-literal VECTOR_DB="${VECTOR_DB}" \
  --from-literal MILVUS_HOST="${MILVUS_HOST}" \
  --from-literal MILVUS_PORT="${MILVUS_PORT}" \
  --from-literal JWT_SECRET_KEY="${JWT_SECRET_KEY}" \
  --from-literal WATSONX_APIKEY="${WATSONX_APIKEY}" \
  --from-literal WATSONX_URL="${WATSONX_URL}" \
  --from-literal WATSONX_INSTANCE_ID="${WATSONX_INSTANCE_ID}" \
  --from-literal OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
  --from-literal ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
  --from-literal LLM_PROVIDER="${LLM_PROVIDER}" \
  --from-literal RAG_LLM="${RAG_LLM}" \
  --from-literal EMBEDDING_MODEL="${EMBEDDING_MODEL}" \
  --from-literal LOG_LEVEL="${LOG_LEVEL}" \
  --from-literal SKIP_AUTH="${SKIP_AUTH}" \
  2>&1 | grep -v "secret exists" || \
ibmcloud code-engine secret update \
  --name rag-modulo-secrets \
  --from-literal COLLECTIONDB_HOST="${COLLECTIONDB_HOST}" \
  --from-literal COLLECTIONDB_PORT="${COLLECTIONDB_PORT}" \
  --from-literal COLLECTIONDB_NAME="${COLLECTIONDB_NAME}" \
  --from-literal COLLECTIONDB_USER="${COLLECTIONDB_USER}" \
  --from-literal COLLECTIONDB_PASSWORD="${COLLECTIONDB_PASS}" \
  --from-literal VECTOR_DB="${VECTOR_DB}" \
  --from-literal MILVUS_HOST="${MILVUS_HOST}" \
  --from-literal MILVUS_PORT="${MILVUS_PORT}" \
  --from-literal JWT_SECRET_KEY="${JWT_SECRET_KEY}" \
  --from-literal WATSONX_APIKEY="${WATSONX_APIKEY}" \
  --from-literal WATSONX_URL="${WATSONX_URL}" \
  --from-literal WATSONX_INSTANCE_ID="${WATSONX_INSTANCE_ID}" \
  --from-literal OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
  --from-literal ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
  --from-literal LLM_PROVIDER="${LLM_PROVIDER}" \
  --from-literal RAG_LLM="${RAG_LLM}" \
  --from-literal EMBEDDING_MODEL="${EMBEDDING_MODEL}" \
  --from-literal LOG_LEVEL="${LOG_LEVEL}" \
  --from-literal SKIP_AUTH="${SKIP_AUTH}"

echo ""
echo -e "${GREEN}✅ Secrets created/updated successfully!${NC}"
echo ""

# Verify
echo -e "${BLUE}📋 Verifying secret...${NC}"
ibmcloud code-engine secret get --name rag-modulo-secrets

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Done! Secrets are ready to use in Code Engine${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
