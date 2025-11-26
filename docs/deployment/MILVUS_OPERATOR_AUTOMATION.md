# Milvus Operator Deployment Automation

## Overview

RAG Modulo now supports automated deployment of Milvus via the Milvus Operator on OpenShift (ROKS). This provides production-grade vector database management with high availability, automated scaling, and simplified operations.

## Architecture

### Deployment Modes

1. **Development Mode**: Embedded Milvus (Helm subchart)
   - Quick setup for local development
   - Single standalone instance
   - Not recommended for production

2. **Production Mode** (RECOMMENDED): Milvus Operator
   - Operator-managed Milvus cluster
   - High availability with 3 etcd replicas
   - Distributed MinIO storage
   - Automatic SCC management for OpenShift

## Quick Start

### Prerequisites

- IBM Cloud CLI (`ibmcloud`) configured
- OpenShift CLI (`oc`) logged into ROKS cluster
- Helm 3.x installed
- kubectl configured with cluster access

### One-Command Deployment

```bash
# Deploy everything (Milvus Operator + RAG Modulo app)
ansible-playbook deployment/ansible/playbooks/deploy-roks-milvus-operator.yml \
  -e target_env=dev \
  -e project_version=0.8.0
```

This single command will:

1. Install Milvus Operator with proper SCC permissions
2. Deploy Milvus cluster via Custom Resource
3. Deploy RAG Modulo application
4. Configure all connections automatically

## Manual Step-by-Step Deployment

### 1. Install Milvus Operator

```bash
# Create operator namespace
oc create namespace milvus-operator

# Create SCC management ClusterRole
oc apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: milvus-operator-scc-manager
rules:
- apiGroups:
  - security.openshift.io
  resources:
  - securitycontextconstraints
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
  - delete
  - use
EOF

# Grant SCC permissions
oc adm policy add-cluster-role-to-user milvus-operator-scc-manager \
  -z milvus-operator -n milvus-operator

oc adm policy add-scc-to-user anyuid \
  -z milvus-operator -n milvus-operator

# Install operator via Helm
helm repo add milvus-operator https://zilliztech.github.io/milvus-operator/
helm repo update milvus-operator

helm upgrade --install milvus-operator \
  milvus-operator/milvus-operator \
  -n milvus-operator \
  --create-namespace \
  --wait \
  --timeout 10m
```

### 2. Deploy Milvus Cluster

```bash
# Create application namespace
oc create namespace rag-modulo

# Grant SCC to application namespace
oc adm policy add-scc-to-user anyuid -z default -n rag-modulo

# Deploy Milvus cluster
oc apply -f - <<EOF
apiVersion: milvus.io/v1beta1
kind: Milvus
metadata:
  name: my-release
  namespace: rag-modulo
  labels:
    app: milvus
spec:
  mode: cluster
  components:
    image: milvusdb/milvus:v2.6.0
  config: {}
  dependencies:
    msgStreamType: woodpecker
    etcd:
      inCluster:
        deletionPolicy: Retain
        values:
          replicaCount: 3
          persistence:
            size: 10Gi
    storage:
      inCluster:
        deletionPolicy: Retain
        values:
          mode: distributed
          persistence:
            size: 100Gi
EOF

# Wait for Milvus to be healthy
oc wait --for=jsonpath='{.status.status}'=Healthy \
  milvus/my-release -n rag-modulo --timeout=10m
```

### 3. Deploy RAG Modulo Application

```bash
helm upgrade --install rag-modulo \
  deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --create-namespace \
  --set image.backend.repository=ghcr.io/manavgup/rag_modulo/backend \
  --set image.backend.tag=0.8.0 \
  --set image.frontend.repository=ghcr.io/manavgup/rag_modulo/frontend \
  --set image.frontend.tag=0.8.0 \
  --set milvus.enabled=false \
  --set milvus.external.enabled=true \
  --set milvus.external.host=my-release-milvus-proxy.rag-modulo.svc.cluster.local \
  --set milvus.external.port=19530 \
  --timeout 15m \
  --wait
```

## Configuration

### Helm Values for External Milvus

```yaml
milvus:
  # Disable embedded Milvus
  enabled: false

  # Configure external Milvus (operator-managed)
  external:
    enabled: true
    host: my-release-milvus-proxy.rag-modulo.svc.cluster.local
    port: 19530
    user: ""  # Optional auth
    password: ""  # Optional auth
```

### Environment-Specific Variables

#### Development

```yaml
milvus_mode: standalone
etcd_storage_size: 10Gi
minio_storage_size: 100Gi
```

#### Production

```yaml
milvus_mode: cluster
etcd_storage_size: 50Gi
minio_storage_size: 1Ti
```

## Verification

### Check Milvus Operator Status

```bash
# Operator pod
oc get pods -n milvus-operator

# Operator logs
oc logs -n milvus-operator -l app.kubernetes.io/name=milvus-operator
```

### Check Milvus Cluster Status

```bash
# Milvus Custom Resource status
oc get milvus my-release -n rag-modulo

# Milvus pods
oc get pods -n rag-modulo -l app=milvus

# Milvus service
oc get svc -n rag-modulo -l app=milvus
```

### Check Application Status

```bash
# Application pods
oc get pods -n rag-modulo -l app.kubernetes.io/name=backend
oc get pods -n rag-modulo -l app.kubernetes.io/name=frontend

# Application route
oc get route -n rag-modulo
```

### Test Milvus Connectivity

```bash
# Port-forward to Milvus proxy
oc port-forward -n rag-modulo svc/my-release-milvus-proxy 19530:19530

# Test connection (from another terminal)
python3 -c "
from pymilvus import connections
connections.connect(host='localhost', port='19530')
print('Milvus connection successful!')
"
```

## Troubleshooting

### Milvus Operator Not Starting

```bash
# Check SCC permissions
oc get rolebinding -n milvus-operator | grep scc
oc get clusterrolebinding | grep milvus-operator-scc

# Grant SCC if missing
oc adm policy add-scc-to-user anyuid -z milvus-operator -n milvus-operator
```

### Milvus Cluster Stuck in Pending

```bash
# Check Milvus CR status
oc describe milvus my-release -n rag-modulo

# Check for SCC issues
oc get events -n rag-modulo --sort-by='.lastTimestamp' | grep -i scc

# Grant SCC to default service account
oc adm policy add-scc-to-user anyuid -z default -n rag-modulo
```

### Milvus Pods Crashing (OOMKilled)

```bash
# Increase memory limits in Milvus CR
oc edit milvus my-release -n rag-modulo

# Update resources section:
spec:
  components:
    resources:
      limits:
        memory: 4Gi  # Increase from 2Gi
      requests:
        memory: 2Gi  # Increase from 1Gi
```

### Backend Cannot Connect to Milvus

```bash
# Verify Milvus service endpoint
oc get svc -n rag-modulo -l app=milvus

# Check backend logs
oc logs -n rag-modulo -l app.kubernetes.io/name=backend --tail=100 | grep -i milvus

# Test connectivity from backend pod
oc exec -it -n rag-modulo deployment/rag-modulo-backend -- \
  curl -v telnet://my-release-milvus-proxy:19530
```

## Ansible Playbook Variables

### Required Variables

```yaml
target_env: dev | prod
project_version: "0.8.0"
```

### Optional Variables

```yaml
# Namespace configuration
app_namespace: "rag-modulo"
milvus_operator_namespace: "milvus-operator"

# Milvus configuration
milvus_version: "v2.6.0"
milvus_cluster_name: "my-release"
milvus_mode: "cluster"  # or "standalone"

# Storage sizes
etcd_storage_size: "10Gi"
minio_storage_size: "100Gi"

# Image registry
image_registry: "ghcr.io/manavgup/rag_modulo"
```

### Example Usage

```bash
# Development deployment
ansible-playbook deployment/ansible/playbooks/deploy-roks-milvus-operator.yml \
  -e target_env=dev \
  -e project_version=0.8.0 \
  -e milvus_mode=standalone \
  -e etcd_storage_size=5Gi \
  -e minio_storage_size=50Gi

# Production deployment
ansible-playbook deployment/ansible/playbooks/deploy-roks-milvus-operator.yml \
  -e target_env=prod \
  -e project_version=0.8.0 \
  -e milvus_mode=cluster \
  -e etcd_storage_size=50Gi \
  -e minio_storage_size=1Ti
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to ROKS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: |
          pip install ansible
          curl -LO https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz
          tar xzf openshift-client-linux.tar.gz
          sudo mv oc kubectl /usr/local/bin/

      - name: Login to OpenShift
        env:
          OPENSHIFT_SERVER: ${{ secrets.OPENSHIFT_SERVER }}
          OPENSHIFT_TOKEN: ${{ secrets.OPENSHIFT_TOKEN }}
        run: |
          oc login --token=$OPENSHIFT_TOKEN --server=$OPENSHIFT_SERVER

      - name: Deploy RAG Modulo
        run: |
          ansible-playbook deployment/ansible/playbooks/deploy-roks-milvus-operator.yml \
            -e target_env=prod \
            -e project_version=${{ github.sha }}
```

## Best Practices

1. **Use External Mode for Production**: Always use `milvus.enabled=false` and `milvus.external.enabled=true` with operator-managed Milvus

2. **Size Storage Appropriately**:
   - Dev: etcd=10Gi, MinIO=100Gi
   - Prod: etcd=50Gi+, MinIO=1Ti+

3. **Enable Monitoring**: Use Milvus Operator's built-in Prometheus integration

4. **Backup Configuration**: Configure retention policies for etcd and MinIO backups

5. **SCC Automation**: Use Helm pre-install hooks for automated SCC setup in CI/CD

## References

- [Milvus Operator Documentation](https://milvus.io/docs/install_cluster-milvusoperator.md)
- [OpenShift Security Context Constraints](https://docs.openshift.com/container-platform/4.12/authentication/managing-security-context-constraints.html)
- [RAG Modulo Helm Chart](deployment/helm/rag-modulo/README.md)
