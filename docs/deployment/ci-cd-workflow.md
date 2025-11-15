# CI/CD Workflow and Versioning Strategy

**Last Updated:** January 2025  
**Status:** ✅ Active

---

## Overview

This document describes the CI/CD workflow for deploying RAG Modulo to IBM Cloud Code Engine, including versioning strategy, image tagging, and registry management.

## Table of Contents

- [Workflow Overview](#workflow-overview)
- [Versioning Strategy](#versioning-strategy)
- [Docker Image Tagging](#docker-image-tagging)
- [Image Cleanup and Retention](#image-cleanup-and-retention)
- [Workflow Jobs](#workflow-jobs)
- [Best Practices](#best-practices)

---

## Workflow Overview

The deployment workflow (`.github/workflows/deploy_complete_app.yml`) provides:

- ✅ **Automated builds** on push to main branch
- ✅ **Daily scheduled builds** (2 AM UTC)
- ✅ **Manual deployment** with environment selection
- ✅ **Release builds** triggered by git tags
- ✅ **Security scanning** with Trivy
- ✅ **Idempotent deployments** (safe to run multiple times)
- ✅ **Automatic image cleanup** to manage registry storage

### Workflow Triggers

```yaml
on:
  workflow_dispatch:    # Manual deployment
  schedule:             # Daily builds at 2 AM UTC
  push:
    branches: [main]    # Automatic on code changes
    tags: ["v*.*.*"]    # Release builds
  release:              # GitHub releases
    types: [published]
```

---

## Versioning Strategy

### Single Source of Truth

The project uses a unified versioning strategy that flows from `.env` → `Makefile` → `GitHub Actions`:

```
.env (PROJECT_VERSION=0.8.0)
  ↓
Makefile (PROJECT_VERSION ?= 1.0.0)  # .env overrides default
  ↓
GitHub Actions (reads from .env or Makefile)
```

### Version Priority Order

The workflow determines version using this priority:

1. **Git tag** (`v1.0.0`) - Highest priority (for releases)
2. **GitHub variable** `PROJECT_VERSION` (if set in repository settings)
3. **`.env` file** (`PROJECT_VERSION=0.8.0`) - Matches Makefile behavior
4. **Makefile default** (`PROJECT_VERSION ?= 1.0.0`)
5. **`pyproject.toml`** (`version = "1.0.0"`)
6. **Commit SHA** (fallback for development builds)

### Setting the Version

#### Option 1: `.env` File (Recommended for Local Development)

Add to your `.env` file:

```bash
PROJECT_VERSION=0.8.0
```

The Makefile automatically includes `.env`:

```makefile
-include .env
ifneq (,$(wildcard .env))
export $(shell sed 's/=.*//' .env)
endif
```

#### Option 2: GitHub Repository Variable (Recommended for CI/CD)

1. Go to **Settings** → **Secrets and variables** → **Actions** → **Variables**
2. Add variable: `PROJECT_VERSION` = `0.8.0`

#### Option 3: Git Tag (For Releases)

```bash
# Create and push a release tag
git tag v1.0.0
git push origin v1.0.0
```

This automatically triggers a release build with version `v1.0.0`.

### Version Examples

**Regular Development Build:**
```bash
# .env has PROJECT_VERSION=0.8.0
# Images tagged with:
- us.icr.io/rag_modulo/rag-modulo-backend:abc123... (commit SHA)
- us.icr.io/rag_modulo/rag-modulo-backend:0.8.0     (from .env)
- us.icr.io/rag_modulo/rag-modulo-backend:latest
```

**Release Build:**
```bash
# git tag v1.2.3
# Images tagged with:
- us.icr.io/rag_modulo/rag-modulo-backend:abc123... (commit SHA)
- us.icr.io/rag_modulo/rag-modulo-backend:v1.2.3    (from git tag)
- us.icr.io/rag_modulo/rag-modulo-backend:latest
```

---

## Docker Image Tagging

### Tagging Strategy

Each Docker image is tagged with **three tags**:

1. **Commit SHA** - Immutable, traceable (e.g., `abc123def456...`)
2. **Version Tag** - Semantic version or commit SHA (e.g., `0.8.0` or `v1.0.0`)
3. **Latest** - Always points to most recent build (e.g., `latest`)

### Tag Types

| Tag Type | Purpose | Used For | Example |
|----------|---------|----------|---------|
| Commit SHA | Immutable, traceable | Production deployments | `abc123def456...` |
| Version | Semantic versioning | Releases, easy reference | `0.8.0`, `v1.0.0` |
| Latest | Convenience | Quick reference, testing | `latest` |

### Important Notes

⚠️ **Never deploy from `latest` in production!**

- `latest` is **mutable** and can change with each build
- Always use **commit SHA** or **version tags** for production deployments
- `latest` is for convenience only (quick lookups, testing)

### Image Naming Convention

```
{ICR_REGION}.icr.io/{CR_NAMESPACE}/{APP_NAME}:{TAG}
```

**Example:**
```
us.icr.io/rag_modulo/rag-modulo-backend:0.8.0
us.icr.io/rag_modulo/rag-modulo-backend:abc123def456...
us.icr.io/rag_modulo/rag-modulo-backend:latest
```

---

## Image Cleanup and Retention

### Automatic Cleanup

To prevent registry bloat from daily builds, the workflow includes an automatic cleanup job that:

- ✅ Runs on scheduled builds and manual workflow dispatch
- ✅ Keeps the last **30 images** (configurable)
- ✅ Only deletes **commit SHA tags** (preserves version tags and `latest`)
- ✅ Prevents storage issues from accumulating old images

### Retention Configuration

Set the retention count via GitHub repository variable:

1. Go to **Settings** → **Secrets and variables** → **Actions** → **Variables**
2. Add variable: `IMAGE_RETENTION_COUNT` = `30` (default: 30)

### What Gets Deleted

**Deleted:**
- Old commit SHA tags beyond retention limit (e.g., `abc123...`, `def456...`)

**Preserved:**
- ✅ All version tags (`v1.0.0`, `v1.2.3`, `0.8.0`, etc.)
- ✅ `latest` tag
- ✅ Recent commit SHA tags (last 30)

### Cleanup Example

```bash
# Before cleanup: 50 images
# After cleanup (retention=30): 30 images + version tags + latest

# Kept:
- us.icr.io/rag_modulo/rag-modulo-backend:v1.0.0  ✅
- us.icr.io/rag_modulo/rag-modulo-backend:0.8.0  ✅
- us.icr.io/rag_modulo/rag-modulo-backend:latest  ✅
- us.icr.io/rag_modulo/rag-modulo-backend:abc123... (last 30) ✅

# Deleted:
- us.icr.io/rag_modulo/rag-modulo-backend:old123... ❌
- us.icr.io/rag_modulo/rag-modulo-backend:old456... ❌
```

---

## Workflow Jobs

### Job Flow

```
deploy-infrastructure
    ↓
build-and-push-backend ──→ security-scan-backend ──→ deploy-backend
build-and-push-frontend ──→ security-scan-frontend ──→ deploy-frontend
    ↓
cleanup-old-images (optional)
    ↓
smoke-test
```

### Job Descriptions

#### 1. `deploy-infrastructure`

- Deploys core infrastructure (PostgreSQL, MinIO, Milvus, etcd)
- Creates Code Engine project (handles soft-deleted projects)
- **Outputs:** `project_name` (used by other jobs)

#### 2. `build-and-push-backend` / `build-and-push-frontend`

- Builds Docker images with multi-stage builds
- Tags images with commit SHA, version, and `latest`
- Pushes to IBM Cloud Container Registry
- Verifies images were pushed successfully
- **Timeouts:** 30 min (backend), 20 min (frontend)

#### 3. `security-scan-backend` / `security-scan-frontend`

- Pulls images from registry
- Scans with Trivy for vulnerabilities
- Uploads SARIF results to GitHub Security tab
- **Non-blocking:** Reports vulnerabilities without failing deployment

#### 4. `deploy-backend` / `deploy-frontend`

- Verifies image exists before deployment
- Creates or updates Code Engine applications (idempotent)
- Configures environment variables and scaling
- **Idempotent:** Safe to run multiple times

#### 5. `cleanup-old-images`

- Removes old commit SHA tags beyond retention limit
- Preserves version tags and `latest`
- Runs on scheduled builds and manual dispatch

#### 6. `smoke-test`

- Waits for apps to be ready
- Tests backend health endpoint
- Tests frontend availability
- Validates complete application deployment
- **Retries:** 5 attempts with exponential backoff

---

## Best Practices

### Version Management

1. **Use `.env` for local development**
   ```bash
   PROJECT_VERSION=0.8.0
   ```

2. **Use GitHub variables for CI/CD**
   - Set `PROJECT_VERSION` in repository variables
   - Or commit `.env` file (if it doesn't contain secrets)

3. **Use git tags for releases**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

### Image Tagging

1. **Always deploy from commit SHA or version tags**
   - Never use `latest` for production
   - Commit SHA ensures exact reproducibility

2. **Tag releases with semantic versions**
   - Use `v1.0.0` format for releases
   - Makes it easy to identify and rollback

3. **Keep version tags forever**
   - Version tags are never deleted by cleanup
   - Safe for long-term reference

### Registry Management

1. **Configure retention appropriately**
   - Default: 30 images
   - Adjust based on build frequency and storage limits

2. **Monitor registry storage**
   - Check IBM Cloud Container Registry usage
   - Adjust `IMAGE_RETENTION_COUNT` if needed

3. **Use version tags for important builds**
   - Version tags are never cleaned up
   - Useful for marking milestones

### Deployment

1. **Run workflows idempotently**
   - Safe to re-run failed workflows
   - Updates existing resources instead of creating duplicates

2. **Verify before deploying**
   - Workflow verifies images exist before deployment
   - Prevents "404 Not Found" errors

3. **Monitor deployment health**
   - Smoke tests validate deployment success
   - Check logs if health checks fail

---

## Troubleshooting

### Version Not Found

**Problem:** Workflow uses commit SHA instead of PROJECT_VERSION

**Solutions:**
1. Check if `.env` file exists and contains `PROJECT_VERSION=0.8.0`
2. Set `PROJECT_VERSION` as GitHub repository variable
3. Verify Makefile has `PROJECT_VERSION ?= 1.0.0` default

### Image Not Found in Registry

**Problem:** Deployment fails with "404 Not Found"

**Solutions:**
1. Check build job logs - did image push succeed?
2. Verify ICR authentication is working
3. Check image tags match between build and deploy jobs
4. Ensure image verification step passes

### Registry Storage Full

**Problem:** Registry running out of space

**Solutions:**
1. Reduce `IMAGE_RETENTION_COUNT` (default: 30)
2. Manually delete old images via IBM Cloud console
3. Ensure cleanup job is running (check scheduled builds)

### Deployment Fails with "Already Exists"

**Problem:** Workflow fails because resource already exists

**Solution:**
- This shouldn't happen - workflow is idempotent
- If it does, check the update logic in deploy jobs
- Workflow should update existing resources, not create new ones

---

## Related Documentation

- [IBM Cloud Code Engine Deployment](ibm-cloud-code-engine.md)
- [Production Deployment](production.md)
- [Workflow Fixes Summary](WORKFLOW_FIXES_SUMMARY.md)
- [Local Testing Solution](ACT_LOCAL_TESTING_SOLUTION.md)

---

## Summary

The CI/CD workflow provides:

- ✅ **Unified versioning** from `.env` → `Makefile` → `GitHub Actions`
- ✅ **Flexible tagging** with commit SHA, version, and `latest`
- ✅ **Automatic cleanup** to manage registry storage
- ✅ **Idempotent deployments** safe to run multiple times
- ✅ **Security scanning** with Trivy
- ✅ **Health validation** with smoke tests

This ensures consistent, traceable, and maintainable deployments to IBM Cloud Code Engine.

