# RAG Modulo Helm Chart

This Helm chart deploys RAG Modulo to Kubernetes/OpenShift with production-ready configuration.

## Prerequisites

- Kubernetes 1.24+ or OpenShift 4.10+
- Helm 3.8+
- kubectl or oc CLI configured
- Persistent Volume provisioner support in the underlying infrastructure
- (Optional) cert-manager for automatic TLS certificate management

## Installation

### Quick Install

```bash
# Install with default values (production)
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --create-namespace

# Install development environment
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo-dev \
  --create-namespace \
  --values ./deployment/helm/rag-modulo/values-dev.yaml

# Install staging environment
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo-staging \
  --create-namespace \
  --values ./deployment/helm/rag-modulo/values-staging.yaml
```

### Install with Secrets

```bash
# Create secrets from .env file
kubectl create secret generic rag-modulo-secrets \
  --from-env-file=.env \
  --namespace rag-modulo

# Install chart
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --create-namespace
```

### Install with Custom Values

```bash
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --create-namespace \
  --set backend.replicaCount=5 \
  --set ingress.hosts.frontend=myapp.example.com
```

## Configuration

The following table lists the configurable parameters of the RAG Modulo chart and their default values.

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.namespace` | Kubernetes namespace | `rag-modulo` |
| `global.environment` | Environment name | `production` |

### Backend Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `backend.enabled` | Enable backend deployment | `true` |
| `backend.replicaCount` | Number of backend replicas | `3` |
| `backend.autoscaling.enabled` | Enable HPA | `true` |
| `backend.autoscaling.minReplicas` | Minimum replicas | `2` |
| `backend.autoscaling.maxReplicas` | Maximum replicas | `10` |
| `backend.resources.requests.memory` | Memory request | `2Gi` |
| `backend.resources.requests.cpu` | CPU request | `1000m` |

### Frontend Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `frontend.enabled` | Enable frontend deployment | `true` |
| `frontend.replicaCount` | Number of frontend replicas | `2` |
| `frontend.autoscaling.enabled` | Enable HPA | `true` |

### Database Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL | `true` |
| `postgresql.persistence.size` | PVC size | `50Gi` |
| `milvus.enabled` | Enable Milvus | `true` |
| `milvus.persistence.size` | PVC size | `100Gi` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class | `nginx` |
| `ingress.tls.enabled` | Enable TLS | `true` |
| `ingress.hosts.frontend` | Frontend hostname | `rag-modulo.example.com` |

## Upgrading

```bash
# Upgrade to new version
helm upgrade rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --values ./deployment/helm/rag-modulo/values-prod.yaml

# Upgrade with specific values
helm upgrade rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --set images.backend.tag=v1.1.0
```

## Uninstalling

```bash
# Uninstall release
helm uninstall rag-modulo --namespace rag-modulo

# Delete namespace (optional)
kubectl delete namespace rag-modulo
```

## OpenShift Deployment

For OpenShift deployments:

```bash
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --create-namespace \
  --set openshift.enabled=true \
  --set openshift.routes.enabled=true \
  --set ingress.enabled=false
```

## IBM Cloud Deployment

For IBM Cloud Kubernetes Service:

```bash
helm install rag-modulo ./deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --create-namespace \
  --set postgresql.persistence.storageClassName=ibmc-block-gold \
  --set milvus.persistence.storageClassName=ibmc-block-gold
```

## Monitoring

The chart includes Prometheus metrics endpoints on:
- Backend: `http://backend-service:8000/metrics`
- Milvus: `http://milvus-service:9091/metrics`

## Troubleshooting

### Check pod status
```bash
kubectl get pods -n rag-modulo
```

### View logs
```bash
kubectl logs -f deployment/rag-modulo-backend -n rag-modulo
```

### Debug failed pods
```bash
kubectl describe pod <pod-name> -n rag-modulo
```

### Access services locally
```bash
# Backend
kubectl port-forward svc/backend-service 8000:8000 -n rag-modulo

# Frontend
kubectl port-forward svc/frontend-service 8080:8080 -n rag-modulo
```

## Support

For issues and questions, please visit:
- GitHub: https://github.com/manavgup/rag_modulo/issues
- Documentation: https://github.com/manavgup/rag_modulo/docs
