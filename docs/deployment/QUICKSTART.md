# Kubernetes Deployment Quick Start

Get RAG Modulo running on Kubernetes in 5 minutes!

## Prerequisites

- Kubernetes cluster (1.24+) or OpenShift (4.10+)
- `kubectl` or `oc` CLI configured
- `helm` 3.8+ installed
- `.env` file with credentials

## Step 1: Prepare Environment

```bash
# Clone repository
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo

# Copy and configure environment
cp env.example .env
# Edit .env with your credentials
```

## Step 2: Deploy (Choose One Method)

### Method A: Helm (Recommended)

```bash
# Development
make helm-install-dev

# Production
make helm-install-prod
```

### Method B: Kubernetes Manifests

```bash
# Development
make k8s-deploy-dev

# Production
make k8s-deploy-prod
```

### Method C: Cloud-Specific

#### IBM Cloud
```bash
# Configure cluster
ibmcloud ks cluster config --cluster <cluster-name>

# Deploy
make ibmcloud-deploy CLUSTER_NAME=<cluster-name>
```

#### OpenShift
```bash
# Login
make openshift-login OC_TOKEN=<token> OC_SERVER=<server>

# Deploy
make openshift-deploy
```

## Step 3: Verify Deployment

```bash
# Check status
make k8s-status

# View logs
make k8s-logs-backend
make k8s-logs-frontend
```

## Step 4: Access Application

### Port Forward (Local Access)
```bash
# Backend
make k8s-port-forward-backend
# Access: http://localhost:8000

# Frontend
make k8s-port-forward-frontend
# Access: http://localhost:3000
```

### Ingress/Route (Production)
```bash
# Get ingress URL
kubectl get ingress -n rag-modulo

# For OpenShift
oc get routes -n rag-modulo
```

## Common Commands

```bash
# Update deployment
make helm-upgrade-prod

# View logs
make k8s-logs-backend

# Check status
make k8s-status

# Open shell in pod
make k8s-shell-backend

# Uninstall
make helm-uninstall
```

## Troubleshooting

### Pods Not Running
```bash
kubectl get pods -n rag-modulo
kubectl describe pod <pod-name> -n rag-modulo
kubectl logs <pod-name> -n rag-modulo
```

### Service Not Accessible
```bash
kubectl get svc -n rag-modulo
kubectl get endpoints -n rag-modulo
```

### Check Events
```bash
kubectl get events -n rag-modulo --sort-by='.lastTimestamp'
```

## Next Steps

- [Full Kubernetes Guide](./kubernetes.md)
- [Configuration Options](./configuration.md)
- [Scaling Guide](./scaling.md)
- [Monitoring Setup](./monitoring.md)

## Getting Help

- Documentation: [docs/](../../)
- Issues: https://github.com/manavgup/rag_modulo/issues
- Discussions: https://github.com/manavgup/rag_modulo/discussions
