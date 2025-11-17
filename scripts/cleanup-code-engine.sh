#!/bin/bash
# Clean up old Code Engine projects and apps
# Run this from your Mac where ibmcloud CLI is installed

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}IBM Cloud Code Engine Cleanup${NC}"
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
fi

# List all Code Engine projects
echo -e "${YELLOW}📋 Listing Code Engine projects...${NC}"
ibmcloud ce project list
echo ""

# Ask user which project to clean up
echo -e "${YELLOW}🗑️  Cleanup Options:${NC}"
echo "1. Delete specific project"
echo "2. Clean up apps in project (keep project)"
echo "3. List resources only (no deletion)"
echo "4. Cancel"
echo ""
read -p "Select option (1-4): " option

case $option in
    1)
        read -p "Enter project name to delete: " project_to_delete
        echo -e "${YELLOW}⚠️  Are you sure you want to delete project '$project_to_delete'?${NC}"
        read -p "Type 'yes' to confirm: " confirm
        if [ "$confirm" = "yes" ]; then
            echo -e "${YELLOW}🗑️  Deleting project $project_to_delete...${NC}"
            ibmcloud ce project delete --name "$project_to_delete" --force
            echo -e "${GREEN}✅ Project deleted${NC}"
        else
            echo -e "${BLUE}Cancelled${NC}"
        fi
        ;;

    2)
        read -p "Enter project name: " project_name
        echo -e "${YELLOW}📍 Selecting project $project_name...${NC}"
        ibmcloud ce project select --name "$project_name"

        echo -e "${YELLOW}📋 Current apps:${NC}"
        ibmcloud ce app list
        echo ""

        echo -e "${YELLOW}🗑️  Delete which apps?${NC}"
        echo "1. Delete all apps"
        echo "2. Delete backend only"
        echo "3. Delete frontend only"
        echo "4. Cancel"
        read -p "Select (1-4): " app_option

        case $app_option in
            1)
                echo -e "${YELLOW}🗑️  Deleting all apps...${NC}"
                for app in $(ibmcloud ce app list -o json | jq -r '.[].name'); do
                    echo "Deleting $app..."
                    ibmcloud ce app delete --name "$app" --force
                done
                echo -e "${GREEN}✅ All apps deleted${NC}"
                ;;
            2)
                echo -e "${YELLOW}🗑️  Deleting backend apps...${NC}"
                for app in $(ibmcloud ce app list -o json | jq -r '.[].name' | grep backend); do
                    echo "Deleting $app..."
                    ibmcloud ce app delete --name "$app" --force
                done
                echo -e "${GREEN}✅ Backend apps deleted${NC}"
                ;;
            3)
                echo -e "${YELLOW}🗑️  Deleting frontend apps...${NC}"
                for app in $(ibmcloud ce app list -o json | jq -r '.[].name' | grep frontend); do
                    echo "Deleting $app..."
                    ibmcloud ce app delete --name "$app" --force
                done
                echo -e "${GREEN}✅ Frontend apps deleted${NC}"
                ;;
            *)
                echo -e "${BLUE}Cancelled${NC}"
                ;;
        esac
        ;;

    3)
        read -p "Enter project name: " project_name
        echo -e "${YELLOW}📍 Selecting project $project_name...${NC}"
        ibmcloud ce project select --name "$project_name" || {
            echo -e "${RED}❌ Project not found${NC}"
            exit 1
        }

        echo -e "${YELLOW}📋 Applications:${NC}"
        ibmcloud ce app list
        echo ""

        echo -e "${YELLOW}📋 Secrets:${NC}"
        ibmcloud ce secret list
        echo ""

        echo -e "${YELLOW}📋 Configmaps:${NC}"
        ibmcloud ce configmap list
        ;;

    *)
        echo -e "${BLUE}Cancelled${NC}"
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Cleanup Complete${NC}"
echo -e "${GREEN}========================================${NC}"
