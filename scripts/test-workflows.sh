#!/bin/bash
# Test GitHub Actions workflows locally before pushing
#
# Usage:
#   ./scripts/test-workflows.sh           # Test all workflows
#   ./scripts/test-workflows.sh ci        # Test only CI workflow
#   ./scripts/test-workflows.sh code-engine  # Test only Code Engine workflow

set -e

WORKFLOW_DIR=".github/workflows"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo -e "${RED}❌ 'act' is not installed${NC}"
    echo ""
    echo "Install act:"
    echo "  macOS:  brew install act"
    echo "  Linux:  curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"
    echo ""
    echo "Documentation: https://github.com/nektos/act"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🧪 Testing GitHub Actions Workflows Locally${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Test function
test_workflow() {
    local workflow_file=$1
    local workflow_name=$2
    local event_type=$3

    echo -e "${YELLOW}📋 Testing: ${workflow_name}${NC}"
    echo "   Workflow: ${workflow_file}"
    echo "   Event: ${event_type}"
    echo ""

    if act ${event_type} -W ${workflow_file} --list > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ${workflow_name} - syntax valid${NC}"
        return 0
    else
        echo -e "${RED}❌ ${workflow_name} - syntax error${NC}"
        return 1
    fi
}

# Track results
total=0
passed=0
failed=0

# Test CI workflow
if [ "$1" == "" ] || [ "$1" == "ci" ]; then
    total=$((total + 1))
    if test_workflow "${WORKFLOW_DIR}/ci.yml" "CI/CD Pipeline" "pull_request"; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
    fi
    echo ""
fi

# Test Publish workflow
if [ "$1" == "" ] || [ "$1" == "publish" ]; then
    total=$((total + 1))
    if test_workflow "${WORKFLOW_DIR}/publish.yml" "Build and Publish" "push"; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
    fi
    echo ""
fi

# Test IBM Code Engine workflow
if [ "$1" == "" ] || [ "$1" == "code-engine" ]; then
    total=$((total + 1))
    if test_workflow "${WORKFLOW_DIR}/ibm-code-engine-staging.yml" "IBM Code Engine Staging" "workflow_dispatch"; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
    fi
    echo ""
fi

# Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Test Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "Total:  ${total}"
echo -e "Passed: ${GREEN}${passed}${NC}"
echo -e "Failed: ${RED}${failed}${NC}"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✅ All workflow validations passed!${NC}"
    echo -e "${GREEN}🚀 Safe to push to GitHub${NC}"
    exit 0
else
    echo -e "${RED}❌ Some workflow validations failed${NC}"
    echo -e "${RED}🛠️  Fix errors before pushing${NC}"
    exit 1
fi
