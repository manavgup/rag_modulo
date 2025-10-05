# RAG Modulo Deployment

This directory contains all deployment configurations for RAG Modulo on Kubernetes/OpenShift.

## Directory Structure

```
deployment/
├── k8s/                    # Raw Kubernetes manifests
│   ├── base/              # Base configurations
│   │   ├── namespace.yaml
│   │   ├── configmaps/    # Application configuration
│   │   ├── secrets/       # Secret templates
│   │   ├── storage/       # PersistentVolumeClaims
│   │   ├── statefulsets/  # StatefulSets (PostgreSQL, Milvus, etc.)
│   │   ├── deployments/   # Deployments (Backend, Frontend, MLFlow)
│   │   ├── services/      # Kubernetes Services
│   │   ├── ingress/       # Ingress/Route configurations
│   │   └── hpa/          # HorizontalPodAutoscaler
│   └── overlays/          # Environment-specific overlays
│       ├── dev/
│       ├── staging/
│       └── prod/
├── helm/                  # Helm chart
│   └── rag-modulo/
│       ├── Chart.yaml
│       ├── values.yaml           # Default values
│       ├── values-dev.yaml       # Development values
│       ├── values-staging.yaml   # Staging values
│       ├── values-prod.yaml      # Production values
│       └── templates/            # Helm templates
└── scripts/               # Deployment scripts
    ├── deploy-k8s.sh     # Raw K8s deployment
    └── deploy-helm.sh    # Helm deployment
```

## Quick Start

### 1. Prerequisites

- Kubernetes 1.24+ or OpenShift 4.10+
- kubectl/oc CLI configured
- Helm 3.8+ (for Helm deployments)
- `.env` file with credentials

### 2. Deploy

Choose your deployment method:

**Helm (Recommended):**
```bash
# Development
make helm-install-dev

# Staging
make helm-install-staging

# Production
make helm-install-prod
```

**Raw Kubernetes:**
```bash
# Development
./deployment/scripts/deploy-k8s.sh dev

# Production
./deployment/scripts/deploy-k8s.sh prod
```

## Deployment Methods

### Method 1: Helm Chart

**Pros:**
- Easy upgrades and rollbacks
- Environment-specific configurations
- Template-based customization
- Release management

**Usage:**
```bash
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --values ./deployment/helm/rag-modulo/values-prod.yaml
```

### Method 2: Raw Kubernetes Manifests

**Pros:**
- Full control over resources
- No Helm dependency
- GitOps-friendly
- Simple debugging

**Usage:**
```bash
kubectl apply -f deployment/k8s/base/ -R -n rag-modulo
```

### Method 3: Deployment Scripts

**Pros:**
- Automated deployment workflow
- Environment validation
- Consistent deployment process

**Usage:**
```bash
./deployment/scripts/deploy-helm.sh prod install
```

## Configuration

### Secrets

Create secrets from `.env` file:

```bash
kubectl create secret generic rag-modulo-secrets \
  --from-env-file=.env \
  --namespace rag-modulo
```

Required secrets:
- Database credentials
- MinIO credentials
- JWT secret
- LLM provider API keys

### Environment-Specific Values

**Development (`values-dev.yaml`):**
- Minimal resources
- No autoscaling
- HTTP (no TLS)
- Debug logging

**Staging (`values-staging.yaml`):**
- Medium resources
- Autoscaling enabled (2-5 replicas)
- TLS enabled
- Info logging

**Production (`values-prod.yaml`):**
- Full resources
- Autoscaling enabled (3-15 replicas)
- TLS with cert-manager
- Info logging
- High-performance storage

## Cloud Provider Specific

### IBM Cloud

```bash
make ibmcloud-deploy CLUSTER_NAME=<cluster-name>
```

Storage classes:
- `ibmc-block-gold` (recommended)
- `ibmc-block-silver`
- `ibmc-file-gold`

### OpenShift

```bash
make openshift-login OC_TOKEN=<token> OC_SERVER=<server>
make openshift-deploy
```

Features:
- Routes instead of Ingress
- Built-in container registry
- Security Context Constraints

### AWS EKS

```bash
aws eks update-kubeconfig --name <cluster>
helm install rag-modulo ./deployment/helm/rag-modulo \
  --set ingress.className=alb
```

### Google GKE

```bash
gcloud container clusters get-credentials <cluster>
helm install rag-modulo ./deployment/helm/rag-modulo
```

### Azure AKS

```bash
az aks get-credentials --resource-group <rg> --name <cluster>
helm install rag-modulo ./deployment/helm/rag-modulo
```

## Components

### Stateful Services

- **PostgreSQL**: Metadata database
- **Milvus**: Vector database
- **MinIO**: Object storage
- **etcd**: Milvus coordination

### Stateless Services

- **Backend**: FastAPI application (3 replicas)
- **Frontend**: React application (2 replicas)
- **MLFlow**: Model tracking (1 replica)

### Auto-Scaling

HorizontalPodAutoscaler configured for:
- Backend: 2-10 replicas (CPU 70%, Memory 80%)
- Frontend: 2-5 replicas (CPU 70%, Memory 80%)

## Monitoring

### Metrics Endpoints

- Backend: `/metrics` (Prometheus format)
- Milvus: `:9091/metrics`

### Logs

```bash
# View logs
kubectl logs -f deployment/rag-modulo-backend -n rag-modulo

# Using Makefile
make k8s-logs-backend
make k8s-logs-frontend
```

### Status

```bash
# Check deployment
kubectl get pods -n rag-modulo
kubectl get svc -n rag-modulo
kubectl get hpa -n rag-modulo

# Using Makefile
make k8s-status
```

## Maintenance

### Upgrade

```bash
# Helm upgrade
make helm-upgrade-prod

# Or manually
helm upgrade rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --values ./deployment/helm/rag-modulo/values-prod.yaml
```

### Rollback

```bash
# Helm rollback
helm rollback rag-modulo -n rag-modulo

# Or to specific revision
helm rollback rag-modulo 2 -n rag-modulo
```

### Cleanup

```bash
# Uninstall Helm release
make helm-uninstall

# Delete namespace
make k8s-cleanup
```

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n rag-modulo
kubectl describe pod <pod-name> -n rag-modulo
```

### Check Logs
```bash
kubectl logs <pod-name> -n rag-modulo
kubectl logs -f deployment/rag-modulo-backend -n rag-modulo
```

### Check Events
```bash
kubectl get events -n rag-modulo --sort-by='.lastTimestamp'
```

### Debug Services
```bash
# Port forward
make k8s-port-forward-backend  # localhost:8000
make k8s-port-forward-frontend # localhost:3000

# Open shell
make k8s-shell-backend
```

## CI/CD Integration

### Automated Deployments

RAG Modulo uses GitHub Actions for automated deployments. Deployments are controlled via GitHub repository variables and can be enabled/disabled without code changes.

**Available Workflows:**
- `.github/workflows/openshift-staging.yml` - OpenShift on IBM Cloud (staging)
- `.github/workflows/k8s-deploy-production.yml` - Kubernetes production
- `.github/workflows/ibm-code-engine-staging.yml` - IBM Code Engine (future)

### Enabling Automated Deployments

#### Step 1: Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions → Secrets** and add:

```
IBM_CLOUD_API_KEY         # IBM Cloud API key with cluster admin access
```

#### Step 2: Configure GitHub Variables

Go to **Settings → Secrets and variables → Actions → Variables** and add:

```
DEPLOY_TO_OPENSHIFT       # Set to "true" to enable OpenShift deployment
OPENSHIFT_CLUSTER_NAME    # Name of your OpenShift cluster (e.g., "rag-modulo-staging")
```

#### Step 3: Enable/Disable Deployments

**To Enable OpenShift Deployment:**
1. Set `DEPLOY_TO_OPENSHIFT = true` in repository variables
2. Push to `main` branch → automatic deployment

**To Disable:**
1. Set `DEPLOY_TO_OPENSHIFT = false`
2. Or delete the variable

**Manual Deployment:**
1. Go to **Actions** tab
2. Select **Deploy to OpenShift Staging** workflow
3. Click **Run workflow**
4. Options:
   - **Force deploy**: Deploy even if disabled in settings
   - **Skip tests**: Skip tests before deployment

### Deployment Configuration

Configure deployment behavior in `.env.example`:

```bash
# Deployment environment: local | staging | production
DEPLOYMENT_ENVIRONMENT=local

# Enable deployment targets (set in GitHub repository variables)
DEPLOY_TO_OPENSHIFT=false
DEPLOY_TO_CODE_ENGINE=false

# Cloud provider: aws | azure | ibm | gcp
CLOUD_PROVIDER=

# Container registry
# - ghcr.io/manavgup/rag_modulo (default, standard K8s/OpenShift)
# - ca.icr.io/rag-modulo (IBM Cloud OpenShift, required for VPC)
CONTAINER_REGISTRY=ghcr.io/manavgup/rag_modulo
```

### Container Registry Strategy

| Environment | Registry | Why |
|-------------|----------|-----|
| Standard K8s/OpenShift | `ghcr.io` | Public registry, works everywhere |
| IBM Cloud OpenShift VPC | `ca.icr.io` | Required due to VPC networking restrictions |

The Helm chart supports configurable registries:
```bash
helm install rag-modulo ./deployment/helm/rag-modulo \
  --set images.registry=ca.icr.io/rag-modulo
```

### OpenShift on IBM Cloud Specifics

The automated deployment includes these OpenShift-specific fixes:

1. **Container Registry**: Pushes to ICR (`ca.icr.io`) instead of GHCR
2. **Backend Health Check**: Uses `/api/health` (not `/health`)
3. **Backend Environment**: Sets `COLLECTIONDB_PASS` (backend code requirement)
4. **Frontend Port**: Uses container port 8080 (nginx default)
5. **Frontend Volumes**: EmptyDir volumes for nginx writable directories
6. **Service Names**: Creates backend service alias for frontend nginx

All fixes are incorporated in the Helm chart and OpenShift manifests.

## Documentation

- [Kubernetes Deployment Guide](../docs/deployment/kubernetes.md)
- [Quick Start Guide](../docs/deployment/QUICKSTART.md)
- [Helm Chart README](./helm/rag-modulo/README.md)

## Support

- Issues: https://github.com/manavgup/rag_modulo/issues
- Discussions: https://github.com/manavgup/rag_modulo/discussions
- Documentation: https://github.com/manavgup/rag_modulo/docs
