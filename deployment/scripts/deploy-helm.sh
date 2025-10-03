#!/bin/bash
# Helm deployment script for RAG Modulo
# Usage: ./deploy-helm.sh [dev|staging|prod] [install|upgrade]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-dev}"
ACTION="${2:-install}"
RELEASE_NAME="rag-modulo"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELM_CHART_DIR="${SCRIPT_DIR}/../helm/rag-modulo"

# Set namespace and values file based on environment
case $ENVIRONMENT in
  dev)
    NAMESPACE="rag-modulo-dev"
    VALUES_FILE="${HELM_CHART_DIR}/values-dev.yaml"
    ;;
  staging)
    NAMESPACE="rag-modulo-staging"
    VALUES_FILE="${HELM_CHART_DIR}/values-staging.yaml"
    ;;
  prod)
    NAMESPACE="rag-modulo"
    VALUES_FILE="${HELM_CHART_DIR}/values-prod.yaml"
    ;;
  *)
    echo -e "${RED}Invalid environment: $ENVIRONMENT${NC}"
    echo "Usage: $0 [dev|staging|prod] [install|upgrade]"
    exit 1
    ;;
esac

echo -e "${GREEN}Deploying RAG Modulo using Helm${NC}"
echo -e "${GREEN}Environment: ${ENVIRONMENT}${NC}"
echo -e "${GREEN}Namespace: ${NAMESPACE}${NC}"
echo -e "${GREEN}Action: ${ACTION}${NC}"

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"
if ! command -v helm &> /dev/null; then
    echo -e "${RED}Helm not found. Please install Helm 3.${NC}"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}kubectl not found. Please install kubectl.${NC}"
    exit 1
fi

# Check Helm version
HELM_VERSION=$(helm version --short | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+')
if [[ ! $HELM_VERSION =~ ^v3\. ]]; then
    echo -e "${RED}Helm 3.x is required. Current version: $HELM_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Helm $HELM_VERSION${NC}"
echo -e "${GREEN}✓ kubectl configured${NC}"

# Lint Helm chart
echo -e "\n${YELLOW}Linting Helm chart...${NC}"
helm lint ${HELM_CHART_DIR}
echo -e "${GREEN}✓ Helm chart linting passed${NC}"

# Create namespace
echo -e "\n${YELLOW}Creating namespace...${NC}"
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✓ Namespace created/verified${NC}"

# Create secrets from .env file if exists
if [ -f "${SCRIPT_DIR}/../../.env" ]; then
    echo -e "\n${YELLOW}Creating secrets from .env file...${NC}"
    kubectl create secret generic rag-modulo-secrets \
        --from-env-file="${SCRIPT_DIR}/../../.env" \
        --namespace=${NAMESPACE} \
        --dry-run=client -o yaml | kubectl apply -f -
    echo -e "${GREEN}✓ Secrets created${NC}"
else
    echo -e "${YELLOW}⚠️  No .env file found.${NC}"
    echo -e "${YELLOW}⚠️  Make sure secrets are created before deployment!${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Perform Helm deployment
case $ACTION in
  install)
    echo -e "\n${YELLOW}Installing Helm chart...${NC}"
    helm install ${RELEASE_NAME} ${HELM_CHART_DIR} \
        --namespace ${NAMESPACE} \
        --values ${VALUES_FILE} \
        --create-namespace \
        --wait \
        --timeout 10m
    echo -e "${GREEN}✓ Helm chart installed${NC}"
    ;;
  upgrade)
    echo -e "\n${YELLOW}Upgrading Helm chart...${NC}"
    helm upgrade ${RELEASE_NAME} ${HELM_CHART_DIR} \
        --namespace ${NAMESPACE} \
        --values ${VALUES_FILE} \
        --wait \
        --timeout 10m
    echo -e "${GREEN}✓ Helm chart upgraded${NC}"
    ;;
  *)
    echo -e "${RED}Invalid action: $ACTION${NC}"
    echo "Valid actions: install, upgrade"
    exit 1
    ;;
esac

# Display deployment status
echo -e "\n${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Helm Deployment Complete!             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}Helm Release Status:${NC}"
helm status ${RELEASE_NAME} -n ${NAMESPACE}

echo -e "\n${YELLOW}Deployment Resources:${NC}"
echo -e "\n${YELLOW}Pods:${NC}"
kubectl get pods -n ${NAMESPACE}

echo -e "\n${YELLOW}Services:${NC}"
kubectl get svc -n ${NAMESPACE}

echo -e "\n${YELLOW}Ingress:${NC}"
kubectl get ingress -n ${NAMESPACE} 2>/dev/null || kubectl get routes -n ${NAMESPACE} 2>/dev/null || echo "No ingress/routes found"

echo -e "\n${YELLOW}HPA (if enabled):${NC}"
kubectl get hpa -n ${NAMESPACE} 2>/dev/null || echo "No HPA configured"

echo -e "\n${YELLOW}Useful Commands:${NC}"
echo "  Check status:    helm status ${RELEASE_NAME} -n ${NAMESPACE}"
echo "  View values:     helm get values ${RELEASE_NAME} -n ${NAMESPACE}"
echo "  Rollback:        helm rollback ${RELEASE_NAME} -n ${NAMESPACE}"
echo "  Uninstall:       helm uninstall ${RELEASE_NAME} -n ${NAMESPACE}"
echo ""
echo "  Backend logs:    kubectl logs -f deployment/rag-modulo-backend -n ${NAMESPACE}"
echo "  Frontend logs:   kubectl logs -f deployment/rag-modulo-frontend -n ${NAMESPACE}"
echo ""
echo "  Port forward:    kubectl port-forward svc/backend-service 8000:8000 -n ${NAMESPACE}"

echo -e "\n${GREEN}Deployment completed successfully!${NC}"
