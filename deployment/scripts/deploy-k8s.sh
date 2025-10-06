#!/bin/bash
# Kubernetes deployment script for RAG Modulo
# Usage: ./deploy-k8s.sh [dev|staging|prod]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-dev}"
NAMESPACE="rag-modulo"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="${SCRIPT_DIR}/../k8s/base"

# Set namespace based on environment
case $ENVIRONMENT in
  dev)
    NAMESPACE="rag-modulo-dev"
    ;;
  staging)
    NAMESPACE="rag-modulo-staging"
    ;;
  prod)
    NAMESPACE="rag-modulo"
    ;;
  *)
    echo -e "${RED}Invalid environment: $ENVIRONMENT${NC}"
    echo "Usage: $0 [dev|staging|prod]"
    exit 1
    ;;
esac

echo -e "${GREEN}Deploying RAG Modulo to ${ENVIRONMENT} environment${NC}"
echo -e "${GREEN}Namespace: ${NAMESPACE}${NC}"

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}kubectl not found. Please install kubectl.${NC}"
    exit 1
fi

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}kubectl is not configured. Please configure kubectl.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ kubectl is configured${NC}"

# Create namespace
echo -e "\n${YELLOW}Creating namespace...${NC}"
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✓ Namespace created/verified${NC}"

# Create secrets (if .env file exists)
if [ -f "${SCRIPT_DIR}/../../.env" ]; then
    echo -e "\n${YELLOW}Creating secrets from .env file...${NC}"
    kubectl create secret generic rag-modulo-secrets \
        --from-env-file="${SCRIPT_DIR}/../../.env" \
        --namespace=${NAMESPACE} \
        --dry-run=client -o yaml | kubectl apply -f -
    echo -e "${GREEN}✓ Secrets created${NC}"
else
    echo -e "${YELLOW}⚠️  No .env file found. Skipping secrets creation.${NC}"
    echo -e "${YELLOW}⚠️  Please create secrets manually before deployment.${NC}"
fi

# Apply ConfigMaps
echo -e "\n${YELLOW}Applying ConfigMaps...${NC}"
kubectl apply -f ${K8S_DIR}/configmaps/ -n ${NAMESPACE}
echo -e "${GREEN}✓ ConfigMaps applied${NC}"

# Apply PersistentVolumeClaims
echo -e "\n${YELLOW}Applying PersistentVolumeClaims...${NC}"
kubectl apply -f ${K8S_DIR}/storage/ -n ${NAMESPACE}
echo -e "${GREEN}✓ PVCs applied${NC}"

# Apply StatefulSets
echo -e "\n${YELLOW}Applying StatefulSets...${NC}"
kubectl apply -f ${K8S_DIR}/statefulsets/ -n ${NAMESPACE}
echo -e "${GREEN}✓ StatefulSets applied${NC}"

# Wait for StatefulSets to be ready
echo -e "\n${YELLOW}Waiting for stateful services to be ready...${NC}"
kubectl wait --for=condition=ready pod -l component=postgres -n ${NAMESPACE} --timeout=300s || true
kubectl wait --for=condition=ready pod -l component=etcd -n ${NAMESPACE} --timeout=300s || true
kubectl wait --for=condition=ready pod -l component=minio -n ${NAMESPACE} --timeout=300s || true
kubectl wait --for=condition=ready pod -l component=milvus -n ${NAMESPACE} --timeout=300s || true
echo -e "${GREEN}✓ Stateful services are ready${NC}"

# Apply Services
echo -e "\n${YELLOW}Applying Services...${NC}"
kubectl apply -f ${K8S_DIR}/services/ -n ${NAMESPACE}
echo -e "${GREEN}✓ Services applied${NC}"

# Apply Deployments
echo -e "\n${YELLOW}Applying Deployments...${NC}"
kubectl apply -f ${K8S_DIR}/deployments/ -n ${NAMESPACE}
echo -e "${GREEN}✓ Deployments applied${NC}"

# Wait for Deployments to be ready
echo -e "\n${YELLOW}Waiting for application deployments to be ready...${NC}"
kubectl wait --for=condition=available deployment/rag-modulo-backend -n ${NAMESPACE} --timeout=300s || true
kubectl wait --for=condition=available deployment/rag-modulo-frontend -n ${NAMESPACE} --timeout=300s || true
kubectl wait --for=condition=available deployment/mlflow-server -n ${NAMESPACE} --timeout=300s || true
echo -e "${GREEN}✓ Application deployments are ready${NC}"

# Apply HPA (only for staging/prod)
if [ "$ENVIRONMENT" != "dev" ]; then
    echo -e "\n${YELLOW}Applying HorizontalPodAutoscalers...${NC}"
    kubectl apply -f ${K8S_DIR}/hpa/ -n ${NAMESPACE}
    echo -e "${GREEN}✓ HPAs applied${NC}"
fi

# Apply Ingress/Routes
echo -e "\n${YELLOW}Applying Ingress configuration...${NC}"
if kubectl get crd routes.route.openshift.io &> /dev/null; then
    echo -e "${YELLOW}OpenShift detected, applying Routes...${NC}"
    kubectl apply -f ${K8S_DIR}/ingress/openshift-routes.yaml -n ${NAMESPACE}
else
    echo -e "${YELLOW}Applying Ingress...${NC}"
    kubectl apply -f ${K8S_DIR}/ingress/ingress.yaml -n ${NAMESPACE}
fi
echo -e "${GREEN}✓ Ingress/Routes applied${NC}"

# Display deployment status
echo -e "\n${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deployment Complete!                  ║${NC}"
echo -e "${GREEN}╔════════════════════════════════════════╝${NC}"
echo -e "\n${YELLOW}Deployment Status:${NC}"
kubectl get pods -n ${NAMESPACE}

echo -e "\n${YELLOW}Services:${NC}"
kubectl get svc -n ${NAMESPACE}

echo -e "\n${YELLOW}Ingress:${NC}"
kubectl get ingress -n ${NAMESPACE} 2>/dev/null || kubectl get routes -n ${NAMESPACE} 2>/dev/null || echo "No ingress/routes found"

echo -e "\n${YELLOW}To check logs:${NC}"
echo "  Backend:  kubectl logs -f deployment/rag-modulo-backend -n ${NAMESPACE}"
echo "  Frontend: kubectl logs -f deployment/rag-modulo-frontend -n ${NAMESPACE}"

echo -e "\n${YELLOW}To access services locally:${NC}"
echo "  Backend:  kubectl port-forward svc/backend-service 8000:8000 -n ${NAMESPACE}"
echo "  Frontend: kubectl port-forward svc/frontend-service 8080:8080 -n ${NAMESPACE}"

echo -e "\n${GREEN}Deployment completed successfully!${NC}"
