# Versioning Strategy

**Last Updated:** January 2025  
**Status:** ✅ Active

---

## Overview

RAG Modulo uses a unified versioning strategy that flows from `.env` → `Makefile` → `GitHub Actions`, ensuring consistent versioning across local development and CI/CD pipelines.

## Table of Contents

- [Version Flow](#version-flow)
- [Setting the Version](#setting-the-version)
- [Version Priority](#version-priority)
- [Semantic Versioning](#semantic-versioning)
- [Docker Image Tagging](#docker-image-tagging)
- [Release Process](#release-process)
- [Best Practices](#best-practices)

---

## Version Flow

The version flows through the system in this order:

```
.env (PROJECT_VERSION=0.8.0)
  ↓
Makefile (PROJECT_VERSION ?= 1.0.0)  # .env overrides default
  ↓
GitHub Actions (reads from .env or Makefile)
  ↓
Docker Images (tagged with version)
```

### How It Works

1. **`.env` file** (if exists) sets `PROJECT_VERSION=0.8.0`
2. **Makefile** includes `.env` and uses it if present, otherwise defaults to `1.0.0`
3. **GitHub Actions** reads from `.env` first, then Makefile, then other sources
4. **Docker images** are tagged with the determined version

---

## Setting the Version

### Option 1: `.env` File (Recommended for Local Development)

Add to your `.env` file:

```bash
PROJECT_VERSION=0.8.0
```

**How Makefile picks it up:**

```makefile
# Include environment variables from .env file if it exists
-include .env
ifneq (,$(wildcard .env))
export $(shell sed 's/=.*//' .env)
endif

# Project info
PROJECT_VERSION ?= 1.0.0  # Default, but .env overrides this
```

The `?=` operator means "assign only if not already set", so `.env` values take precedence.

### Option 2: GitHub Repository Variable (Recommended for CI/CD)

1. Go to **Settings** → **Secrets and variables** → **Actions** → **Variables**
2. Add variable: `PROJECT_VERSION` = `0.8.0`

This is useful when `.env` is gitignored and not available in CI/CD.

### Option 3: Git Tag (For Releases)

```bash
# Create and push a release tag
git tag v1.0.0
git push origin v1.0.0
```

This automatically triggers a release build and uses the tag as the version.

---

## Version Priority

The system determines version using this priority order (highest to lowest):

1. **Git tag** (`v1.0.0`) - Highest priority
   - Used when you push a tag like `v1.0.0`
   - Automatically triggers release workflow

2. **GitHub variable** `PROJECT_VERSION`
   - Set in repository settings
   - Useful for CI/CD when `.env` is not available

3. **`.env` file** (`PROJECT_VERSION=0.8.0`)
   - Matches Makefile behavior
   - Used for local development

4. **Makefile default** (`PROJECT_VERSION ?= 1.0.0`)
   - Fallback if `.env` doesn't exist
   - Defined in `Makefile` line 26

5. **`pyproject.toml`** (`version = "1.0.0"`)
   - Python package version
   - Fallback if Makefile doesn't have PROJECT_VERSION

6. **Commit SHA** (final fallback)
   - Used for development builds
   - Ensures every build has a unique identifier

### Example Priority Resolution

```bash
# Scenario 1: .env exists with PROJECT_VERSION=0.8.0
# Result: Uses 0.8.0

# Scenario 2: .env doesn't exist, Makefile has PROJECT_VERSION ?= 1.0.0
# Result: Uses 1.0.0

# Scenario 3: Git tag v1.2.3 is pushed
# Result: Uses v1.2.3 (overrides everything)

# Scenario 4: GitHub variable PROJECT_VERSION=0.9.0 is set
# Result: Uses 0.9.0 (if no git tag)
```

---

## Semantic Versioning

RAG Modulo follows [Semantic Versioning](https://semver.org/) (SemVer):

```
MAJOR.MINOR.PATCH
```

### Version Number Meanings

- **MAJOR** (1.0.0): Breaking changes, incompatible API changes
- **MINOR** (0.1.0): New features, backward-compatible
- **PATCH** (0.0.1): Bug fixes, backward-compatible

### Examples

```bash
# Major release (breaking changes)
PROJECT_VERSION=2.0.0

# Minor release (new features)
PROJECT_VERSION=1.1.0

# Patch release (bug fixes)
PROJECT_VERSION=1.0.1

# Pre-release
PROJECT_VERSION=1.0.0-beta.1
```

### Git Tags Format

When creating release tags, use the `v` prefix:

```bash
# Correct
git tag v1.0.0
git tag v1.2.3
git tag v2.0.0-beta.1

# Incorrect (workflow won't recognize)
git tag 1.0.0
git tag release-1.0.0
```

---

## Docker Image Tagging

### Tag Strategy

Each Docker image is tagged with **three tags**:

1. **Commit SHA** - Immutable, traceable
2. **Version Tag** - Semantic version or commit SHA
3. **Latest** - Always points to most recent build

### Tag Examples

**Regular Development Build:**
```bash
# .env has PROJECT_VERSION=0.8.0
# Images tagged with:
- us.icr.io/rag_modulo/rag-modulo-backend:abc123def456... (commit SHA)
- us.icr.io/rag_modulo/rag-modulo-backend:0.8.0           (from .env)
- us.icr.io/rag_modulo/rag-modulo-backend:latest
```

**Release Build:**
```bash
# git tag v1.2.3
# Images tagged with:
- us.icr.io/rag_modulo/rag-modulo-backend:abc123def456... (commit SHA)
- us.icr.io/rag_modulo/rag-modulo-backend:v1.2.3          (from git tag)
- us.icr.io/rag_modulo/rag-modulo-backend:latest
```

### Tag Usage

| Tag Type | Use For | Example |
|----------|---------|---------|
| Commit SHA | Production deployments | `abc123def456...` |
| Version | Releases, easy reference | `0.8.0`, `v1.0.0` |
| Latest | Quick reference only | `latest` |

⚠️ **Important:** Never deploy from `latest` in production! It's mutable and can change.

---

## Release Process

### Creating a Release

#### Step 1: Update Version

```bash
# Update .env file
echo "PROJECT_VERSION=1.0.0" >> .env

# Or update Makefile default
# Edit Makefile line 26:
# PROJECT_VERSION ?= 1.0.0
```

#### Step 2: Commit Changes

```bash
git add .env Makefile
git commit -m "chore: Bump version to 1.0.0"
git push origin main
```

#### Step 3: Create Release Tag

```bash
# Create and push tag
git tag v1.0.0
git push origin v1.0.0
```

This automatically:
- Triggers release workflow
- Builds images with `v1.0.0` tag
- Deploys to production (if configured)

#### Step 4: Create GitHub Release (Optional)

1. Go to **Releases** → **Draft a new release**
2. Select tag `v1.0.0`
3. Add release notes
4. Publish release

---

## Best Practices

### Version Management

1. **Use `.env` for local development**
   ```bash
   PROJECT_VERSION=0.8.0
   ```

2. **Update version before major changes**
   - Major changes → bump MAJOR
   - New features → bump MINOR
   - Bug fixes → bump PATCH

3. **Use git tags for releases**
   - Tag format: `v1.0.0`
   - Tag after merging to main
   - Include release notes

4. **Keep versions in sync**
   - `.env` → `Makefile` → `pyproject.toml`
   - Update all when releasing

### Version Consistency

Ensure version is consistent across:

- ✅ `.env` file (if used)
- ✅ `Makefile` (default)
- ✅ `pyproject.toml` (Python package version)
- ✅ GitHub repository variable (for CI/CD)
- ✅ Git tags (for releases)

### Versioning Workflow

```bash
# 1. Update version in .env
echo "PROJECT_VERSION=0.9.0" >> .env

# 2. Test locally
make build-all
make test-all

# 3. Commit and push
git add .env
git commit -m "chore: Bump version to 0.9.0"
git push origin main

# 4. Create release tag
git tag v0.9.0
git push origin v0.9.0

# 5. Verify deployment
# Check GitHub Actions workflow
# Verify images are tagged correctly
```

---

## Troubleshooting

### Version Not Being Used

**Problem:** Workflow uses commit SHA instead of PROJECT_VERSION

**Solutions:**
1. Check if `.env` file exists and contains `PROJECT_VERSION=0.8.0`
2. Verify Makefile has `PROJECT_VERSION ?= 1.0.0` default
3. Set `PROJECT_VERSION` as GitHub repository variable
4. Check workflow logs for version extraction step

### Version Mismatch

**Problem:** Different versions in different places

**Solution:**
```bash
# Check all version sources
grep -r "PROJECT_VERSION\|version" .env Makefile pyproject.toml

# Update to match
# 1. Update .env
# 2. Update Makefile default
# 3. Update pyproject.toml
# 4. Commit changes
```

### Git Tag Not Recognized

**Problem:** Workflow doesn't use git tag version

**Solution:**
- Ensure tag format is `v*.*.*` (e.g., `v1.0.0`)
- Check workflow triggers include `tags: ["v*.*.*"]`
- Verify tag was pushed: `git push origin v1.0.0`

---

## Related Documentation

- [CI/CD Workflow](../deployment/ci-cd-workflow.md) - Complete workflow documentation
- [Deployment Guide](../deployment/index.md) - Deployment overview
- [Changelog](../changelog.md) - Version history and changes

---

## Summary

The versioning strategy provides:

- ✅ **Single source of truth**: `.env` → `Makefile` → `GitHub Actions`
- ✅ **Flexible configuration**: Multiple ways to set version
- ✅ **Semantic versioning**: Clear version meaning
- ✅ **Consistent tagging**: Docker images tagged correctly
- ✅ **Release automation**: Git tags trigger releases

This ensures consistent, traceable versioning across all environments.

