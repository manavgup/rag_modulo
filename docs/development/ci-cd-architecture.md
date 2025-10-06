# CI/CD Pipeline Architecture

**Last Updated**: October 6, 2025
**Status**: Under redesign (see Issue #324)
**Inspiration**: [IBM MCP Context Forge](https://github.com/IBM/mcp-context-forge)

## Overview

RAG Modulo's CI/CD pipeline ensures code quality, security, and reliability through automated testing, linting, security scanning, and deployment validation.

## Current Architecture (As of v1.0)

### Workflow Inventory

| Workflow | Purpose | Triggers | Duration |
|----------|---------|----------|----------|
| `ci.yml` | Main pipeline (lint, test, build) | All PRs | ~14 min |
| `dev-environment-ci.yml` | Dev container validation | Dev env changes | ~10 min |
| `security.yml` | Secret scanning | All PRs | ~11s |
| `makefile-testing.yml` | Makefile validation | Makefile changes | ~3 min |
| `codespace-testing.yml` | Codespace validation | Backend changes | ~8s |
| `claude-code-review.yml` | AI code review | All PRs | ~5 min |
| `pr-devcontainer-info.yml` | Add dev env info | PR open | ~10s |
| `publish.yml` | Build & push images | Merge to main | ~15 min |

**Total per PR**: ~17 minutes (includes duplicate builds)

### Current Issues

1. ❌ **Duplicate Builds**: Backend built twice per PR (ci.yml + dev-environment-ci.yml)
2. ❌ **Disk Space Failures**: Common due to duplicate builds
3. ❌ **Slow Feedback**: Monolithic workflows hide specific failures
4. ❌ **Limited Security**: Only secret scanning (no CVE scans)
5. ❌ **No SBOM**: Missing supply chain documentation
6. ✅ **Python 3.12**: Our requirement (no need for 3.11 - we use 3.12-specific features)

## Proposed Architecture (MCP-Inspired)

### Design Principles

Inspired by [IBM MCP Context Forge's CI/CD](https://github.com/IBM/mcp-context-forge/.github/workflows):

1. **Separation of Concerns** - One workflow, one purpose
2. **Matrix Execution** - Parallel jobs for visibility
3. **Staged Pipeline** - Fast feedback first, expensive later
4. **Security-First** - Comprehensive scanning (Hadolint, Dockle, Trivy, SBOM)
5. **Fail-Fast: False** - Show all failures, not just first
6. **Build Once** - No duplicate builds, use artifacts

### Workflow Structure

```
.github/workflows/
├── 01-lint.yml                 # Multi-linter matrix (Stage 1)
├── 02-test-unit.yml            # Unit tests with coverage (Stage 2)
├── 03-build-secure.yml         # Build + security scan (Stage 2)
├── 04-integration.yml          # Integration tests (Stage 3)
├── 05-deploy.yml               # Deployment (post-merge)
└── specialized/
    ├── dev-environment-ci.yml  # Conditional: dev env changes only
    ├── codespace-testing.yml   # Lightweight validation
    └── claude-review.yml       # AI code review
```

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  PULL REQUEST or PUSH to main                                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
    ┌────────────────┴────────────────┐
    │                                 │
╔═══════════════════════╗   ╔════════════════════╗
║  STAGE 1              ║   ║  ALWAYS PARALLEL   ║
║  Fast Feedback        ║   ║                    ║
║  (2-3 minutes)        ║   ║  - Claude Review   ║
╚═══════════════════════╝   ║  - Codespace Info  ║
    │                       ╚════════════════════╝
    ├─ Lint Matrix (parallel)
    │  ├─ YAML lint
    │  ├─ JSON lint
    │  ├─ TOML lint
    │  ├─ Ruff (check)
    │  ├─ Ruff (format)
    │  ├─ MyPy
    │  ├─ Pylint
    │  ├─ Pydocstyle
    │  ├─ ESLint (frontend)
    │  └─ Prettier (frontend)
    │
    ├─ Security Scan (parallel)
    │  ├─ Gitleaks
    │  └─ Trufflehog
    │
    └─ Test Isolation
       └─ Atomic tests
    │
    └────── All Stage 1 passed ✅
                     │
    ┌────────────────┴────────────────┐
    │                                 │
╔═══════════════════════╗   ╔════════════════════╗
║  STAGE 2              ║   ║  STAGE 2           ║
║  Unit Tests           ║   ║  Build & Scan      ║
║  (4-5 minutes)        ║   ║  (6-8 minutes)     ║
╚═══════════════════════╝   ╚════════════════════╝
    │                                 │
    ├─ Python 3.12                    ├─ Image Matrix
    │  └─ pytest -m unit              │  ├─ Backend
    │     --cov 80%                   │  │  ├─ Hadolint (Dockerfile)
    │     (single version -           │  │  ├─ Build (BuildKit cache)
    │      we use 3.12 features)      │  │  ├─ Dockle (image lint)
    │                                 │  │  ├─ Trivy (CVE scan)
    │                                 │  │  ├─ Syft (SBOM)
    │                                 │  │  └─ Upload SARIF
    │                                 │  │
    │                                 │  └─ Frontend
    │                                 │     ├─ Hadolint
    │                                 │     ├─ Build
    │                                 │     ├─ Dockle
    │                                 │     ├─ Trivy
    │                                 │     └─ Syft
    │                                 │
    └────── All Stage 2 passed ✅ ────┘
                     │
    ┌────────────────┴────────────────┬──────────────┐
    │                                 │              │
╔═══════════════════════╗   ╔════════════════╗  ╔═══════════════╗
║  STAGE 3              ║   ║  STAGE 3       ║  ║  STAGE 3      ║
║  Smoke Tests          ║   ║  Integration   ║  ║  E2E Tests    ║
║  (2-3 minutes)        ║   ║  (5-7 minutes) ║  ║  (Optional)   ║
╚═══════════════════════╝   ╚════════════════╝  ╚═══════════════╝
    │                                 │              │
    ├─ Start minimal stack            ├─ Suite Matrix     (Future)
    ├─ Health checks                  │  ├─ API tests      ├─ Playwright
    ├─ Critical APIs                  │  ├─ VectorDB       └─ User flows
    └─ Quick validation               │  ├─ Storage
                                      │  └─ Full stack
                                      │
    └────────── All Stage 3 passed ✅ ─┘
                     │
         ┌───────────┴───────────┐
         │                       │
    [PR Workflow]          [Main Branch]
         │                       │
    [Summary                [Push to GHCR]
     Report]                [Cosign Sign]
                           [Attest SBOM]
                           [Deploy Staging]
```

## Stage Definitions

### Stage 1: Fast Feedback (~2-3 minutes)

**Goal**: Catch obvious issues quickly before expensive operations

**Jobs**:
- **Lint Matrix** - Each linter is a separate job (parallel)
- **Security Scan** - Secret detection (gitleaks, trufflehog)
- **Test Isolation** - Atomic tests without dependencies

**Fail Criteria**:
- Any linter fails
- Secrets detected
- Atomic tests fail

**On Failure**: Stop pipeline (don't waste CI on broken code)

### Stage 2: Build & Test (~6-8 minutes, parallel)

**Goal**: Verify code quality and build artifacts

**Jobs**:
- **Unit Tests** - Python 3.12, 80% coverage requirement
- **Build Images** - Backend + frontend matrix with security scans

**Fail Criteria**:
- Coverage < 80%
- Unit tests fail
- Build fails
- CRITICAL CVEs found
- Security lint fails (Hadolint/Dockle)

**On Failure**: Stop pipeline, provide detailed logs

### Stage 3: Integration & Validation (~5-7 minutes, parallel)

**Goal**: Validate end-to-end functionality

**Jobs**:
- **Smoke Tests** - Quick validation of critical paths
- **Integration Tests** - Full stack testing by suite
- **E2E Tests** - Browser-based user flows (future)

**Fail Criteria**:
- Service startup fails
- API tests fail
- Integration tests fail

**On Failure**: Show service logs, provide debugging info

## Workflow Details

### 01-lint.yml

**Purpose**: Static analysis and code quality

**Matrix Strategy** (Inspired by MCP Context Forge):
```yaml
strategy:
  fail-fast: false
  matrix:
    linter:
      - {id: yamllint, name: "YAML Lint"}
      - {id: jsonlint, name: "JSON Lint"}
      - {id: toml-check, name: "TOML Lint"}
      - {id: ruff-check, name: "Ruff Check"}
      - {id: ruff-format, name: "Ruff Format"}
      - {id: mypy, name: "MyPy Type Check"}
      - {id: pylint, name: "Pylint Quality"}
      - {id: pydocstyle, name: "Docstring Style"}
      - {id: eslint, name: "ESLint (Frontend)"}
      - {id: prettier, name: "Prettier Format"}
```

**Benefits**:
- ✅ Each linter runs in parallel (~2-3 min total)
- ✅ See exactly which linter failed
- ✅ Can retry individual linters
- ✅ Better visibility in GitHub UI

**Permissions**: `contents: read`

### 02-test-unit.yml

**Purpose**: Unit testing with coverage across Python versions

**Python Version**:
- Python 3.12 only (our requirement: `requires-python = ">=3.12,<3.13"`)
- Unlike MCP Context Forge (library), we're an application using 3.12-specific features

**Steps**:
1. Setup Python (with pip cache)
2. Install Poetry + dependencies
3. Run pytest with coverage (80% minimum)
4. Upload coverage artifacts (XML + HTML)
5. Post coverage summary to job

**Coverage Reporting**:
- Branch + line coverage
- Per-file coverage table in job summary
- Artifacts retained for 7 days
- Fail if < 80%

**Permissions**: `contents: read, checks: write`

### 03-build-secure.yml

**Purpose**: Build Docker images with comprehensive security scanning

**Matrix Strategy**:
```yaml
strategy:
  fail-fast: false
  matrix:
    image:
      - {name: backend, context: ./backend, dockerfile: ./backend/Dockerfile.backend}
      - {name: frontend, context: ./frontend, dockerfile: ./frontend/Dockerfile.frontend}
```

**Security Pipeline** (Inspired by MCP Context Forge):
1. **Pre-Build**: Hadolint (Dockerfile linting) → SARIF upload
2. **Build**: Docker Buildx with layer caching
3. **Post-Build**:
   - Dockle (image linting) → SARIF
   - Trivy (CVE scanning) → SARIF
   - Syft (SBOM generation) → Artifact
4. **On Main Only**:
   - Push to GHCR
   - Cosign signing (keyless OIDC)
   - SBOM attestation

**BuildKit Caching**:
```yaml
cache-from: type=local,src=/tmp/.buildx-cache
cache-to: type=local,dest=/tmp/.buildx-cache-new,mode=max
```

**Security Scans**:
- **Hadolint**: Dockerfile best practices
- **Dockle**: Container image security
- **Trivy**: CVE detection (fail on CRITICAL/HIGH)
- **Syft**: SPDX SBOM generation

**Permissions**:
```yaml
contents: read
packages: write          # Push to GHCR
security-events: write   # Upload SARIF
id-token: write          # Cosign signing
```

### 04-integration.yml

**Purpose**: End-to-end validation of built images

**Jobs**:

1. **smoke-tests** (2-3 min)
   - Start minimal stack (backend + postgres)
   - Test health endpoints
   - Test critical API paths
   - Quick pass/fail

2. **integration-full** (5-7 min)
   - Start full stack (postgres, milvus, minio, backend, frontend)
   - Run integration test suite
   - Validate service communication
   - Database migrations
   - Vector DB operations

**Service Matrix** (Future):
```yaml
matrix:
  suite:
    - {name: "API Integration", markers: "integration and api"}
    - {name: "VectorDB Integration", markers: "integration and vectordb"}
    - {name: "Storage Integration", markers: "integration and storage"}
```

**Permissions**: `contents: read`

### 05-deploy.yml

**Purpose**: Automated deployment on merge to main

**Triggers**:
```yaml
on:
  push:
    branches: [main]
  workflow_dispatch:  # Manual trigger
```

**Steps**:
1. Download built images from build-secure.yml
2. Verify signatures (Cosign)
3. Deploy to staging
4. Run smoke tests on staging
5. (Manual approval for production)
6. Deploy to production

**Permissions**: `contents: read, packages: read, deployments: write`

## Specialized Workflows

### dev-environment-ci.yml

**Purpose**: Validate dev container and development environment setup

**Triggers** (FIXED in PR #323):
```yaml
paths:
  - '.devcontainer/**'
  - 'docker-compose.dev.yml'
  - 'docker-compose.hotreload.yml'
  # Removed: backend/**, tests/** (prevented duplicate builds)
```

**When to Run**:
- Changes to .devcontainer configuration
- Changes to dev docker-compose files
- Manual trigger (workflow_dispatch)

**What It Tests**:
- Dev container JSON validation
- Docker compose configuration
- Development image builds
- Tool availability (poetry, make, python)

### makefile-testing.yml

**Purpose**: Validate Makefile targets work correctly

**Triggers**:
```yaml
paths:
  - 'Makefile'
  - '.github/workflows/makefile-testing.yml'
```

**Tests**:
- `make help`
- `make info`
- `make check-docker`
- Other essential targets

### security.yml

**Purpose**: Secret scanning with gitleaks and trufflehog

**Triggers**: All pull requests

**Scans**:
- Gitleaks (GitHub native)
- TruffleHog (broader coverage)
- Both upload findings to GitHub Security

### claude-code-review.yml

**Purpose**: AI-powered code review using Claude

**Triggers**: PR open/synchronize

**Provides**:
- Code quality feedback
- Best practice suggestions
- Potential bug detection

## Performance Optimization

### BuildKit Layer Caching

```yaml
- uses: docker/setup-buildx-action@v3

- uses: actions/cache@v4
  with:
    path: /tmp/.buildx-cache
    key: buildx-${{ matrix.image.name }}-${{ github.sha }}
    restore-keys: buildx-${{ matrix.image.name }}-
```

**Benefits**:
- 60-80% faster rebuilds
- Reduced disk usage
- Better cache hit rate

### Disk Space Management

```bash
# Free ~14GB before Docker builds
sudo rm -rf /usr/share/dotnet      # ~6GB
sudo rm -rf /opt/ghc               # ~3GB
sudo rm -rf /usr/local/share/boost # ~2GB
sudo rm -rf "$AGENT_TOOLSDIRECTORY" # ~3GB
docker system prune -af --volumes   # Variable
```

**Applied in**:
- ci.yml (build job)
- dev-environment-ci.yml (build job)

### Dependency Caching

```yaml
- uses: actions/setup-python@v4
  with:
    python-version: '3.12'
    cache: 'pip'  # Cache pip dependencies

- uses: actions/cache@v4
  with:
    path: ~/.cache/pypoetry
    key: poetry-${{ hashFiles('**/poetry.lock') }}
```

## Security & Compliance

### SARIF Upload Integration

All security tools upload results to GitHub Security tab:

```yaml
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
    category: tool-name
```

**Benefits**:
- Centralized security findings
- Trend analysis over time
- Integration with GitHub Advanced Security

### SBOM Generation

**Tool**: Syft (Anchore)
**Format**: SPDX JSON
**Frequency**: Every build
**Retention**: 30 days (artifacts), permanent (releases)

```yaml
- uses: anchore/sbom-action@v0
  with:
    image: backend:latest
    format: spdx-json
    output-file: sbom.spdx.json
```

### Image Signing (Production)

**Tool**: Cosign (keyless OIDC)
**When**: Only on merge to main
**What**: Sign images + attest SBOM

```yaml
- uses: sigstore/cosign-installer@v3

- name: Sign image
  run: cosign sign --yes $IMAGE_TAG

- name: Attest SBOM
  run: cosign attest --yes --predicate sbom.spdx.json $IMAGE_TAG
```

## Testing Strategy

### Test Pyramid

```
       /\
      /E2\       E2E Tests (Browser, Playwright)
     /____\      - User workflows
    /      \     - Full stack
   / Integ  \    Integration Tests (Docker Compose)
  /__________\   - API integration
 /            \  - Database integration
/    Unit      \ Unit Tests (Fast, Isolated)
/______________\ - Business logic
                 - Pure functions
```

### Test Markers

```python
@pytest.mark.atomic       # No external dependencies
@pytest.mark.unit         # Unit tests
@pytest.mark.integration  # Requires services
@pytest.mark.api          # API endpoint tests
@pytest.mark.e2e          # End-to-end tests
```

### Coverage Requirements

| Test Type | Coverage Target | Current |
|-----------|----------------|---------|
| Unit Tests | 80% | ~60% |
| Integration Tests | 60% | ~40% |
| Overall | 75% | ~55% |

## Artifact Management

### Build Artifacts

| Artifact | Retention | Purpose |
|----------|-----------|---------|
| Docker images | 1 day | Reuse across workflows |
| Coverage reports (XML) | 7 days | Trend analysis |
| Coverage reports (HTML) | 7 days | Detailed inspection |
| SBOM (SPDX) | 30 days | Supply chain audit |
| Security scans (SARIF) | Permanent | Compliance |
| Test results | 7 days | Debugging |

### Cache Strategy

```yaml
# Dependency caches
- Python pip: actions/setup-python (cache: 'pip')
- Poetry venv: actions/cache (backend/.venv)
- npm packages: actions/setup-node (cache: 'npm')

# Build caches
- Docker layers: BuildKit local cache
- Buildx: actions/cache (/tmp/.buildx-cache)
```

## Deployment Pipeline

### Staging Deployment

**Trigger**: Merge to main
**Target**: IBM Code Engine / Kubernetes Staging
**Steps**:
1. Pull signed images from GHCR
2. Verify signatures (Cosign)
3. Deploy to staging namespace
4. Run smoke tests on staging
5. Notify team (Slack/GitHub)

### Production Deployment

**Trigger**: Manual approval after staging validation
**Target**: Kubernetes Production
**Steps**:
1. Manual approval gate
2. Pull signed images
3. Verify signatures
4. Blue/green deployment
5. Health checks
6. Smoke tests
7. Gradual traffic shift
8. Monitoring alerts

## Monitoring & Observability

### CI/CD Metrics

Track in GitHub Actions insights:
- Average PR CI duration
- Build success rate
- Test flakiness
- Cache hit rate
- Security findings trend

### Alerts

Set up alerts for:
- ❌ Critical CVEs in images
- ❌ Coverage drops below 75%
- ❌ Build time > 15 minutes
- ❌ Repeated workflow failures

## Best Practices

### 1. Minimal Permissions

Always use least-privilege:
```yaml
permissions:
  contents: read  # Default
  # Add only what's needed:
  packages: write        # If pushing to GHCR
  security-events: write # If uploading SARIF
  id-token: write        # If using Cosign
```

### 2. Fail-Fast: False

Show all failures:
```yaml
strategy:
  fail-fast: false  # Don't stop on first failure
```

**Why**: See all linting issues at once, not one-by-one

### 3. Continue-on-Error for Non-Blocking

```yaml
- name: Run optional check
  continue-on-error: true  # Don't fail workflow
```

**Use for**: Performance tests, optional validations

### 4. Proper Cleanup

```yaml
- name: Cleanup
  if: always()  # Run even if job fails
  run: docker compose down -v
```

### 5. Timeout Protection

```yaml
timeout-minutes: 15  # Per job
```

**Prevents**: Hung jobs consuming CI minutes

## Troubleshooting

### Common Issues

**"No space left on device"**
- **Cause**: Large Docker builds without cleanup
- **Fix**: Disk cleanup step before builds
- **Prevention**: BuildKit caching, artifact reuse

**"Workflow runs twice"**
- **Cause**: Overlapping path triggers
- **Fix**: Make path triggers specific and exclusive
- **Prevention**: Regular workflow audit

**"Flaky tests"**
- **Cause**: Race conditions, hardcoded sleeps
- **Fix**: Proper wait logic with timeouts
- **Prevention**: Atomic test design, retry logic

**"Build cache misses"**
- **Cause**: Cache key changes every build
- **Fix**: Use restore-keys with prefix
- **Prevention**: Stable cache key strategy

## Migration Guide

### From Current to MCP-Inspired

**Phase 1: Foundation**
1. Update dev-environment-ci.yml triggers ✅ (Done in PR #323)
2. Split monolithic lint into matrix
3. Add BuildKit caching
4. Set fail-fast: false

**Phase 2: Security**
1. Add Trivy CVE scanning
2. Add Hadolint + Dockle
3. Generate SBOM
4. Upload all SARIF

**Phase 3: Testing**
1. Increase coverage to 80%
2. Add smoke tests
3. Add integration tests
4. Add branch coverage

**Phase 4: Advanced**
1. Cosign signing
2. E2E tests
3. Performance benchmarks
4. Deployment automation

## References

- [IBM MCP Context Forge CI/CD](https://github.com/IBM/mcp-context-forge/.github/workflows)
- [GitHub Actions Best Practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [Docker Build Best Practices](https://docs.docker.com/build/building/best-practices/)
- [SARIF Documentation](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)

## Change Log

- **2025-10-06**: Initial architecture documentation
- **2025-10-06**: Added MCP Context Forge analysis
- **2025-10-06**: Proposed redesign based on best practices

---

**Next**: See Issue #324 for implementation plan
