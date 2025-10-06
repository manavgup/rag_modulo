# Kubernetes Deployment Guide

This guide covers deploying RAG Modulo to Kubernetes and OpenShift clusters with production-ready configuration.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Options](#deployment-options)
- [Configuration](#configuration)
- [Cloud Providers](#cloud-providers)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

- **Kubernetes 1.24+** or **OpenShift 4.10+**
- **kubectl** or **oc CLI** configured
- **Helm 3.8+** (for Helm deployments)
- **Docker** (for building images)

### Optional Tools

- **cert-manager** for automatic TLS certificates
- **Prometheus** for metrics collection
- **Grafana** for visualization

### Access Requirements

- Cluster admin access or appropriate RBAC permissions
- Container registry access (GHCR, Docker Hub, or private registry)
- DNS configuration for ingress/routes

## Quick Start

### 1. Using Helm (Recommended)

```bash
# Development environment
make helm-install-dev

# Staging environment
make helm-install-staging

# Production environment
make helm-install-prod
```

### 2. Using Raw Kubernetes Manifests

```bash
# Development environment
make k8s-deploy-dev

# Staging environment
make k8s-deploy-staging

# Production environment
make k8s-deploy-prod
```

### 3. Manual Deployment

```bash
# 1. Create namespace
kubectl create namespace rag-modulo

# 2. Create secrets
kubectl create secret generic rag-modulo-secrets \
  --from-env-file=.env \
  --namespace rag-modulo

# 3. Apply manifests
kubectl apply -f deployment/k8s/base/configmaps/ -n rag-modulo
kubectl apply -f deployment/k8s/base/storage/ -n rag-modulo
kubectl apply -f deployment/k8s/base/statefulsets/ -n rag-modulo
kubectl apply -f deployment/k8s/base/services/ -n rag-modulo
kubectl apply -f deployment/k8s/base/deployments/ -n rag-modulo
kubectl apply -f deployment/k8s/base/ingress/ -n rag-modulo
kubectl apply -f deployment/k8s/base/hpa/ -n rag-modulo
```

## Deployment Options

### Option 1: Helm Chart

**Pros:**
- Easy upgrades and rollbacks
- Environment-specific configurations
- Template-based customization
- Release management

**When to Use:**
- Production deployments
- Multiple environments
- Complex configurations
- Team collaboration

**Example:**
```bash
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --values ./deployment/helm/rag-modulo/values-prod.yaml \
  --set ingress.hosts.frontend=myapp.example.com
```

### Option 2: Raw Kubernetes Manifests

**Pros:**
- Full control over resources
- No Helm dependency
- GitOps-friendly
- Simple debugging

**When to Use:**
- CI/CD pipelines
- GitOps workflows (ArgoCD, Flux)
- Simple deployments
- Learning K8s

**Example:**
```bash
./deployment/scripts/deploy-k8s.sh prod
```

### Option 3: Kustomize (Coming Soon)

Kustomize overlays for environment-specific customizations.

## Configuration

### Environment Variables

Required secrets (create from `.env` file):

```bash
# Database
COLLECTIONDB_USER=postgres
COLLECTIONDB_PASSWORD=<secure-password>

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<secure-password>
MINIO_ACCESS_KEY=<access-key>
MINIO_SECRET_KEY=<secret-key>

# JWT
JWT_SECRET_KEY=<jwt-secret>

# LLM Providers
WATSONX_APIKEY=<watsonx-key>
WATSONX_URL=<watsonx-url>
WATSONX_PROJECT_ID=<project-id>
OPENAI_API_KEY=<openai-key>
ANTHROPIC_API_KEY=<anthropic-key>
```

### Resource Configuration

**Development:**
```yaml
backend:
  replicaCount: 1
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
```

**Production:**
```yaml
backend:
  replicaCount: 3
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 15
  resources:
    requests:
      memory: "2Gi"
      cpu: "1000m"
```

### Storage Configuration

**Default Storage Class:**
```yaml
postgresql:
  persistence:
    size: 50Gi
    # Uses default storage class
```

**Custom Storage Class:**
```yaml
postgresql:
  persistence:
    size: 50Gi
    storageClassName: fast-ssd
```

## Cloud Providers

### IBM Cloud Kubernetes Service

```bash
# 1. Install IBM Cloud CLI
curl -fsSL https://clis.cloud.ibm.com/install/linux | sh

# 2. Login
ibmcloud login --apikey <your-api-key>

# 3. Configure kubectl
ibmcloud ks cluster config --cluster <cluster-name>

# 4. Deploy using Makefile
make ibmcloud-deploy CLUSTER_NAME=<cluster-name>

# Or deploy with Helm
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --create-namespace \
  --values ./deployment/helm/rag-modulo/values-prod.yaml \
  --set postgresql.persistence.storageClassName=ibmc-block-gold \
  --set milvus.persistence.storageClassName=ibmc-block-gold
```

**IBM Cloud Storage Classes:**
- `ibmc-block-gold` - High performance block storage
- `ibmc-block-silver` - Medium performance
- `ibmc-block-bronze` - Standard performance
- `ibmc-file-gold` - High performance file storage

### OpenShift

```bash
# 1. Login to OpenShift
oc login --token=<token> --server=<server-url>

# Or use Makefile
make openshift-login OC_TOKEN=<token> OC_SERVER=<server>

# 2. Deploy with OpenShift Routes
make openshift-deploy

# Or with Helm
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --create-namespace \
  --set openshift.enabled=true \
  --set openshift.routes.enabled=true \
  --set ingress.enabled=false
```

**OpenShift Features:**
- Routes instead of Ingress
- Security Context Constraints (SCC)
- Built-in container registry
- Integrated monitoring

### AWS EKS

```bash
# 1. Configure kubectl
aws eks update-kubeconfig --name <cluster-name> --region <region>

# 2. Install AWS Load Balancer Controller (for ALB Ingress)
# https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html

# 3. Deploy
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --create-namespace \
  --set ingress.className=alb \
  --set postgresql.persistence.storageClassName=gp3
```

### Google GKE

```bash
# 1. Configure kubectl
gcloud container clusters get-credentials <cluster-name> --region <region>

# 2. Deploy
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --create-namespace \
  --set postgresql.persistence.storageClassName=standard-rwo
```

### Azure AKS

```bash
# 1. Configure kubectl
az aks get-credentials --resource-group <rg> --name <cluster-name>

# 2. Deploy
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --create-namespace \
  --set postgresql.persistence.storageClassName=managed-premium
```

## Monitoring

### Check Deployment Status

```bash
# Using Makefile
make k8s-status

# Or directly with kubectl
kubectl get pods -n rag-modulo
kubectl get svc -n rag-modulo
kubectl get ingress -n rag-modulo
kubectl get hpa -n rag-modulo
```

### View Logs

```bash
# Backend logs
make k8s-logs-backend

# Frontend logs
make k8s-logs-frontend

# Or with kubectl
kubectl logs -f deployment/rag-modulo-backend -n rag-modulo
```

### Metrics Endpoints

- **Backend**: `http://backend-service:8000/metrics`
- **Milvus**: `http://milvus-service:9091/metrics`

### Prometheus Integration

Add annotations to services for Prometheus scraping:

```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"
```

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting

```bash
# Check pod status
kubectl get pods -n rag-modulo

# Describe pod for events
kubectl describe pod <pod-name> -n rag-modulo

# Check logs
kubectl logs <pod-name> -n rag-modulo
```

**Common Causes:**
- Image pull errors (check registry access)
- Resource constraints (check node capacity)
- Volume mount issues (check PVC status)
- Configuration errors (check secrets/configmaps)

#### 2. Service Not Accessible

```bash
# Check service endpoints
kubectl get endpoints -n rag-modulo

# Test service connectivity
kubectl run test-pod --rm -it --image=curlimages/curl -- \
  curl http://backend-service:8000/health
```

#### 3. Persistent Volume Issues

```bash
# Check PVC status
kubectl get pvc -n rag-modulo

# Check PV status
kubectl get pv

# Describe PVC for events
kubectl describe pvc <pvc-name> -n rag-modulo
```

#### 4. Ingress/Route Not Working

```bash
# Check ingress status
kubectl get ingress -n rag-modulo
kubectl describe ingress rag-modulo-ingress -n rag-modulo

# For OpenShift
oc get routes -n rag-modulo
oc describe route <route-name> -n rag-modulo
```

### Debug Commands

```bash
# Port forward to access services locally
make k8s-port-forward-backend  # localhost:8000
make k8s-port-forward-frontend # localhost:3000

# Open shell in pod
make k8s-shell-backend

# Check events
kubectl get events -n rag-modulo --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n rag-modulo
kubectl top nodes
```

### Rollback Deployment

```bash
# Helm rollback
helm rollback rag-modulo -n rag-modulo

# Or rollback to specific revision
helm rollback rag-modulo 2 -n rag-modulo

# Check rollback history
helm history rag-modulo -n rag-modulo
```

## Cleanup

```bash
# Uninstall Helm release
make helm-uninstall

# Or delete namespace (removes all resources)
make k8s-cleanup

# Manual cleanup
kubectl delete namespace rag-modulo
```

## Security Best Practices

1. **Use Secrets Management:**
   - External Secrets Operator
   - Sealed Secrets
   - HashiCorp Vault

2. **Enable Network Policies:**
   - Restrict pod-to-pod communication
   - Allow only necessary ingress/egress

3. **Use Pod Security Standards:**
   - Enforce restricted pod security
   - Run as non-root user
   - Read-only root filesystem

4. **Enable RBAC:**
   - Principle of least privilege
   - Service account per application
   - Regular access audits

5. **Scan Images:**
   - Use Trivy or Clair for vulnerability scanning
   - Automated scanning in CI/CD
   - Update base images regularly

## Next Steps

- [CI/CD Integration](./cicd.md)
- [Monitoring and Observability](./monitoring.md)
- [Scaling Guide](./scaling.md)
- [Disaster Recovery](./disaster-recovery.md)
