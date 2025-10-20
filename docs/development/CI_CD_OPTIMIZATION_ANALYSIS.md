# CI/CD Optimization Analysis

## Executive Summary

**Current Issue**: PR #438 CI/CD taking 15-20+ minutes due to Docker builds on every PR.

**Root Cause**: `03-build-secure.yml` builds Docker images on PRs even when only code changes (not Dockerfile/dependencies).

**Recommendation**: Adopt IBM's `mcp-context-forge` strategy - separate fast PR checks from slow container builds.

---

## Current vs IBM Comparison

### Our Current Approach (RAG Modulo)

```yaml
# 03-build-secure.yml - Runs on EVERY PR (Lines 4-14)
on:
  pull_request:
    branches: [main]
    paths:
      - 'backend/Dockerfile.backend'
      - 'backend/pyproject.toml'
      - 'backend/poetry.lock'
      - 'frontend/Dockerfile.frontend'
      - 'frontend/package*.json'
      - 'docker-compose*.yml'
```

**Problem**: Path filters help, but still run when dependencies change (which is frequent).

**Timing Breakdown**:

- Lint (01-lint.yml): ~60s ✅ FAST
- Security Scan (02-security.yml): ~45s ✅ FAST
- **Docker Build (03-build-secure.yml): ~15-20 min** ❌ SLOW
- Unit Tests (04-pytest.yml): ~90s ✅ FAST
- Frontend Lint (07-frontend-lint.yml): ~27s ✅ FAST

**Total**: ~18-22 minutes per PR

---

### IBM's Approach (mcp-context-forge)

**Strategy**: Separate workflows based on speed/purpose

#### 1. Fast PR Checks (< 3 minutes)

```yaml
# pytest.yml - Python unit tests
# lint.yml - Code quality (autoflake, isort, black)
# lint-plugins.yml - Plugin-specific linting
# lint-web.yml - Frontend linting
# bandit.yml - Security linting
```

**Runs on**: Every PR
**Time**: 2-3 minutes total

#### 2. Full Build Pipeline (5-10 minutes)

```yaml
# full-build-pipeline.yml - Complete verification
# Runs: venv → format → test → lint → bandit → smoke → docker-build
```

**Runs on**: Push to main (after merge)
**Time**: 5-10 minutes

#### 3. Docker Security Scans (15-20 minutes)

```yaml
# docker-image.yml - Full security suite
# Hadolint → Dockle → Syft → Trivy → Grype → Cosign
```

**Runs on**:

- Push to main (post-merge)
- Weekly schedule (Tuesday 18:17 UTC)
- Manual trigger

**Time**: 15-20 minutes

---

## Key Learnings from IBM

### 1. **BuildKit Cache Strategy**

**IBM's Approach**:

```yaml
- name: 🔄 Restore BuildKit layer cache
  uses: actions/cache@v4
  with:
    path: /tmp/.buildx-cache
    key: ${{ runner.os }}-buildx-${{ github.sha }}
    restore-keys: ${{ runner.os }}-buildx-

- name: 🏗️ Build Docker image
  run: |
    docker buildx build \
      --cache-from type=local,src=/tmp/.buildx-cache \
      --cache-to type=local,dest=/tmp/.buildx-cache,mode=max \
      --load \
      .
```

**Our Approach** (line 115):

```yaml
# No external cache to avoid slow export - rely on BuildKit's internal cache
build-args: |
  BUILDKIT_INLINE_CACHE=1
```

**Recommendation**: Test IBM's approach - explicit cache may be faster than inline cache.

---

### 2. **Trivy Filesystem Scanning (No Docker Build Required!)**

**Answer to your question**: YES, you can run Trivy WITHOUT building containers!

**IBM Uses**:

```yaml
- name: 🛡️ Trivy vulnerability scan
  uses: aquasecurity/trivy-action@0.33.1
  with:
    image-ref: ${{ env.IMAGE_NAME }}:latest  # Image scan
    format: sarif
    severity: CRITICAL
```

**What we can do** (already partially implemented - line 226):

```yaml
- name: 🔍 Trivy - Filesystem Scan
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'              # ← No Docker build needed!
    scan-ref: backend/           # Scan source code directly
    format: sarif
    severity: 'CRITICAL,HIGH'
```

**Benefits**:

- ✅ No Docker build required (~15 min savings)
- ✅ Scans `pyproject.toml`, `poetry.lock`, `package.json` for CVEs
- ✅ Detects vulnerable dependencies BEFORE building image
- ✅ Can run on EVERY PR in < 30 seconds

---

### 3. **Grype as Alternative to Trivy**

IBM uses **both** Trivy and Grype:

```yaml
- name: 📥 Installing Grype CLI
  run: curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh

- name: 🔍 Grype vulnerability scan
  run: grype ${{ env.IMAGE_NAME }}:latest --scope all-layers --only-fixed
```

**Why both?**

- Trivy: Fast, RHEL/UBI-friendly
- Grype: More comprehensive database, better fix recommendations

**IBM's Note** (line 30):

```yaml
env:
  # Temporarily disable Trivy (RHEL 10 unsupported). Set to 'true' to re-enable.
  TRIVY_ENABLED: 'false'
```

They disabled Trivy due to RHEL 10 incompatibility - we should test Grype as backup.

---

### 4. **Image Signing with Cosign**

IBM signs all images with **key-less OIDC**:

```yaml
- name: 🔏 Sign & attest images
  env:
    COSIGN_EXPERIMENTAL: "1"
  run: |
    cosign sign --yes "$IMAGE_NAME:latest"
    cosign attest --yes \
                 --predicate sbom.spdx.json \
                 --type spdxjson \
                 "$IMAGE_NAME:latest"
```

**Benefits**:

- ✅ Cryptographic proof of authenticity
- ✅ SLSA compliance
- ✅ No key management (uses GitHub OIDC)

**Recommendation**: Add this for production images (not PRs).

---

## Recommended Optimization Strategy

### Phase 1: Immediate Wins (< 1 hour implementation)

#### A. Move Docker Builds to Post-Merge Only

**Change `03-build-secure.yml` trigger**:

```yaml
on:
  # Remove pull_request entirely
  push:
    branches: [main]
    # Always scan on merge to main
  schedule:
    # Weekly CVE scan every Tuesday at 6:17 PM UTC
    - cron: '17 18 * * 2'
  workflow_dispatch:  # Manual trigger option
```

**Add Trivy Filesystem Scan to `02-security.yml`** (runs on PRs):

```yaml
- name: 🔍 Trivy - Python Dependencies Scan
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    scan-ref: 'backend/'
    format: 'sarif'
    output: 'trivy-backend-deps.sarif'
    severity: 'CRITICAL,HIGH'
    scanners: 'vuln'  # Only scan for vulnerabilities, not misconfigurations

- name: 🔍 Trivy - Frontend Dependencies Scan
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    scan-ref: 'frontend/'
    format: 'sarif'
    output: 'trivy-frontend-deps.sarif'
    severity: 'CRITICAL,HIGH'
    scanners: 'vuln'
```

**Expected PR Time**: 2-3 minutes (down from 18-22 minutes)

---

#### B. Add Grype as Backup Scanner

```yaml
# In 03-build-secure.yml (post-merge only)
- name: 📥 Install Grype
  run: curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

- name: 🔍 Grype vulnerability scan
  run: |
    grype ${{ matrix.image_name }}:${{ github.sha }} \
          --scope all-layers \
          --only-fixed \
          --output sarif \
          --file grype-${{ matrix.service }}.sarif
```

---

### Phase 2: Performance Optimizations (< 2 hours)

#### A. Test BuildKit Cache Strategy

Replace inline cache with IBM's approach:

```yaml
- name: 🔄 Restore BuildKit cache
  uses: actions/cache@v4
  with:
    path: /tmp/.buildx-cache
    key: ${{ runner.os }}-buildx-${{ matrix.service }}-${{ hashFiles(format('{0}/Dockerfile.{1}', matrix.context, matrix.service), format('{0}/poetry.lock', matrix.context), format('{0}/package-lock.json', matrix.context)) }}
    restore-keys: |
      ${{ runner.os }}-buildx-${{ matrix.service }}-
      ${{ runner.os }}-buildx-

- name: 🏗️ Build Docker Image
  uses: docker/build-push-action@v5
  with:
    cache-from: type=local,src=/tmp/.buildx-cache
    cache-to: type=local,dest=/tmp/.buildx-cache-new,mode=max

# Move cache to prevent bloat
- name: Move cache
  run: |
    rm -rf /tmp/.buildx-cache
    mv /tmp/.buildx-cache-new /tmp/.buildx-cache
```

**Expected Speedup**: 30-50% on subsequent builds (15min → 7-10min)

---

#### B. Parallelize Security Scans

Currently sequential (line 127-253). Run Hadolint, Dockle, Trivy, Syft in parallel:

```yaml
jobs:
  hadolint:
    runs-on: ubuntu-latest
    steps: [...]

  build-image:
    runs-on: ubuntu-latest
    steps: [...]

  dockle:
    needs: build-image
    runs-on: ubuntu-latest
    steps: [...]

  trivy:
    needs: build-image
    runs-on: ubuntu-latest
    steps: [...]

  syft:
    needs: build-image
    runs-on: ubuntu-latest
    steps: [...]
```

**Expected Speedup**: 40% (scans run concurrently instead of sequentially)

---

### Phase 3: Advanced Features (< 4 hours)

#### A. Image Signing with Cosign

```yaml
- name: 📥 Install Cosign
  if: github.ref == 'refs/heads/main'
  uses: sigstore/cosign-installer@v3.9.2

- name: 🔏 Sign & attest images
  if: github.ref == 'refs/heads/main'
  env:
    COSIGN_EXPERIMENTAL: "1"
  run: |
    cosign sign --yes ${{ matrix.ghcr_image }}:${{ github.sha }}
    cosign attest --yes \
                 --predicate sbom-${{ matrix.service }}.spdx.json \
                 --type spdxjson \
                 ${{ matrix.ghcr_image }}:${{ github.sha }}
```

#### B. Conditional Docker Builds

Only build if source code changes (not just workflow changes):

```yaml
- name: Check if Docker build needed
  id: check_build
  run: |
    CHANGED_FILES=$(git diff --name-only ${{ github.event.before }} ${{ github.sha }})
    if echo "$CHANGED_FILES" | grep -qE '^(backend|frontend)/'; then
      echo "build_needed=true" >> $GITHUB_OUTPUT
    else
      echo "build_needed=false" >> $GITHUB_OUTPUT
    fi

- name: Build Docker image
  if: steps.check_build.outputs.build_needed == 'true'
  [...]
```

---

## IBM vs RAG Modulo: Side-by-Side

| Aspect | IBM mcp-context-forge | RAG Modulo (Current) | Recommendation |
|--------|----------------------|---------------------|----------------|
| **PR Duration** | 2-3 min | 18-22 min | ✅ Adopt IBM approach |
| **Docker Builds** | Post-merge only | Every PR (path-filtered) | ✅ Move to post-merge |
| **Trivy Filesystem** | Not used | Partial (line 226) | ✅ Use on every PR |
| **BuildKit Cache** | Explicit cache restore | Inline cache | ⚠️ Test IBM's approach |
| **Vulnerability Scanners** | Trivy + Grype | Trivy only | ✅ Add Grype backup |
| **Image Signing** | Cosign (OIDC) | Not implemented | ✅ Add for production |
| **Parallel Scans** | Yes | No (sequential) | ✅ Parallelize |
| **Weekly Scans** | Tuesday 18:17 UTC | Tuesday 18:17 UTC | ✅ Already aligned |

---

## Expected Performance Impact

### Current (PR #438)

```
01-lint.yml:          ~60s
02-security.yml:      ~45s
03-build-secure.yml:  ~15-20 min  ← BOTTLENECK
04-pytest.yml:        ~90s
07-frontend-lint.yml: ~27s
────────────────────────────────
Total:                ~18-22 min
```

### After Phase 1 (Immediate Wins)

```
01-lint.yml:          ~60s
02-security.yml:      ~45s (+ Trivy fs scan: +30s = 75s total)
04-pytest.yml:        ~90s
07-frontend-lint.yml: ~27s
────────────────────────────────
Total:                ~3-4 min  ✅ 85% FASTER

# Docker builds move to post-merge (developers don't wait)
03-build-secure.yml:  Runs AFTER merge in background
```

### After Phase 2 (Optimizations)

```
Post-merge builds:    ~7-10 min (down from 15-20 min)
✅ 50% faster container builds
```

---

## Implementation Plan

### Week 1: Immediate Wins (Recommended NOW)

**Day 1**: Move Docker builds to post-merge only

```bash
# Edit .github/workflows/03-build-secure.yml
# Remove pull_request trigger
# Add filesystem Trivy scans to 02-security.yml
```

**Day 2**: Add Grype scanner

```bash
# Add Grype to 03-build-secure.yml
# Test both Trivy and Grype on sample images
```

**Day 3**: Test and validate

```bash
# Create test PR
# Verify fast PR checks (< 4 min)
# Verify post-merge builds work
```

### Week 2: Performance Optimizations

**Day 1-2**: Implement BuildKit cache strategy
**Day 3-4**: Parallelize security scans
**Day 5**: Performance testing and comparison

### Week 3: Advanced Features

**Day 1-2**: Add Cosign image signing
**Day 3-4**: Implement conditional builds
**Day 5**: Documentation and rollout

---

## Questions Answered

### Q: Do we need to build Docker images on every PR?

**A**: NO. IBM's approach proves you can:

1. Run Trivy **filesystem scans** on PRs (no Docker build needed)
2. Build containers **only** on merge to main
3. Run weekly scheduled scans for new CVEs

**Savings**: ~15-18 minutes per PR

---

### Q: Can we do Trivy security scan without building a container?

**A**: YES! Trivy supports multiple scan types:

```yaml
# 1. Filesystem scan (no container needed)
trivy fs --scanners vuln backend/

# 2. Config scan (IaC security)
trivy config --format sarif terraform/

# 3. Repository scan (end-to-end)
trivy repo --scanners vuln,secret .
```

**Already in your workflow** (line 226-253):

```yaml
- name: 🔍 Trivy - Filesystem Scan
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'  # ← No Docker build!
    scan-ref: ${{ matrix.context }}
```

**Recommendation**: Move this to run on EVERY PR in `02-security.yml`

---

## Cost Analysis

### Current Costs (Estimated)

```
GitHub Actions minutes per PR: ~20 min
PRs per month: ~40
Monthly usage: 800 min

At current rate:
- Free tier: 2,000 min/month (exhausted in ~2.5 weeks)
- Overage: $0.008/min for private repos
- Monthly overage cost: ~$6-8
```

### After Optimization

```
GitHub Actions minutes per PR: ~3-4 min
PRs per month: ~40
Monthly usage: 120-160 min

Results:
- Well within free tier
- No overage costs
- Faster developer feedback
```

**Savings**: ~640 min/month (~$5-7 saved)

---

## Monitoring & Validation

### Metrics to Track

```yaml
# Add to workflow summaries
- name: 📊 Performance Metrics
  run: |
    echo "### ⏱️ Performance" >> $GITHUB_STEP_SUMMARY
    echo "- Workflow duration: ${{ job.duration }}" >> $GITHUB_STEP_SUMMARY
    echo "- Cache hit rate: ${{ steps.cache.outputs.cache-hit }}" >> $GITHUB_STEP_SUMMARY
```

### Success Criteria

- ✅ PR checks complete in < 5 minutes
- ✅ Post-merge builds complete in < 10 minutes
- ✅ No increase in missed vulnerabilities
- ✅ Developer satisfaction improves

---

## References

- IBM mcp-context-forge: <https://github.com/IBM/mcp-context-forge>
- Trivy Docs: <https://aquasecurity.github.io/trivy/>
- Grype Docs: <https://github.com/anchore/grype>
- Cosign Docs: <https://docs.sigstore.dev/cosign/overview/>
- Docker BuildKit Cache: <https://docs.docker.com/build/cache/>

---

## Appendix: Example Workflow

```yaml
# .github/workflows/pr-checks.yml (NEW - Fast PR checks)
name: PR Checks (Fast)

on:
  pull_request:
    branches: [main]

jobs:
  quick-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Trivy filesystem scan (no Docker build)
      - name: 🔍 Scan Dependencies
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'

      # Existing fast checks
      - name: Run Lint
        run: make lint

      - name: Run Tests
        run: make test-unit-fast

# Expected duration: 2-3 minutes
```

---

**Generated**: 2025-10-19
**Author**: Claude Code + Analysis of IBM mcp-context-forge
**Status**: Ready for implementation
