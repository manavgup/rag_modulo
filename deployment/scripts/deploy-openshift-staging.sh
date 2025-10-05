#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="rag-modulo-staging"
HELM_RELEASE="rag-modulo"
ICR_NAMESPACE="rag-modulo"
ICR_REGION="ca-tor"
REGISTRY="ca.icr.io/${ICR_NAMESPACE}"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}RAG Modulo OpenShift Staging Deployment${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Step 1: Verify prerequisites
echo -e "${YELLOW}Step 1: Verifying prerequisites...${NC}"

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}✗ kubectl not found${NC}"
    exit 1
fi

if ! command -v helm &> /dev/null; then
    echo -e "${RED}✗ helm not found${NC}"
    exit 1
fi

if ! command -v ibmcloud &> /dev/null; then
    echo -e "${RED}✗ ibmcloud CLI not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}"
echo ""

# Step 2: Delete existing namespace if it exists
echo -e "${YELLOW}Step 2: Cleaning up existing namespace...${NC}"
if kubectl get namespace $NAMESPACE &> /dev/null; then
    echo -e "${YELLOW}  Deleting namespace $NAMESPACE...${NC}"
    kubectl delete namespace $NAMESPACE --wait=true
    echo -e "${GREEN}✓ Namespace deleted${NC}"
else
    echo -e "${GREEN}✓ Namespace doesn't exist${NC}"
fi
echo ""

# Step 3: Create namespace
echo -e "${YELLOW}Step 3: Creating namespace...${NC}"
kubectl create namespace $NAMESPACE
echo -e "${GREEN}✓ Namespace created${NC}"
echo ""

# Step 4: Create secrets
echo -e "${YELLOW}Step 4: Creating secrets...${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo -e "${YELLOW}Please create .env file with required secrets${NC}"
    exit 1
fi

# Load environment variables from .env
set -a
source .env
set +a

# Create secrets
kubectl create secret generic rag-modulo-secrets \
    --namespace=$NAMESPACE \
    --from-literal=COLLECTIONDB_USER="${COLLECTIONDB_USER:-raguser}" \
    --from-literal=COLLECTIONDB_PASSWORD="${COLLECTIONDB_PASS:-ragpassword}" \
    --from-literal=MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}" \
    --from-literal=MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}" \
    --from-literal=JWT_SECRET_KEY="${JWT_SECRET_KEY:-dev-secret-key}" \
    --from-literal=WATSONX_APIKEY="${WATSONX_APIKEY:-}" \
    --from-literal=WATSONX_PROJECT_ID="${WATSONX_INSTANCE_ID:-}" \
    --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
    --from-literal=ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"

echo -e "${GREEN}✓ Secrets created${NC}"
echo ""

# Step 5: Create ConfigMap
echo -e "${YELLOW}Step 5: Creating ConfigMap...${NC}"
kubectl create configmap rag-modulo-config \
    --namespace=$NAMESPACE \
    --from-literal=COLLECTIONDB_HOST=postgresql \
    --from-literal=COLLECTIONDB_PORT=5432 \
    --from-literal=COLLECTIONDB_NAME=collectiondb \
    --from-literal=MILVUS_HOST=milvus-standalone \
    --from-literal=MILVUS_PORT=19530 \
    --from-literal=MINIO_ENDPOINT=minio:9000 \
    --from-literal=LOG_LEVEL=INFO \
    --from-literal=VECTOR_DB=milvus \
    --from-literal=EMBEDDING_MODEL=sentence-transformers/all-minilm-l6-v2 \
    --from-literal=EMBEDDING_DIM=384

echo -e "${GREEN}✓ ConfigMap created${NC}"
echo ""

# Step 6: Create ICR image pull secret
echo -e "${YELLOW}Step 6: Creating ICR image pull secret...${NC}"

# Delete existing secret if it exists
kubectl delete secret icr-secret -n $NAMESPACE 2>/dev/null || true

# Check if IBM_CLOUD_API_KEY is set
if [ -z "${IBM_CLOUD_API_KEY}" ]; then
    echo -e "${RED}✗ IBM_CLOUD_API_KEY environment variable not set${NC}"
    echo -e "${YELLOW}Please set IBM_CLOUD_API_KEY or export it from .env${NC}"
    exit 1
fi

# Use API key directly (doesn't expire like IAM tokens)
kubectl create secret docker-registry icr-secret \
    --namespace=$NAMESPACE \
    --docker-server=ca.icr.io \
    --docker-username=iamapikey \
    --docker-password="${IBM_CLOUD_API_KEY}"

echo -e "${GREEN}✓ ICR secret created${NC}"
echo ""

# Step 7: Deploy StatefulSets
echo -e "${YELLOW}Step 7: Deploying databases...${NC}"

echo -e "  Deploying PostgreSQL..."
kubectl apply -f deployment/openshift/postgresql.yaml -n $NAMESPACE

echo -e "  Deploying etcd..."
kubectl apply -f deployment/openshift/etcd.yaml -n $NAMESPACE

echo -e "  Deploying MinIO..."
kubectl apply -f deployment/openshift/minio.yaml -n $NAMESPACE

echo -e "  Deploying Milvus..."
kubectl apply -f deployment/openshift/milvus.yaml -n $NAMESPACE

echo -e "${GREEN}✓ Database deployments created${NC}"
echo ""

# Step 8: Wait for databases to be ready
echo -e "${YELLOW}Step 8: Waiting for databases to be ready...${NC}"
echo -e "  This may take 2-3 minutes..."

kubectl wait --for=condition=ready pod -l app=postgresql -n $NAMESPACE --timeout=5m || true
kubectl wait --for=condition=ready pod -l app=milvus-etcd -n $NAMESPACE --timeout=5m || true
kubectl wait --for=condition=ready pod -l app=minio -n $NAMESPACE --timeout=5m || true
kubectl wait --for=condition=ready pod -l app=milvus-standalone -n $NAMESPACE --timeout=5m || true

echo -e "${GREEN}✓ Databases are ready${NC}"
echo ""

# Step 9: Create backend service alias
echo -e "${YELLOW}Step 9: Creating backend service alias...${NC}"
kubectl apply -f deployment/openshift/backend-alias.yaml -n $NAMESPACE
echo -e "${GREEN}✓ Service alias created${NC}"
echo ""

# Step 10: Deploy application with Helm
echo -e "${YELLOW}Step 10: Deploying application with Helm...${NC}"
helm upgrade --install $HELM_RELEASE ./deployment/helm/rag-modulo \
    --namespace $NAMESPACE \
    --set images.registry=$REGISTRY \
    --set backend.replicaCount=2 \
    --set frontend.replicaCount=2 \
    --wait --timeout 10m

echo -e "${GREEN}✓ Application deployed${NC}"
echo ""

# Step 11: Create OpenShift routes
echo -e "${YELLOW}Step 11: Creating OpenShift routes...${NC}"
kubectl apply -f deployment/openshift/routes.yaml -n $NAMESPACE
echo -e "${GREEN}✓ Routes created${NC}"
echo ""

# Step 12: Verify deployment
echo -e "${YELLOW}Step 12: Verifying deployment...${NC}"
echo ""

echo -e "${CYAN}=== Pods ===${NC}"
kubectl get pods -n $NAMESPACE

echo ""
echo -e "${CYAN}=== Services ===${NC}"
kubectl get svc -n $NAMESPACE

echo ""
echo -e "${CYAN}=== Routes ===${NC}"
kubectl get routes -n $NAMESPACE

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get application URLs
FRONTEND_URL=$(kubectl get route rag-modulo-frontend -n $NAMESPACE -o jsonpath='{.spec.host}' 2>/dev/null || echo "Not found")
BACKEND_URL=$(kubectl get route rag-modulo-backend -n $NAMESPACE -o jsonpath='{.spec.host}' 2>/dev/null || echo "Not found")

echo -e "${CYAN}Application URLs:${NC}"
echo -e "  Frontend: ${GREEN}https://$FRONTEND_URL${NC}"
echo -e "  Backend:  ${GREEN}https://$BACKEND_URL${NC}"
echo ""
