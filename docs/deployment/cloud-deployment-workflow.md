# Cloud Deployment Workflow Guide

## Overview

This guide explains the **recommended workflow** for building Docker images and deploying RAG Modulo to cloud platforms (ROKS, EKS, AKS, GKE).

**TL;DR**: Use native platform builds for local testing, GitHub Actions for cloud deployment.

## The Two-Track Workflow

### Track 1: Local Development (Platform-Native)

**For Mac Developers** (Apple Silicon M1/M2/M3):
```bash
# ✅ Build ARM64 locally (fast, native)
make dev-full-build          # Builds ARM64 images
make dev-full-start          # Test locally in containers

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

**For Linux Developers** (x86_64/AMD64):
```bash
# ✅ Build AMD64 locally (fast, native)
make dev-full-build          # Builds AMD64 images
make dev-full-start          # Test locally in containers

# Same URLs as Mac
```

**Key Points**:
- **Same commands** work on Mac and Linux
- **Same docker-compose files** (platform-agnostic)
- Builds are **fast** (5-10 min) because they're native
- Perfect for rapid iteration and testing

### Track 2: Cloud Deployment (AMD64-Only)

**Option A: GitHub Actions** (Recommended ✅)
```bash
# Step 1: Commit and push code
git add .
git commit -m "feat: add new feature"
git push

# Step 2: Let GitHub Actions build (automatic)
# - Runs on merge to main
# - Native AMD64 build on Linux runners
# - 10-15 minutes, no Mac resources used
# - Pushes to ghcr.io/manavgup/rag_modulo

# Step 3: Deploy to cloud
make deploy-roks-app         # ROKS (IBM Cloud)
make deploy-eks-app          # EKS (AWS) - coming soon
make deploy-aks-app          # AKS (Azure) - coming soon
make deploy-gke-app          # GKE (Google Cloud) - coming soon
```

**Option B: Mac Local Build** (Not Recommended ❌)
```bash
# ⚠️ SLOW: Cross-compilation ARM64 → AMD64
make build-cloud-push-all    # 10-15 min build + 3-6 min push

# Why NOT recommended:
# - QEMU emulation (12-18x slower than native)
# - Uses Mac CPU/memory continuously
# - GitHub Actions is faster and free
```

## Performance Comparison

| Build Method | Platform | Time | Notes |
|--------------|----------|------|-------|
| **Local Dev (Mac)** | ARM64 → ARM64 | 5-10 min | ✅ Fast, recommended for testing |
| **Local Dev (Linux)** | AMD64 → AMD64 | 5-10 min | ✅ Fast, recommended for testing |
| **Mac → Cloud** | ARM64 → AMD64 | 13-21 min | ❌ Slow QEMU cross-compilation |
| **GitHub Actions** | AMD64 → AMD64 | 10-15 min | ✅ Fast, native build, recommended |

## Makefile Targets Reference

### Local Development Targets

```bash
# Native platform builds (fast)
make dev-full-build           # Build for native arch (ARM64/AMD64)
make dev-full-start           # Start full stack in containers
make dev-full-stop            # Stop containers
make dev-full-logs            # View logs

# Hybrid mode (Mac ARM + infrastructure)
make local-dev-infra          # Infrastructure only
make local-dev-backend        # Backend with hot-reload
make local-dev-frontend       # Frontend with hot-reload
```

###Cloud Deployment Targets

```bash
# Cloud builds (AMD64-only)
make build-cloud-backend      # Build AMD64 backend locally
make build-cloud-frontend     # Build AMD64 frontend locally
make build-cloud-all          # Build both (slow on Mac!)

# Cloud build + push
make build-cloud-push-all     # Build + push to GHCR (slow on Mac!)

# Deployment
make deploy-roks-app          # Deploy to IBM ROKS (OpenShift)
make k8s-deploy-app           # Cloud-agnostic Kubernetes deploy
make k8s-status               # Check deployment status
make k8s-logs                 # View pod logs
```

### Deprecated Targets (Backward Compatible)

```bash
# Old names still work but show deprecation warnings
make build-multiarch-all      # → build-cloud-all
make build-multiarch-push-all # → build-cloud-push-all
```

## Recommended Workflows

### Daily Development (Mac or Linux)

```bash
# 1. Start infrastructure
make local-dev-infra

# 2. Start app with hot-reload
make local-dev-backend    # Terminal 1
make local-dev-frontend   # Terminal 2

# 3. Develop, test, iterate
# Changes auto-reload!

# 4. When ready, commit and push
git add . && git commit -m "feat: ..." && git push
```

### Production Deployment

```bash
# 1. Merge PR to main
# → GitHub Actions builds AMD64 images automatically

# 2. Deploy to cloud
make deploy-roks-app

# 3. Verify deployment
make k8s-status
make k8s-logs

# 4. Check pods running
kubectl get pods -n rag-modulo
```

### Emergency Local Build (If GitHub Actions is down)

```bash
# ⚠️ Only use if GitHub Actions unavailable
make build-cloud-push-all    # 13-21 min on Mac
make deploy-roks-app
```

## Cloud Platform Support

### Current Support

- ✅ **IBM ROKS** (Red Hat OpenShift on Kubernetes)
  - Deployment: `make deploy-roks-app`
  - Uses OpenShift Routes for ingress
  - Helm chart: `deployment/helm/rag-modulo/`

### Coming Soon

- 🔜 **AWS EKS** (Elastic Kubernetes Service)
  - Deployment: `make deploy-eks-app`
  - Uses Kubernetes Ingress

- 🔜 **Azure AKS** (Azure Kubernetes Service)
  - Deployment: `make deploy-aks-app`
  - Uses Kubernetes Ingress

- 🔜 **Google GKE** (Google Kubernetes Engine)
  - Deployment: `make deploy-gke-app`
  - Uses Kubernetes Ingress

## Architecture: Why This Works

### Platform-Agnostic Design

The system uses **3-layer architecture**:

1. **Layer 1**: Platform-agnostic targets
   - `build-backend`, `build-frontend`
   - Detect native platform automatically
   - Fast builds for local testing

2. **Layer 2**: Platform-type targets
   - `k8s-deploy-app` (cloud-agnostic Kubernetes)
   - `serverless-deploy-app` (cloud-agnostic serverless)
   - Use variables to configure cloud-specific behavior

3. **Layer 3**: Cloud-specific shortcuts
   - `deploy-roks-app` (IBM convenience wrapper)
   - `deploy-eks-app` (AWS convenience wrapper)
   - Preconfigure variables for specific clouds

### Helm Chart Abstraction

```yaml
# deployment/helm/rag-modulo/values.yaml
ingress:
  route:
    enabled: true      # For ROKS/OpenShift
  kubernetes:
    enabled: false      # For EKS/AKS/GKE
```

Single Helm chart deploys to any cloud!

## GitHub Actions Workflows

### `publish.yml` - Automatic Builds

**Triggers**: Every push to `main` that modifies code

**What it does**:
- Builds backend + frontend on native AMD64 runners
- Tags: `0.8.0`, `latest`, `1.0.<build_number>`
- Pushes to GHCR
- Uses GitHub Actions cache for speed

**No manual intervention needed!**

### `build-multiarch-images.yml` - Manual Trigger

**Triggers**: Manual workflow dispatch

**Usage**:
```bash
# Trigger via CLI
gh workflow run build-multiarch-images.yml -f push_to_registry=true

# Monitor progress
gh run watch

# Deploy when complete
make deploy-roks-app
```

## Troubleshooting

### "Build is very slow on my Mac"

**Problem**: Using `make build-cloud-push-all` on Mac ARM

**Solution**: Don't build locally! Use GitHub Actions:
```bash
git push  # Triggers automatic build
make deploy-roks-app
```

### "I need to test AMD64 image before pushing to production"

**Solution**: Use manual GitHub Actions workflow:
```bash
# Build with explicit tag
gh workflow run build-multiarch-images.yml \
  -f push_to_registry=true \
  -f version_tag=test-1.2.3

# Deploy test version
helm upgrade rag-modulo deployment/helm/rag-modulo/ \
  --set backend.image.tag=test-1.2.3
```

### "Docker buildx error on Mac"

**Problem**: Buildx multi-platform configuration issues

**Solution**: Reset Docker buildx:
```bash
docker buildx rm multiarch-builder || true
docker buildx create --name multiarch-builder --use
docker buildx inspect --bootstrap
```

## Best Practices

1. ✅ **DO**: Use `make dev-full-build` for local testing
2. ✅ **DO**: Let GitHub Actions build for cloud deployment
3. ✅ **DO**: Test locally before pushing to main
4. ❌ **DON'T**: Build AMD64 on Mac ARM unless urgent
5. ❌ **DON'T**: Skip testing locally before deploying
6. ❌ **DON'T**: Push untested images to production

## Performance Metrics

Based on actual testing (Nov 2024):

- **Mac ARM → ARM64**: 5-10 minutes (local testing)
- **Linux AMD64 → AMD64**: 5-10 minutes (local testing)
- **Mac ARM → AMD64 (QEMU)**: 13-21 minutes (not recommended)
- **GitHub Actions AMD64**: 10-15 minutes (recommended)
- **GHCR Image Push**: 3-6 minutes
- **Helm Deployment**: 2-5 minutes

**Total cloud deployment time**: ~15-25 minutes (code push → running in cloud)

## Related Documentation

- [Multi-Architecture Build Guide](MULTIARCH_BUILD_GUIDE.md) - GitHub Actions details
- [Kubernetes Deployment Guide](kubernetes.md) - Kubernetes specifics
- [IBM Cloud Deployment Analysis](ibm-cloud-deployment-analysis.md) - ROKS details
- [Terraform + Ansible Architecture](terraform-ansible-architecture.md) - Infrastructure as Code

## Migration Notes

**November 2024**: Makefile targets renamed for clarity

- `build-multiarch-*` → `build-cloud-*` (more accurate)
- Old names still work (backward compatible)
- Deprecation warnings guide users to new names

**Reason**: "multiarch" was misleading - we only build AMD64 for cloud, not ARM64+AMD64.
