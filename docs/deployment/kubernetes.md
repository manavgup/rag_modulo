# Kubernetes Deployment Guide

This guide covers deploying RAG Modulo to Kubernetes clusters, including deployment manifests, Helm charts, scaling strategies, and production best practices.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Kubernetes Manifests](#kubernetes-manifests)
- [Helm Chart Deployment](#helm-chart-deployment)
- [Scaling & High Availability](#scaling--high-availability)
- [Storage & Persistence](#storage--persistence)
- [Networking & Ingress](#networking--ingress)
- [Resource Management](#resource-management)
- [Troubleshooting](#troubleshooting)

## Overview

RAG Modulo on Kubernetes consists of:

- **Backend Deployment**: FastAPI application (StatefulSet or Deployment)
- **Frontend Deployment**: React/Nginx static server
- **PostgreSQL StatefulSet**: Primary database
- **Milvus StatefulSet**: Vector database with etcd dependency
- **MinIO StatefulSet**: Object storage
- **MLFlow Deployment**: Model tracking server

**Architecture Pattern**: Microservices with shared infrastructure services

## Prerequisites

### Required Tools

```bash
# Kubernetes cluster (v1.24+)
kubectl version --client

# Helm (v3.0+)
helm version

# Optional: k9s for cluster management
k9s version
```

### Cluster Requirements

- **Kubernetes**: 1.24+ (tested on 1.28)
- **Nodes**: 3+ nodes recommended for HA
- **CPU**: 8+ cores total
- **Memory**: 16GB+ total
- **Storage**: Dynamic provisioning with StorageClass

### Docker Images

```bash
# Backend
ghcr.io/manavgup/rag_modulo/backend:latest

# Frontend
ghcr.io/manavgup/rag_modulo/frontend:latest
```

## Kubernetes Manifests

### Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: rag-modulo
  labels:
    name: rag-modulo
    environment: production
```

### Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-modulo-secrets
  namespace: rag-modulo
type: Opaque
stringData:
  # Database
  postgres-user: postgres
  postgres-password: CHANGE_ME_SECURE_PASSWORD
  postgres-db: rag_modulo_db

  # JWT
  jwt-secret-key: CHANGE_ME_MIN_32_CHARS_SECURE_JWT_SECRET

  # MinIO
  minio-root-user: minioadmin
  minio-root-password: CHANGE_ME_SECURE_PASSWORD

  # MLFlow
  mlflow-username: mlflow
  mlflow-password: CHANGE_ME_SECURE_PASSWORD

  # LLM Providers
  watsonx-api-key: YOUR_WATSONX_API_KEY
  watsonx-url: https://us-south.ml.cloud.ibm.com
  watsonx-instance-id: YOUR_INSTANCE_ID

  # Optional: OpenAI, Anthropic
  openai-api-key: YOUR_OPENAI_KEY
  anthropic-api-key: YOUR_ANTHROPIC_KEY
```

**Create from file**:

```bash
# DO NOT commit secrets to git!
kubectl apply -f secrets.yaml

# Or create from .env file
kubectl create secret generic rag-modulo-secrets \
  --from-env-file=.env \
  --namespace=rag-modulo
```

### ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-modulo-config
  namespace: rag-modulo
data:
  # Application
  ENVIRONMENT: "production"
  SKIP_AUTH: "false"
  DEVELOPMENT_MODE: "false"
  TESTING: "false"

  # Database
  COLLECTIONDB_HOST: "postgres-service"
  COLLECTIONDB_PORT: "5432"

  # Vector Database
  VECTOR_DB: "milvus"
  MILVUS_HOST: "milvus-service"
  MILVUS_PORT: "19530"

  # Object Storage
  MINIO_HOST: "minio-service"
  MINIO_PORT: "9000"

  # MLFlow
  MLFLOW_TRACKING_URI: "http://mlflow-service:5000"

  # Frontend
  FRONTEND_URL: "https://rag-modulo.example.com"
  BACKEND_URL: "https://api.rag-modulo.example.com"
```

### PostgreSQL StatefulSet

```yaml
# postgres-statefulset.yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: rag-modulo
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
  clusterIP: None  # Headless service
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: rag-modulo
spec:
  serviceName: postgres-service
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:13
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: rag-modulo-secrets
              key: postgres-db
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: rag-modulo-secrets
              key: postgres-user
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: rag-modulo-secrets
              key: postgres-password
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 5
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: standard  # Change to your StorageClass
      resources:
        requests:
          storage: 50Gi
```

### Milvus StatefulSet

```yaml
# milvus-statefulset.yaml
apiVersion: v1
kind: Service
metadata:
  name: milvus-etcd
  namespace: rag-modulo
spec:
  selector:
    app: milvus-etcd
  ports:
    - port: 2379
      targetPort: 2379
  clusterIP: None
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: milvus-etcd
  namespace: rag-modulo
spec:
  serviceName: milvus-etcd
  replicas: 1
  selector:
    matchLabels:
      app: milvus-etcd
  template:
    metadata:
      labels:
        app: milvus-etcd
    spec:
      containers:
      - name: etcd
        image: quay.io/coreos/etcd:v3.5.9
        env:
        - name: ETCD_NAME
          value: "etcd"
        - name: ETCD_DATA_DIR
          value: "/etcd-data"
        - name: ETCD_LISTEN_CLIENT_URLS
          value: "http://0.0.0.0:2379"
        - name: ETCD_ADVERTISE_CLIENT_URLS
          value: "http://milvus-etcd:2379"
        volumeMounts:
        - name: etcd-data
          mountPath: /etcd-data
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
  volumeClaimTemplates:
  - metadata:
      name: etcd-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: milvus-service
  namespace: rag-modulo
spec:
  selector:
    app: milvus
  ports:
    - port: 19530
      targetPort: 19530
      name: grpc
    - port: 9091
      targetPort: 9091
      name: metrics
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: milvus
  namespace: rag-modulo
spec:
  serviceName: milvus-service
  replicas: 1
  selector:
    matchLabels:
      app: milvus
  template:
    metadata:
      labels:
        app: milvus
    spec:
      containers:
      - name: milvus
        image: milvusdb/milvus:v2.4.4
        command: ["milvus", "run", "standalone"]
        ports:
        - containerPort: 19530
          name: grpc
        - containerPort: 9091
          name: metrics
        env:
        - name: ETCD_ENDPOINTS
          value: "milvus-etcd:2379"
        - name: MINIO_ADDRESS
          value: "minio-service:9000"
        - name: MINIO_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: rag-modulo-secrets
              key: minio-root-user
        - name: MINIO_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: rag-modulo-secrets
              key: minio-root-password
        volumeMounts:
        - name: milvus-data
          mountPath: /var/lib/milvus
        resources:
          requests:
            memory: "4Gi"
            cpu: "1000m"
          limits:
            memory: "8Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 9091
          initialDelaySeconds: 60
          periodSeconds: 30
  volumeClaimTemplates:
  - metadata:
      name: milvus-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
```

### Backend Deployment

```yaml
# backend-deployment.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: rag-modulo
spec:
  selector:
    app: backend
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: rag-modulo
spec:
  replicas: 3  # Scale based on load
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
        version: v1
    spec:
      containers:
      - name: backend
        image: ghcr.io/manavgup/rag_modulo/backend:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        env:
        # ConfigMap values
        - name: ENVIRONMENT
          valueFrom:
            configMapKeyRef:
              name: rag-modulo-config
              key: ENVIRONMENT
        - name: COLLECTIONDB_HOST
          valueFrom:
            configMapKeyRef:
              name: rag-modulo-config
              key: COLLECTIONDB_HOST
        - name: MILVUS_HOST
          valueFrom:
            configMapKeyRef:
              name: rag-modulo-config
              key: MILVUS_HOST
        # Secret values
        - name: COLLECTIONDB_USER
          valueFrom:
            secretKeyRef:
              name: rag-modulo-secrets
              key: postgres-user
        - name: COLLECTIONDB_PASS
          valueFrom:
            secretKeyRef:
              name: rag-modulo-secrets
              key: postgres-password
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: rag-modulo-secrets
              key: jwt-secret-key
        - name: WATSONX_APIKEY
          valueFrom:
            secretKeyRef:
              name: rag-modulo-secrets
              key: watsonx-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

### Frontend Deployment

```yaml
# frontend-deployment.yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: rag-modulo
spec:
  selector:
    app: frontend
  ports:
    - port: 8080
      targetPort: 8080
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: rag-modulo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: ghcr.io/manavgup/rag_modulo/frontend:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: REACT_APP_BACKEND_URL
          value: "https://api.rag-modulo.example.com"
        - name: REACT_APP_WS_URL
          value: "wss://api.rag-modulo.example.com/ws"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Helm Chart Deployment

### Directory Structure

```bash
rag-modulo-helm/
├── Chart.yaml
├── values.yaml
├── values-production.yaml
├── templates/
│   ├── namespace.yaml
│   ├── secrets.yaml
│   ├── configmap.yaml
│   ├── postgres-statefulset.yaml
│   ├── milvus-statefulset.yaml
│   ├── minio-statefulset.yaml
│   ├── backend-deployment.yaml
│   ├── frontend-deployment.yaml
│   ├── ingress.yaml
│   └── NOTES.txt
└── README.md
```

### Chart.yaml

```yaml
apiVersion: v2
name: rag-modulo
description: RAG Modulo - Production-ready RAG platform
type: application
version: 1.0.0
appVersion: "1.0.0"
keywords:
  - rag
  - ai
  - llm
  - vector-database
maintainers:
  - name: RAG Modulo Team
```

### values.yaml (excerpt)

```yaml
# Global settings
global:
  namespace: rag-modulo
  environment: production

# Backend
backend:
  replicaCount: 3
  image:
    repository: ghcr.io/manavgup/rag_modulo/backend
    tag: latest
    pullPolicy: Always
  resources:
    requests:
      memory: "2Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "2000m"
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70

# PostgreSQL
postgres:
  enabled: true
  image: postgres:13
  storage: 50Gi
  storageClass: standard

# Milvus
milvus:
  enabled: true
  image: milvusdb/milvus:v2.4.4
  storage: 100Gi
  resources:
    requests:
      memory: "4Gi"
      cpu: "1000m"

# Ingress
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.rag-modulo.example.com
      paths:
        - path: /
          pathType: Prefix
          service: backend-service
  tls:
    - secretName: rag-modulo-tls
      hosts:
        - api.rag-modulo.example.com
```

### Deploy with Helm

```bash
# Add repository (if published to Helm repo)
helm repo add rag-modulo https://charts.rag-modulo.com
helm repo update

# Install from local chart
helm install rag-modulo ./rag-modulo-helm \
  --namespace rag-modulo \
  --create-namespace \
  --values values-production.yaml

# Upgrade deployment
helm upgrade rag-modulo ./rag-modulo-helm \
  --namespace rag-modulo \
  --values values-production.yaml

# Rollback to previous version
helm rollback rag-modulo 1 --namespace rag-modulo

# Uninstall
helm uninstall rag-modulo --namespace rag-modulo
```

## Scaling & High Availability

### Horizontal Pod Autoscaling (HPA)

```yaml
# backend-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: rag-modulo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 1
        periodSeconds: 60
```

### Pod Disruption Budget

```yaml
# backend-pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: backend-pdb
  namespace: rag-modulo
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: backend
```

### Multi-Region Deployment

For global availability, deploy to multiple regions:

```bash
# Region 1: us-east-1
kubectl --context=us-east-1 apply -f manifests/

# Region 2: eu-west-1
kubectl --context=eu-west-1 apply -f manifests/

# Use global load balancer (AWS Route53, Cloudflare, etc.)
```

## Storage & Persistence

### StorageClass for Different Providers

```yaml
# AWS EBS (gp3)
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
volumeBindingMode: WaitForFirstConsumer

# GCP Persistent Disk
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: pd.csi.storage.gke.io
parameters:
  type: pd-ssd
volumeBindingMode: WaitForFirstConsumer

# Azure Disk
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: disk.csi.azure.com
parameters:
  skuName: Premium_LRS
volumeBindingMode: WaitForFirstConsumer
```

### Backup Strategy

```yaml
# Use Velero for cluster backups
velero install \
  --provider aws \
  --bucket rag-modulo-backups \
  --backup-location-config region=us-east-1

# Schedule daily backups
velero schedule create rag-modulo-daily \
  --schedule="0 2 * * *" \
  --include-namespaces=rag-modulo

# Restore from backup
velero restore create --from-backup rag-modulo-daily-20250109
```

## Networking & Ingress

### Ingress with NGINX

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rag-modulo-ingress
  namespace: rag-modulo
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.rag-modulo.example.com
    - rag-modulo.example.com
    secretName: rag-modulo-tls
  rules:
  - host: api.rag-modulo.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000
  - host: rag-modulo.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 8080
```

## Resource Management

### Resource Quotas

```yaml
# resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: rag-modulo-quota
  namespace: rag-modulo
spec:
  hard:
    requests.cpu: "20"
    requests.memory: "40Gi"
    limits.cpu: "40"
    limits.memory: "80Gi"
    persistentvolumeclaims: "10"
```

### LimitRange

```yaml
# limit-range.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: rag-modulo-limits
  namespace: rag-modulo
spec:
  limits:
  - max:
      cpu: "4"
      memory: "8Gi"
    min:
      cpu: "100m"
      memory: "128Mi"
    default:
      cpu: "500m"
      memory: "512Mi"
    defaultRequest:
      cpu: "250m"
      memory: "256Mi"
    type: Container
```

## Troubleshooting

### Check Pod Status

```bash
# List all pods
kubectl get pods -n rag-modulo

# Describe problematic pod
kubectl describe pod backend-xxx -n rag-modulo

# View logs
kubectl logs -f backend-xxx -n rag-modulo

# Previous container logs (after crash)
kubectl logs backend-xxx -n rag-modulo --previous
```

### Debug Pod Issues

```bash
# Run interactive shell in pod
kubectl exec -it backend-xxx -n rag-modulo -- /bin/bash

# Test database connectivity
kubectl exec -it backend-xxx -n rag-modulo -- python -c "
from rag_solution.file_management.database import engine
print(engine.url)
"

# Check environment variables
kubectl exec backend-xxx -n rag-modulo -- env | grep COLLECTION
```

### Network Troubleshooting

```bash
# Test service DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -n rag-modulo -- nslookup postgres-service

# Test service connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n rag-modulo -- curl http://backend-service:8000/api/health
```

### Related Documentation

- [Cloud Deployment](cloud.md) - Docker and cloud platform deployment
- [Monitoring & Observability](monitoring.md) - Prometheus and logging
- [Security Hardening](security-hardening.md) - K8s security best practices
