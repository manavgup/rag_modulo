#!/bin/bash
# bulk-ai-assist.sh - Bulk add ai-assist label to existing issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Bulk AI-Assist Label Addition Tool${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo "Install from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: Not authenticated with GitHub CLI${NC}"
    echo "Run: gh auth login"
    exit 1
fi

echo -e "${GREEN}✓ GitHub CLI is installed and authenticated${NC}"
echo ""

# Function to show issue preview
show_issue_preview() {
    local issue_num=$1
    echo -e "${YELLOW}Preview of issue #${issue_num}:${NC}"
    gh issue view "$issue_num" --json title,body,labels --jq '
        "Title: \(.title)\n" +
        "Labels: \((.labels // [] | map(.name) | join(", ")))\n" +
        "Body (first 200 chars): \(.body[:200])..."
    ' 2>/dev/null || echo "  [Issue not found or access denied]"
    echo ""
}

# Function to check if issue already has ai-assist label
has_ai_assist_label() {
    local issue_num=$1
    gh issue view "$issue_num" --json labels --jq '.labels[].name' 2>/dev/null | grep -q "ai-assist"
}

# Mode selection
echo -e "${BLUE}Select mode:${NC}"
echo "  1) Manual list - Enter issue numbers manually"
echo "  2) Query mode - Auto-find issues by criteria"
echo "  3) Label mode - Add ai-assist to issues with specific label"
echo ""
read -p "Enter choice (1-3): " mode

case $mode in
    1)
        # Manual mode
        echo ""
        echo -e "${BLUE}Manual Mode: Enter issue numbers${NC}"
        echo "Enter issue numbers (space-separated) or 'done' to finish:"
        read -p "> " -a ISSUES
        ;;

    2)
        # Query mode
        echo ""
        echo -e "${BLUE}Query Mode: Find issues automatically${NC}"
        echo ""
        echo "Select criteria:"
        echo "  1) Open bugs"
        echo "  2) Good first issues"
        echo "  3) Help wanted"
        echo "  4) Enhancement requests"
        echo "  5) Custom label"
        echo ""
        read -p "Enter choice (1-5): " query_choice

        case $query_choice in
            1) LABEL="bug" ;;
            2) LABEL="good first issue" ;;
            3) LABEL="help wanted" ;;
            4) LABEL="enhancement" ;;
            5)
                read -p "Enter custom label: " LABEL
                ;;
            *)
                echo -e "${RED}Invalid choice${NC}"
                exit 1
                ;;
        esac

        read -p "How many issues to fetch? (max 50): " LIMIT
        LIMIT=${LIMIT:-20}

        echo ""
        echo -e "${YELLOW}Fetching issues with label '$LABEL'...${NC}"
        ISSUES=($(gh issue list --label "$LABEL" --state open --limit "$LIMIT" --json number --jq '.[].number'))

        if [ ${#ISSUES[@]} -eq 0 ]; then
            echo -e "${RED}No issues found with label '$LABEL'${NC}"
            exit 0
        fi

        echo -e "${GREEN}Found ${#ISSUES[@]} issues${NC}"
        ;;

    3)
        # Label mode
        echo ""
        read -p "Enter source label: " SOURCE_LABEL
        read -p "How many issues to process? (max 50): " LIMIT
        LIMIT=${LIMIT:-20}

        echo ""
        echo -e "${YELLOW}Fetching issues with label '$SOURCE_LABEL'...${NC}"
        ISSUES=($(gh issue list --label "$SOURCE_LABEL" --state open --limit "$LIMIT" --json number --jq '.[].number'))

        if [ ${#ISSUES[@]} -eq 0 ]; then
            echo -e "${RED}No issues found with label '$SOURCE_LABEL'${NC}"
            exit 0
        fi

        echo -e "${GREEN}Found ${#ISSUES[@]} issues${NC}"
        ;;

    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Issues to Process: ${#ISSUES[@]}${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

# Show preview of issues
echo -e "${YELLOW}Preview of first 3 issues:${NC}"
for i in {0..2}; do
    if [ $i -lt ${#ISSUES[@]} ]; then
        show_issue_preview "${ISSUES[$i]}"
    fi
done

# Confirmation
echo ""
read -p "$(echo -e ${YELLOW}Add ai-assist label to these ${#ISSUES[@]} issues? [y/N]: ${NC})" -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Aborted${NC}"
    exit 0
fi

# Process issues
echo ""
echo -e "${BLUE}Processing issues...${NC}"
echo ""

ADDED=0
SKIPPED=0
FAILED=0

for issue in "${ISSUES[@]}"; do
    # Skip comments or invalid entries
    [[ $issue =~ ^# ]] && continue
    [[ ! $issue =~ ^[0-9]+$ ]] && continue

    echo -n "Processing issue #$issue... "

    # Check if already has ai-assist label
    if has_ai_assist_label "$issue"; then
        echo -e "${YELLOW}SKIPPED (already has ai-assist)${NC}"
        ((SKIPPED++))
        continue
    fi

    # Add the label
    if gh issue edit "$issue" --add-label "ai-assist" 2>/dev/null; then
        echo -e "${GREEN}✓ ADDED${NC}"
        ((ADDED++))

        # Rate limit: wait 2 seconds between requests
        sleep 2
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED++))
    fi
done

# Summary
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✓ Added ai-assist: $ADDED${NC}"
echo -e "${YELLOW}⊘ Skipped (already labeled): $SKIPPED${NC}"
echo -e "${RED}✗ Failed: $FAILED${NC}"
echo ""

if [ $ADDED -gt 0 ]; then
    echo -e "${GREEN}Success! AI planning will start for these issues.${NC}"
    echo ""
    echo "Monitor progress:"
    echo "  gh issue list --label \"ai-assist,plan-ready\" --limit 50"
    echo ""
    echo "View issues ready for approval:"
    echo "  gh issue list --label \"plan-ready\" --limit 20"
fi

echo ""
echo -e "${BLUE}Done!${NC}"
