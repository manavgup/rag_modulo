#!/bin/bash
# Validate CI workflows can run locally
# This is a placeholder script for pre-commit validation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Validating CI workflows..."

# Check if act is installed (for local workflow testing)
if command -v act &> /dev/null; then
    echo -e "${GREEN}✓${NC} act is installed"

    # List workflows
    if [ -d ".github/workflows" ]; then
        workflow_count=$(ls -1 .github/workflows/*.yml 2>/dev/null | wc -l)
        echo -e "${GREEN}✓${NC} Found $workflow_count workflow files"
    else
        echo -e "${RED}✗${NC} No .github/workflows directory found"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠${NC} act is not installed (optional for local CI testing)"
    echo -e "${YELLOW}⚠${NC} Install with: brew install act (macOS) or see https://github.com/nektos/act"
fi

# Validate workflow YAML syntax
for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ]; then
        if python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Valid YAML: $(basename $workflow)"
        else
            echo -e "${RED}✗${NC} Invalid YAML: $(basename $workflow)"
            exit 1
        fi
    fi
done

echo -e "${GREEN}✓${NC} All CI workflows validated"
exit 0
