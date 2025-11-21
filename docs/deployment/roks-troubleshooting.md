# IBM ROKS Deployment Troubleshooting Guide

This guide documents common issues and solutions when deploying RAG Modulo to IBM Red Hat OpenShift Kubernetes Service (ROKS).

## Table of Contents

- [Backend Issues](#backend-issues)
- [Frontend Issues](#frontend-issues)
- [Milvus Vector Database](#milvus-vector-database)
- [OpenShift Security Context Constraints](#openshift-security-context-constraints)
- [Helm Deployment](#helm-deployment)
- [Quick Reference](#quick-reference)

---

## Backend Issues

### CrashLoopBackOff - HuggingFace Model Download

**Symptoms:**
```
rag-modulo-backend-xxx   0/1   CrashLoopBackOff   5   10m
```

**Log Pattern:**
```
OSError: [Errno 30] Read-only file system: '/root/.cache/huggingface'
```

**Root Cause:**
OpenShift runs containers with a read-only root filesystem by default. HuggingFace libraries attempt to download models to `/root/.cache/huggingface`.

**Solution:**
Set the `HF_HOME` environment variable to a writable directory:

```yaml
# In deployment or values.yaml
env:
  - name: HF_HOME
    value: "/tmp/huggingface"
```

Or via Helm:
```bash
helm upgrade --install rag-modulo deployment/helm/rag-modulo \
  --set backend.env.HF_HOME=/tmp/huggingface
```

---

### CrashLoopBackOff - Health Probe Timeout

**Symptoms:**
```
Liveness probe failed: Get "http://10.x.x.x:8000/health": context deadline exceeded
```

**Root Cause:**
The backend downloads ML models on startup, which can take 30-60 seconds. Default health probe timeouts are too aggressive.

**Solution:**
Increase health probe timing in the deployment:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 60    # Was 30
  periodSeconds: 30          # Was 10
  timeoutSeconds: 10         # Was 5
  failureThreshold: 5        # Was 3

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 15
  timeoutSeconds: 10
```

---

### CrashLoopBackOff - Transformers Import Error

**Symptoms:**
```
ImportError: cannot import name 'AutoModelForImageTextToText' from 'transformers'
```

**Root Cause:**
Transformers library version mismatch or initialization issues in production mode.

**Solution:**
Set environment to development mode for graceful handling:

```yaml
env:
  - name: ENVIRONMENT
    value: "development"
```

---

## Frontend Issues

### ImagePullBackOff

**Symptoms:**
```
rag-modulo-frontend-xxx   0/1   ImagePullBackOff   0   5m
```

**Root Cause:**
- Incorrect image repository path
- Missing image pull secrets for private registries

**Solution:**
1. Verify image path in values.yaml:
```yaml
image:
  frontend:
    repository: ghcr.io/manavgup/rag_modulo/frontend
    tag: "0.8.0"
```

2. For private registries, create and reference image pull secrets:
```bash
oc create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=$GITHUB_USER \
  --docker-password=$GITHUB_TOKEN \
  -n rag-modulo

# Reference in deployment
imagePullSecrets:
  - name: ghcr-secret
```

---

## Milvus Vector Database

### Intermittent Connection Failures

**Symptoms:**
```
Failed to connect to Milvus at xxx:19530: illegal connection params or server unavailable
Retrying connection to Milvus... (Attempt 2/3)
Connected to Milvus at xxx:19530
```

**Log Pattern (every 3-5 seconds):**
```
Disconnected existing Milvus connection
Connected to Milvus at my-release-milvus.rag-modulo.svc.cluster.local:19530
```

**Root Cause:**
The MilvusStore `_connect()` method was disconnecting valid connections before reconnecting. In Kubernetes, each health check creates a new store instance, triggering unnecessary disconnect/reconnect cycles. K8s SDN latency causes first connection attempts to occasionally fail.

**Solution:**
PR #648 adds connection reuse logic. Update to the latest backend image:

```bash
# Trigger rolling update
oc rollout restart deployment/rag-modulo-backend -n rag-modulo
```

**Expected Behavior After Fix:**
- Before: `Disconnected existing Milvus connection` every 3 seconds
- After: `Reusing existing Milvus connection` (DEBUG level, minimal logging)

---

### Milvus Cluster Not Healthy

**Symptoms:**
```
oc get milvus my-release -n rag-modulo
NAME         MODE      STATUS    AGE
my-release   cluster   Unhealthy 10m
```

**Diagnostic Commands:**
```bash
# Check Milvus component pods
oc get pods -n rag-modulo -l app.kubernetes.io/instance=my-release

# Check etcd pods
oc get pods -n rag-modulo -l app.kubernetes.io/name=etcd

# Check MinIO pods
oc get pods -n rag-modulo -l app.kubernetes.io/name=minio

# View Milvus operator logs
oc logs -n milvus-operator deployment/milvus-operator
```

**Common Fixes:**
1. Ensure etcd and MinIO are running first
2. Check PVC provisioning (storage class must support RWO)
3. Verify SCC permissions (see next section)

---

## OpenShift Security Context Constraints

### Pods Stuck in CreateContainerConfigError

**Symptoms:**
```
rag-modulo-backend-xxx   0/1   CreateContainerConfigError   0   2m
```

**Root Cause:**
OpenShift requires explicit Security Context Constraints (SCC) for containers that need elevated permissions.

**Solution:**
Grant `anyuid` SCC to service accounts:

```bash
# For Milvus Operator
oc adm policy add-scc-to-user anyuid -z milvus-operator -n milvus-operator

# For application namespace
oc adm policy add-scc-to-user anyuid -z default -n rag-modulo
```

---

### Milvus Operator Cannot Create SCCs

**Symptoms:**
Milvus operator fails to create required SCCs for Milvus components.

**Solution:**
Create a ClusterRole with SCC management permissions:

```yaml
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
```

Then bind it:
```bash
oc adm policy add-cluster-role-to-user milvus-operator-scc-manager \
  -z milvus-operator -n milvus-operator
```

---

## Helm Deployment

### Deployment Timeout

**Symptoms:**
```
Error: context deadline exceeded
```

**Root Cause:**
Default Helm timeout (5 minutes) is insufficient for complex deployments with Milvus.

**Solution:**
Increase timeout:
```bash
helm upgrade --install rag-modulo deployment/helm/rag-modulo \
  --namespace rag-modulo \
  --timeout 15m \
  --wait
```

---

### External Milvus Configuration

When using Milvus Operator (instead of embedded Milvus), configure external connection:

```bash
helm upgrade --install rag-modulo deployment/helm/rag-modulo \
  --set milvus.enabled=false \
  --set milvus.external.enabled=true \
  --set milvus.external.host=my-release-milvus-proxy.rag-modulo.svc.cluster.local \
  --set milvus.external.port=19530
```

---

## Quick Reference

### Environment Variables for ROKS

| Variable | Value | Purpose |
|----------|-------|---------|
| `HF_HOME` | `/tmp/huggingface` | Writable cache for HuggingFace models |
| `ENVIRONMENT` | `development` | Graceful handling of library issues |
| `MILVUS_HOST` | `my-release-milvus-proxy.rag-modulo.svc.cluster.local` | Milvus service endpoint |
| `MILVUS_PORT` | `19530` | Milvus gRPC port |

### Health Probe Settings

| Setting | Recommended Value | Default |
|---------|-------------------|---------|
| `initialDelaySeconds` | 60 | 30 |
| `periodSeconds` | 30 | 10 |
| `timeoutSeconds` | 10 | 5 |
| `failureThreshold` | 5 | 3 |

### SCC Commands

```bash
# Grant anyuid to service account
oc adm policy add-scc-to-user anyuid -z <service-account> -n <namespace>

# Check SCC for a pod
oc get pod <pod-name> -o yaml | grep -A5 securityContext

# List all SCCs
oc get scc
```

### Diagnostic Commands

```bash
# Check pod status
oc get pods -n rag-modulo

# View pod logs
oc logs -n rag-modulo deployment/rag-modulo-backend --tail=100

# Describe pod for events
oc describe pod <pod-name> -n rag-modulo

# Check Milvus cluster status
oc get milvus -n rag-modulo

# View recent events
oc get events -n rag-modulo --sort-by='.lastTimestamp' | tail -20
```

---

## Related Documentation

- [Kubernetes Deployment Guide](./kubernetes.md)
- [Milvus Operator Automation](./MILVUS_OPERATOR_AUTOMATION.md)
- [Cloud Deployment Workflow](./cloud-deployment-workflow.md)
- [Security Hardening](./security-hardening.md)
