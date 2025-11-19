# Multi-Architecture Docker Build Guide

## Overview

This guide explains how to build Docker images for RAG Modulo that run on AMD64 (x86_64) architecture, which is required for deployment to IBM Cloud ROKS (Red Hat OpenShift Kubernetes Service).

## Problem Statement

### The Challenge

When building Docker images on **ARM64 Macs** (Apple Silicon M1/M2/M3) for deployment to **AMD64 cloud infrastructure**, there are two approaches:

1. **Cross-platform builds with QEMU emulation** (local Mac)
   - ❌ **Very slow**: 2-3+ hours per build
   - ❌ Uses Mac resources continuously
   - ❌ Requires complex Docker buildx configuration
   - ⚠️ CPU instruction emulation overhead (10-50x slower)

2. **Native AMD64 builds** (GitHub Actions)
   - ✅ **Fast**: 10-15 minutes per build
   - ✅ Runs on GitHub's AMD64 infrastructure
   - ✅ No emulation overhead
   - ✅ Automatic caching and layer optimization

## Solution: GitHub Actions Workflows

We provide two workflows for building Docker images:

### 1. `publish.yml` - Automatic Builds on Main Branch

**Triggers**: Automatically on every push to `main` that modifies backend or frontend code

**What it does**:

- Builds both backend and frontend images
- Tags with multiple versions:
  - `1.0.<run_number>` (incremental build number)
  - `0.8.0` (current release version)
  - `latest` (always points to most recent)
- Pushes to GitHub Container Registry (GHCR)
- Uses GitHub Actions cache for faster rebuilds

**Usage**: No manual intervention needed - just merge code to `main`

### 2. `build-multiarch-images.yml` - Manual Build Trigger

**Triggers**: Manual workflow dispatch (for testing or rebuilding)

**What it does**:

- Builds backend and frontend separately
- Explicitly targets `linux/amd64` platform
- Supports manual version tagging
- Useful for testing before deployment

**Usage**:

```bash
# Trigger via GitHub CLI
gh workflow run build-multiarch-images.yml -f push_to_registry=true

# Or via GitHub UI:
# Actions → Build Multi-Architecture Docker Images → Run workflow
```

## Quick Start

### For Developers

**Normal development workflow** (code changes):

1. Develop locally as usual
2. Create PR and merge to `main`
3. `publish.yml` automatically builds and pushes images
4. Deploy using `make remote-deploy-app-only-dev`

**For manual testing** (rebuild without code changes):

```bash
# Trigger manual build
gh workflow run build-multiarch-images.yml -f push_to_registry=true

# Monitor progress
gh run watch

# Deploy once complete
make remote-deploy-app-only-dev
```

### For Deployment

Images are available at:

- Backend: `ghcr.io/manavgup/rag_modulo/backend:0.8.0`
- Frontend: `ghcr.io/manavgup/rag_modulo/frontend:0.8.0`

Helm deployment automatically pulls these images when you run:

```bash
make remote-deploy-dev  # Full deployment (infrastructure + app)
# OR
make remote-deploy-app-only-dev  # App deployment only
```

## Local Development (Optional)

If you need to build locally (not recommended):

```bash
# 1. Ensure Docker buildx is configured
docker buildx create --name multiplatform \
  --driver docker-container \
  --driver-opt network=host \
  --buildkitd-flags '--allow-insecure-entitlement security.insecure --allow-insecure-entitlement network.host' \
  --use \
  --bootstrap

# 2. Build and push (takes 2-3 hours)
make build-push-all

# 3. Monitor progress
tail -f /tmp/build-output.log
```

**Note**: Local builds are **not recommended** due to the extreme slowdown from QEMU emulation.

## Architecture Details

### Why AMD64?

IBM Cloud ROKS workers use AMD64 (x86_64) processors:

- Worker flavor: `bx2.4x16` (Intel/AMD based)
- Container runtime expects AMD64 binaries
- ARM64 images will not run on these workers

### Build Process

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions (AMD64)                   │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐                      │
│  │   Frontend   │    │   Backend    │                      │
│  │   Build      │    │   Build      │                      │
│  └──────┬───────┘    └──────┬───────┘                      │
│         │                   │                               │
│         └─────────┬─────────┘                               │
│                   │                                          │
│                   ▼                                          │
│         ┌─────────────────────┐                            │
│         │       Push to       │                            │
│         │  GHCR (ghcr.io)    │                            │
│         └─────────┬───────────┘                            │
└───────────────────┼──────────────────────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   ROKS Cluster       │
         │   (AMD64 Workers)    │
         │                      │
         │  • Backend Pods      │
         │  • Frontend Pods     │
         │  • PostgreSQL        │
         │  • Milvus            │
         └──────────────────────┘
```

## Troubleshooting

### Build Failures

**Problem**: GitHub Actions build fails with "out of space"
**Solution**: Builds include automatic cleanup - check logs for specific errors

**Problem**: Local build extremely slow
**Solution**: Use GitHub Actions workflows instead - 10x faster

### Image Not Found

**Problem**: `ImagePullBackOff` error in Kubernetes
**Solution**:

1. Check if images exist: `docker manifest inspect ghcr.io/manavgup/rag_modulo/backend:0.8.0`
2. Ensure workflow completed successfully
3. Verify GHCR credentials in cluster

### Wrong Architecture

**Problem**: Container exits with "exec format error"
**Solution**: Image was built for wrong architecture. Rebuild with `platforms: linux/amd64`

## Performance Comparison

| Method | Time | CPU Usage | Network | Reliability |
|--------|------|-----------|---------|-------------|
| **Local (QEMU)** | 2-3 hours | 100% Mac | Low | Medium |
| **GitHub Actions** | 10-15 min | 0% Mac | High | High |
| **Factor** | **12-18x faster** | **0% overhead** | N/A | Higher |

## Best Practices

1. **Always use GitHub Actions** for production builds
2. **Tag images properly**: Use version tags (0.8.0) not just `latest`
3. **Test locally first**: Use `make local-dev-backend` for iteration
4. **Monitor builds**: Use `gh run watch` to track progress
5. **Cache effectively**: GitHub Actions cache speeds up rebuilds significantly

## Related Documentation

- [Kubernetes Deployment Guide](./KUBERNETES_DEPLOYMENT_GUIDE.md)
- [Makefile Integration](./MAKEFILE_INTEGRATION_SUMMARY.md)
- [CI/CD Workflows](../../.github/workflows/)

## See Also

- Docker Buildx: <https://docs.docker.com/build/buildx/>
- GitHub Container Registry: <https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry>
- Multi-platform builds: <https://docs.docker.com/build/building/multi-platform/>
