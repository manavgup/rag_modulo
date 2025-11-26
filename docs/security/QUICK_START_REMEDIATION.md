# Quick Start: Security Remediation Guide

**Priority:** CRITICAL
**Time Required:** 1-2 hours for Phase 1
**Last Updated:** 2025-11-25

## 🚨 Immediate Actions Required

Your repository has **80+ security vulnerabilities** including **15 CRITICAL** issues that need immediate attention.

---

## Phase 1: Critical Fixes (Do This First!)

### Prerequisites

- Access to repository with write permissions
- Poetry installed (`curl -sSL https://install.python-poetry.org | python3 -`)
- Node.js 20+ installed
- Docker installed (for Phase 2)

### Step 1: Run the Automated Fix Script (Recommended)

```bash
# Make the script executable
chmod +x scripts/security/fix-critical-vulnerabilities.sh

# Run the script
./scripts/security/fix-critical-vulnerabilities.sh
```

This script will:

- ✅ Backup current dependencies
- ✅ Update Starlette (fixes DoS vulnerability)
- ✅ Update Authlib (fixes auth bypass & DoS)
- ✅ Update glob (fixes command injection)
- ✅ Update js-yaml (fixes YAML parsing issues)
- ✅ Update webpack-dev-server (fixes info disclosure)
- ✅ Run tests to verify nothing broke

### Step 2: Manual Verification

After running the script, verify the updates:

```bash
# Check Python package versions
poetry show starlette authlib

# Expected versions:
# starlette >= 0.41.3
# authlib >= 1.3.3

# Check Node.js package versions
cd frontend
npm list glob js-yaml webpack-dev-server
```

### Step 3: Test Your Application

```bash
# Backend tests
cd backend
poetry run pytest tests/ -v

# Frontend tests
cd frontend
npm test

# Integration tests (if available)
npm run test:integration
```

### Step 4: Deploy to Staging

```bash
# Build and test locally
docker-compose up --build

# If successful, deploy to staging
# (Use your existing deployment process)
```

---

## Phase 2: Docker Base Image Updates (Next Week)

### Backend Dockerfile Updates

**Current Issue:** Using outdated base images with 45+ system library vulnerabilities

**File:** `backend/Dockerfile`

```dockerfile
# BEFORE (vulnerable)
FROM python:3.12-slim

# AFTER (secure)
FROM python:3.12-slim-bookworm

# Add this after FROM
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

### Frontend Dockerfile Updates

**File:** `frontend/Dockerfile`

```dockerfile
# BEFORE (vulnerable)
FROM node:20-alpine

# AFTER (secure)
FROM node:20-alpine3.19

# Add this after FROM
RUN apk update && apk upgrade --no-cache
```

### opencv-python Fix (FFmpeg Vulnerabilities)

**Issue:** opencv-python bundles vulnerable ffmpeg libraries

**Solution:** Switch to headless version

```bash
# Update pyproject.toml
poetry remove opencv-python
poetry add opencv-python-headless

# Or manually edit pyproject.toml:
# opencv-python-headless = "^4.8.1"
```

---

## Phase 3: Enable Continuous Security Monitoring

### 1. Enable Dependabot (5 minutes)

1. Go to your repository on GitHub
2. Click **Settings** → **Security** → **Code security and analysis**
3. Enable:
   - ✅ Dependabot alerts
   - ✅ Dependabot security updates
   - ✅ Dependabot version updates

### 2. Add Security Scanning Workflow (Already Done!)

The workflow file has been created at `.github/workflows/security-scan.yml`

To activate it:

```bash
git add .github/workflows/security-scan.yml
git commit -m "Add automated security scanning"
git push
```

This will run:

- Python security scans (pip-audit, safety, bandit)
- Node.js security scans (npm audit)
- Docker image scans (Trivy)
- Secret scanning (Gitleaks)
- Weekly automated scans

### 3. Install Pre-commit Hooks (Optional but Recommended)

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml (if not exists)
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: detect-private-key
      - id: check-added-large-files

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
EOF

# Install the hooks
pre-commit install

# Test it
pre-commit run --all-files
```

---

## Verification Checklist

After completing Phase 1, verify:

- [ ] No CRITICAL vulnerabilities in `npm audit`
- [ ] No CRITICAL vulnerabilities in `pip-audit`
- [ ] All tests passing
- [ ] Application runs locally
- [ ] Authentication works correctly
- [ ] API endpoints respond correctly

Run these commands to verify:

```bash
# Python vulnerabilities
pip install pip-audit
pip-audit

# Node.js vulnerabilities
cd frontend
npm audit --audit-level=high

# Run all tests
cd backend && poetry run pytest
cd frontend && npm test
```

---

## Troubleshooting

### Issue: Poetry update fails

```bash
# Clear cache and try again
poetry cache clear pypi --all
poetry update starlette authlib
```

### Issue: npm update fails

```bash
# Clear cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Issue: Tests fail after updates

```bash
# Restore from backup
mv pyproject.toml.backup pyproject.toml
mv poetry.lock.backup poetry.lock
poetry install

# Investigate specific test failures
poetry run pytest tests/ -v --tb=long
```

### Issue: Docker build fails

```bash
# Clear Docker cache
docker system prune -a

# Rebuild without cache
docker build --no-cache -t rag-modulo-backend:latest -f backend/Dockerfile .
```

---

## Expected Timeline

| Phase | Duration | Effort |
|-------|----------|--------|
| Phase 1: Critical Fixes | 1-2 hours | 1 developer |
| Testing & Validation | 2-3 hours | 1 QA engineer |
| Phase 2: Docker Updates | 1 day | 1 developer |
| Phase 3: Monitoring Setup | 2 hours | 1 DevOps engineer |
| **Total** | **2-3 days** | **Small team** |

---

## Success Metrics

After remediation, you should see:

- ✅ **0 CRITICAL** vulnerabilities
- ✅ **<5 HIGH** vulnerabilities (with mitigation plans)
- ✅ **Automated scanning** in CI/CD
- ✅ **Weekly Dependabot updates**
- ✅ **All tests passing**

---

## Getting Help

### Resources

- Full analysis: [`docs/security/SECURITY_ALERT_ANALYSIS.md`](./SECURITY_ALERT_ANALYSIS.md)
- GitHub Security: <https://docs.github.com/en/code-security>
- OWASP Top 10: <https://owasp.org/www-project-top-ten/>

### Support

- Security issues: Report immediately to security team
- Questions: Create an issue in the repository
- Urgent: Contact DevOps/Security team directly

---

## Next Steps After Phase 1

1. ✅ Monitor for new vulnerabilities (Dependabot will alert you)
2. ✅ Schedule Phase 2 (Docker updates) for next week
3. ✅ Review authentication implementation
4. ✅ Conduct security training for team
5. ✅ Plan penetration testing engagement

---

**Remember:** Security is an ongoing process, not a one-time fix!

Keep dependencies updated, monitor alerts, and follow security best practices.
