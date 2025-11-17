#!/bin/bash
# View Code Engine logs
# Run this from your Mac where ibmcloud CLI is installed

set -e

# Colors
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load configuration
SECRETS_FILE="${PROJECT_ROOT}/.secrets"
if [ -f "$SECRETS_FILE" ]; then
    source "$SECRETS_FILE"
fi

PROJECT_NAME="${CODE_ENGINE_PROJECT:-rag-modulo}"

echo -e "${BLUE}Code Engine Logs${NC}"
echo ""

# Select project
ibmcloud ce project select --name "$PROJECT_NAME" 2>/dev/null || {
    echo "Project not found. Available projects:"
    ibmcloud ce project list
    exit 1
}

# Get log tail count (default 50)
TAIL_COUNT="${1:-50}"

echo -e "${YELLOW}Backend Logs (last $TAIL_COUNT lines):${NC}"
ibmcloud ce app logs --app rag-modulo-backend --tail "$TAIL_COUNT" 2>/dev/null || echo "Backend app not found"

echo ""
echo -e "${YELLOW}Frontend Logs (last $TAIL_COUNT lines):${NC}"
ibmcloud ce app logs --app rag-modulo-frontend --tail "$TAIL_COUNT" 2>/dev/null || echo "Frontend app not found"

echo ""
echo "To follow logs in real-time, use:"
echo "  ibmcloud ce app logs --app rag-modulo-backend --follow"
echo "  ibmcloud ce app logs --app rag-modulo-frontend --follow"
