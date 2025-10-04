#!/bin/bash
# Complete IBM Cloud OpenShift infrastructure setup for RAG Modulo
# This script creates everything from scratch:
# - Resource group
# - VPC with subnets
# - Cloud Object Storage (for OpenShift registry)
# - OpenShift cluster
# - Then deploys the application using Helm

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="${1:-rag-modulo}"
ENVIRONMENT="${2:-staging}"
REGION="${3:-ca-tor}"
ZONE="${4:-ca-tor-1}"
WORKERS="${5:-2}"
FLAVOR="${6:-bx2.4x16}"

# Derived names
RESOURCE_GROUP="${PROJECT_NAME}-${ENVIRONMENT}"
VPC_NAME="${PROJECT_NAME}-${ENVIRONMENT}-vpc"
SUBNET_NAME="${PROJECT_NAME}-${ENVIRONMENT}-subnet"
CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
COS_INSTANCE="rag-modulo-cos"  # Fixed name to avoid prompts

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🚀 RAG Modulo - OpenShift Infrastructure Setup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Project:        ${NC}${PROJECT_NAME}"
echo -e "${BLUE}Environment:    ${NC}${ENVIRONMENT}"
echo -e "${BLUE}Region:         ${NC}${REGION}"
echo -e "${BLUE}Zone:           ${NC}${ZONE}"
echo -e "${BLUE}Workers:        ${NC}${WORKERS}"
echo -e "${BLUE}Worker Flavor:  ${NC}${FLAVOR} (4 vCPU, 16GB RAM)"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if IBM_CLOUD_API_KEY is set
if [ -z "$IBM_CLOUD_API_KEY" ]; then
    echo -e "${RED}❌ IBM_CLOUD_API_KEY environment variable not set${NC}"
    echo "Set it with: export IBM_CLOUD_API_KEY='your-api-key'"
    exit 1
fi

# Step 1: Login to IBM Cloud
echo -e "${YELLOW}Step 1: Logging in to IBM Cloud...${NC}"
ibmcloud login --apikey "$IBM_CLOUD_API_KEY" -r "$REGION" -q

# Step 2: Create Resource Group
echo ""
echo -e "${YELLOW}Step 2: Creating resource group '${RESOURCE_GROUP}'...${NC}"
if ibmcloud resource group "$RESOURCE_GROUP" &>/dev/null; then
    echo -e "${GREEN}✓ Resource group already exists${NC}"
else
    ibmcloud resource group-create "$RESOURCE_GROUP"
    echo -e "${GREEN}✓ Resource group created${NC}"
fi

# Target the resource group
ibmcloud target -g "$RESOURCE_GROUP"

# Step 3: Create VPC
echo ""
echo -e "${YELLOW}Step 3: Creating VPC '${VPC_NAME}'...${NC}"
VPC_ID=$(ibmcloud is vpcs --output json | jq -r ".[] | select(.name==\"$VPC_NAME\") | .id")
if [ -n "$VPC_ID" ] && [ "$VPC_ID" != "null" ]; then
    echo -e "${GREEN}✓ VPC already exists (ID: $VPC_ID)${NC}"
else
    VPC_ID=$(ibmcloud is vpc-create "$VPC_NAME" --resource-group-name "$RESOURCE_GROUP" --output json | jq -r '.id')
    echo -e "${GREEN}✓ VPC created (ID: $VPC_ID)${NC}"
fi

# Step 4: Create Subnet
echo ""
echo -e "${YELLOW}Step 4: Creating subnet '${SUBNET_NAME}'...${NC}"
SUBNET_ID=$(ibmcloud is subnets --output json | jq -r ".[] | select(.name==\"$SUBNET_NAME\") | .id")
if [ -n "$SUBNET_ID" ] && [ "$SUBNET_ID" != "null" ]; then
    echo -e "${GREEN}✓ Subnet already exists (ID: $SUBNET_ID)${NC}"
else
    # Create subnet with appropriate CIDR
    SUBNET_ID=$(ibmcloud is subnet-create "$SUBNET_NAME" "$VPC_ID" \
        --ipv4-address-count 256 \
        --zone "$ZONE" \
        --resource-group-name "$RESOURCE_GROUP" \
        --output json | jq -r '.id')
    echo -e "${GREEN}✓ Subnet created (ID: $SUBNET_ID)${NC}"
fi

# Step 5: Create Cloud Object Storage instance (required for OpenShift registry backup)
echo ""
echo -e "${YELLOW}Step 5: Creating Cloud Object Storage instance...${NC}"
COS_CRN=$(ibmcloud resource service-instances --service-name cloud-object-storage --output json | \
    jq -r ".[] | select(.name==\"$COS_INSTANCE\") | .crn")

if [ -n "$COS_CRN" ] && [ "$COS_CRN" != "null" ]; then
    echo -e "${GREEN}✓ COS instance already exists${NC}"
else
    # Create COS instance with standard plan (required for OpenShift)
    # Note: This uses paid plan (~$0.02/GB/month for storage)
    ibmcloud resource service-instance-create "$COS_INSTANCE" \
        cloud-object-storage standard global \
        -p '{"HMAC":true}' \
        -g "$RESOURCE_GROUP"

    # Wait for COS to be created
    sleep 10

    # Get the CRN
    COS_CRN=$(ibmcloud resource service-instances --service-name cloud-object-storage --output json | \
        jq -r ".[] | select(.name==\"$COS_INSTANCE\") | .crn")
    echo -e "${GREEN}✓ COS instance created${NC}"
fi

echo -e "${BLUE}COS CRN: ${NC}$COS_CRN"

# Step 6: Check if cluster already exists
echo ""
echo -e "${YELLOW}Step 6: Checking if cluster exists...${NC}"
CLUSTER_EXISTS=$(ibmcloud ks cluster ls --output json | jq -r ".[] | select(.name==\"$CLUSTER_NAME\") | .name")

if [ -n "$CLUSTER_EXISTS" ]; then
    echo -e "${GREEN}✓ Cluster '$CLUSTER_NAME' already exists${NC}"
    echo -e "${YELLOW}Skipping cluster creation. Use existing cluster.${NC}"

    # Get cluster state
    CLUSTER_STATE=$(ibmcloud ks cluster get --cluster "$CLUSTER_NAME" --output json | jq -r '.state')
    echo -e "${BLUE}Cluster state: ${NC}$CLUSTER_STATE"

    if [ "$CLUSTER_STATE" != "normal" ]; then
        echo -e "${YELLOW}⚠️  Cluster is not in 'normal' state. Current state: $CLUSTER_STATE${NC}"
        echo "Waiting for cluster to be ready..."
    fi
else
    # Step 7: Create OpenShift Cluster
    echo ""
    echo -e "${YELLOW}Step 7: Creating OpenShift cluster '${CLUSTER_NAME}'...${NC}"
    echo -e "${BLUE}This will take approximately 30-45 minutes...${NC}"

    ibmcloud ks cluster create vpc-gen2 \
        --name "$CLUSTER_NAME" \
        --version 4.15_openshift \
        --zone "$ZONE" \
        --vpc-id "$VPC_ID" \
        --subnet-id "$SUBNET_ID" \
        --flavor "$FLAVOR" \
        --workers "$WORKERS" \
        --cos-instance "$COS_CRN"

    echo -e "${GREEN}✓ Cluster creation initiated${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}⏳ Cluster is provisioning (30-45 minutes)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Monitor progress with:"
    echo "  ibmcloud ks cluster ls"
    echo "  ibmcloud ks cluster get --cluster $CLUSTER_NAME"
    echo ""
    echo "Once cluster state is 'normal', run:"
    echo "  make openshift-deploy-app CLUSTER_NAME=$CLUSTER_NAME"
    echo ""
    exit 0
fi

# Step 8: Configure kubectl/oc CLI
echo ""
echo -e "${YELLOW}Step 8: Configuring cluster access...${NC}"
ibmcloud ks cluster config --cluster "$CLUSTER_NAME" --admin

# Verify cluster access
if oc status &>/dev/null; then
    echo -e "${GREEN}✓ Cluster access configured${NC}"
else
    echo -e "${RED}❌ Failed to configure cluster access${NC}"
    exit 1
fi

# Step 9: Deploy application using Helm
echo ""
echo -e "${YELLOW}Step 9: Deploying RAG Modulo application...${NC}"

# Change to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Deploy using Makefile target
make openshift-deploy-app CLUSTER_NAME="$CLUSTER_NAME"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Infrastructure setup and deployment complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Resource Summary:${NC}"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  VPC:            $VPC_NAME ($VPC_ID)"
echo "  Subnet:         $SUBNET_NAME ($SUBNET_ID)"
echo "  COS Instance:   $COS_INSTANCE"
echo "  Cluster:        $CLUSTER_NAME"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Check deployment status:"
echo "     oc get pods -n rag-modulo-${ENVIRONMENT}"
echo ""
echo "  2. Get application URLs:"
echo "     oc get routes -n rag-modulo-${ENVIRONMENT}"
echo ""
echo "  3. View logs:"
echo "     oc logs -f deployment/rag-modulo-backend -n rag-modulo-${ENVIRONMENT}"
echo ""
