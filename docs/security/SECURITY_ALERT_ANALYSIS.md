# Security Alert Analysis and Remediation Plan

**Generated:** 2025-11-25
**Repository:** manavgup/rag_modulo
**Total Open Alerts:** 80+

## Executive Summary

The repository has **80+ open security alerts** across multiple severity levels:

- **Critical (Error):** 15+ alerts
- **High (Warning):** 20+ alerts
- **Medium/Low (Note):** 45+ alerts

### Key Findings

1. **Critical Python Dependencies:** Authlib, Starlette vulnerabilities (DoS, RFC violations)
2. **Critical Node.js Dependencies:** glob CLI command injection, js-yaml vulnerabilities
3. **Docker Base Image Issues:** BusyBox, system libraries (ffmpeg, curl, systemd)
4. **Frontend Security:** webpack-dev-server information exposure
5. **Backend Security:** Multiple ffmpeg CVEs in opencv-python dependencies

---

## Detailed Analysis by Severity

### 🔴 CRITICAL (Error Severity) - Immediate Action Required

#### 1. **Starlette DoS Vulnerability (CVE-2025-62727)**

- **Alert:** #235
- **Location:** `poetry.lock`
- **Impact:** Denial of Service via Range header merging
- **Status:** Open
- **Priority:** P0 - Critical
- **Action:** Update Starlette to latest patched version immediately

#### 2. **Authlib Vulnerabilities (Multiple CVEs)**

- **Alerts:** #232, #233, #234
- **CVEs:** CVE-2025-59420 (RFC violation), CVE-2025-61920 (DoS), CVE-2025-62706
- **Location:** `poetry.lock`
- **Impact:** Authentication bypass, Denial of Service
- **Status:** Open (some fixed in #229-231)
- **Priority:** P0 - Critical
- **Action:** Update Authlib to version 1.3.3 or later

#### 3. **glob CLI Command Injection (CVE-2025-64756)**

- **Alerts:** #294, #303
- **Location:** `package-lock.json`, `frontend/package-lock.json`
- **Impact:** Command injection via -c/--cmd flag
- **Status:** Open
- **Priority:** P0 - Critical
- **Action:** Update glob package immediately

#### 4. **FFmpeg High Severity Vulnerabilities**

- **Alerts:** #166, #167, #170, #171, #183, #184, #189
- **CVEs:** CVE-2025-9951, CVE-2023-49502, CVE-2025-1594, CVE-2023-6605, CVE-2023-50008, CVE-2023-50010, CVE-2024-31582
- **Location:** `opencv_python.libs/libavcodec`
- **Impact:** Buffer overflow, arbitrary code execution
- **Status:** Open
- **Priority:** P1 - High
- **Action:** Update opencv-python or use alternative without bundled ffmpeg

---

### 🟡 HIGH (Warning Severity) - Action Required

#### 5. **js-yaml Vulnerabilities (CVE-2025-64718)**

- **Alerts:** #238, #239, #240, #241
- **Location:** `package-lock.json`, `frontend/package-lock.json`
- **Impact:** YAML parsing vulnerabilities
- **Status:** Open
- **Priority:** P1 - High
- **Action:** Update js-yaml to latest version

#### 6. **webpack-dev-server Information Exposure**

- **Alerts:** #227, #228
- **CVEs:** CVE-2025-30359, CVE-2025-30360
- **Location:** `frontend/package-lock.json`
- **Impact:** Information disclosure
- **Status:** Open
- **Priority:** P1 - High
- **Action:** Update webpack-dev-server

#### 7. **BusyBox netstat Vulnerability (CVE-2024-58251)**

- **Alerts:** #304, #306, #308
- **Location:** `library/rag-modulo-frontend`
- **Impact:** Local users can launch network attacks
- **Status:** Open
- **Priority:** P2 - Medium
- **Action:** Update base Docker image to use newer BusyBox or Alpine

#### 8. **curl Vulnerability (CVE-2025-10966)**

- **Alert:** #237
- **Location:** `rag-modulo-frontend//lib/apk/db/installed`
- **Impact:** Medium severity curl vulnerability
- **Status:** Open
- **Priority:** P2 - Medium
- **Action:** Update Alpine base image

#### 9. **pip Vulnerability (GHSA-4xh5-x5gv-qwph)**

- **Alert:** #199
- **Location:** Backend Python environment
- **Impact:** Medium severity pip vulnerability
- **Status:** Open
- **Priority:** P2 - Medium
- **Action:** Update pip to latest version

---

### 🔵 MEDIUM/LOW (Note Severity) - Scheduled Remediation

#### 10. **System Library Vulnerabilities**

Multiple low-severity CVEs in system packages:

- **systemd/libudev** (CVE-2013-4392, CVE-2023-31437, CVE-2023-31438, CVE-2023-31439)
- **util-linux** (CVE-2022-0563)
- **coreutils** (CVE-2017-18018, CVE-2025-5278)
- **glibc** (CVE-2019-1010022, CVE-2019-1010023, CVE-2019-1010024, CVE-2019-1010025, CVE-2010-4756, CVE-2018-20796, CVE-2019-9192)
- **ncurses** (CVE-2025-6141)
- **shadow** (CVE-2007-5686, CVE-2024-56433)
- **sqlite** (CVE-2021-45346, CVE-2025-7709)
- **tar** (CVE-2005-2541)
- **perl** (CVE-2011-4116)
- **apt** (CVE-2011-3374)

**Priority:** P3 - Low
**Action:** Update base Docker images to latest stable versions

#### 11. **BusyBox tar Vulnerability (CVE-2025-46394)**

- **Alerts:** #305, #307, #309
- **Location:** `library/rag-modulo-frontend`
- **Impact:** TAR archive filename hiding
- **Status:** Open
- **Priority:** P3 - Low
- **Action:** Update base Docker image

#### 12. **Python Vulnerability (CVE-2025-6075)**

- **Alert:** #236
- **Location:** `libpython3.12.so.1.0`
- **Impact:** Low severity Python vulnerability
- **Status:** Open
- **Priority:** P3 - Low
- **Action:** Update Python base image

---

## Remediation Plan

### Phase 1: Critical Fixes (Week 1)

#### Day 1-2: Python Backend Dependencies

```bash
# Update critical Python packages
poetry update starlette authlib
poetry lock
poetry install

# Verify versions
poetry show starlette authlib
```

**Expected Versions:**

- `starlette >= 0.41.3`
- `authlib >= 1.3.3`

#### Day 3-4: Node.js Frontend Dependencies

```bash
cd frontend
npm audit fix --force
npm update glob js-yaml webpack-dev-server
npm audit

# If issues persist
npm install glob@latest js-yaml@latest webpack-dev-server@latest
```

#### Day 5: Testing

- Run full test suite
- Verify authentication flows
- Test API endpoints
- Check frontend functionality

### Phase 2: High Priority Fixes (Week 2)

#### Docker Base Image Updates

**Frontend Dockerfile:**

```dockerfile
# Update from Alpine 3.x to latest
FROM node:20-alpine3.19 AS builder
# Ensure latest packages
RUN apk update && apk upgrade --no-cache
```

**Backend Dockerfile:**

```dockerfile
# Update Python base image
FROM python:3.12-slim-bookworm
# Update system packages
RUN apt-get update && apt-get upgrade -y && apt-get clean
```

#### opencv-python Alternative

```bash
# Option 1: Use opencv-python-headless (no GUI, smaller, fewer deps)
poetry remove opencv-python
poetry add opencv-python-headless

# Option 2: Build opencv without ffmpeg
# Add to pyproject.toml
[tool.poetry.dependencies]
opencv-python-headless = "^4.8.1"
```

### Phase 3: System Library Updates (Week 3)

#### Update All Base Images

1. **Frontend:** Update to `alpine:3.19` or `alpine:edge`
2. **Backend:** Update to `python:3.12-slim-bookworm` (latest Debian)
3. **Rebuild all containers**
4. **Run security scans**

```bash
# Rebuild with updated bases
docker build -t rag-modulo-frontend:latest -f frontend/Dockerfile .
docker build -t rag-modulo-backend:latest -f backend/Dockerfile .

# Scan for vulnerabilities
docker scan rag-modulo-frontend:latest
docker scan rag-modulo-backend:latest
```

---

## Dependency Update Commands

### Python (Backend)

```bash
# Update all dependencies
poetry update

# Update specific critical packages
poetry update starlette authlib

# Check for vulnerabilities
poetry export -f requirements.txt | safety check --stdin

# Alternative: Use pip-audit
pip install pip-audit
pip-audit
```

### Node.js (Frontend)

```bash
cd frontend

# Audit and fix
npm audit
npm audit fix

# Update specific packages
npm update glob js-yaml webpack-dev-server

# Check for outdated packages
npm outdated

# Update all to latest (use with caution)
npm update
```

---

## Continuous Security Monitoring

### 1. Enable Dependabot

Currently disabled. Enable in repository settings:

- Go to Settings → Security → Code security and analysis
- Enable "Dependabot alerts"
- Enable "Dependabot security updates"

### 2. Add Security Scanning to CI/CD

**GitHub Actions Workflow (`.github/workflows/security-scan.yml`):**

```yaml
name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday

jobs:
  python-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install poetry pip-audit safety
          poetry install
      - name: Run pip-audit
        run: pip-audit
      - name: Run safety check
        run: poetry export -f requirements.txt | safety check --stdin

  node-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci
      - name: Run npm audit
        working-directory: ./frontend
        run: npm audit --audit-level=moderate

  docker-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

### 3. Pre-commit Hooks

**`.pre-commit-config.yaml`:**

```yaml
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
```

---

## Testing Strategy

### 1. Security Testing Checklist

- [ ] All critical dependencies updated
- [ ] No high/critical vulnerabilities in `npm audit`
- [ ] No high/critical vulnerabilities in `pip-audit`
- [ ] Docker images scanned with Trivy
- [ ] Authentication flows tested
- [ ] API endpoints tested
- [ ] Frontend functionality verified
- [ ] Integration tests passing
- [ ] E2E tests passing

### 2. Regression Testing

```bash
# Backend tests
cd backend
poetry run pytest tests/ -v

# Frontend tests
cd frontend
npm test
npm run test:e2e

# Integration tests
docker-compose up -d
npm run test:integration
```

---

## Risk Assessment

### Current Risk Level: **HIGH** 🔴

**Breakdown:**

- **Critical Vulnerabilities:** 15+ (DoS, Command Injection, Auth Bypass)
- **High Vulnerabilities:** 20+ (Information Disclosure, Buffer Overflow)
- **Medium/Low Vulnerabilities:** 45+ (System Libraries)

### Post-Remediation Target: **LOW** 🟢

**Expected Outcome:**

- **Critical:** 0
- **High:** 0-2 (acceptable if mitigated)
- **Medium/Low:** <10 (system libraries only)

---

## Timeline and Resources

### Estimated Effort

- **Phase 1 (Critical):** 3-5 days (1 developer)
- **Phase 2 (High):** 5-7 days (1 developer)
- **Phase 3 (System):** 2-3 days (1 developer)
- **Testing:** 2-3 days (1 QA engineer)

**Total:** 2-3 weeks

### Required Resources

- 1 Senior Backend Developer
- 1 Senior Frontend Developer
- 1 QA Engineer
- 1 DevOps Engineer (for Docker/CI/CD)

---

## Success Metrics

1. **Zero critical vulnerabilities** in production
2. **<5 high severity vulnerabilities** (with documented mitigation)
3. **Automated security scanning** in CI/CD
4. **Weekly dependency updates** via Dependabot
5. **Security scan passing** before each deployment

---

## Recommendations

### Immediate Actions (This Week)

1. ✅ Enable Dependabot alerts and security updates
2. ✅ Update Starlette, Authlib, glob, js-yaml
3. ✅ Run full test suite after updates
4. ✅ Deploy to staging for validation

### Short-term (Next 2 Weeks)

1. Update Docker base images
2. Replace opencv-python with headless version
3. Implement security scanning in CI/CD
4. Add pre-commit hooks for secret detection

### Long-term (Next Month)

1. Establish security review process
2. Regular dependency update schedule
3. Security training for development team
4. Penetration testing engagement

---

## Additional Security Considerations

### 1. Secrets Management

- Review `.secrets.example` and `.secrets.baseline`
- Ensure no secrets in git history
- Use environment variables for all sensitive data
- Consider using HashiCorp Vault or AWS Secrets Manager

### 2. Authentication & Authorization

- Review Authlib implementation after update
- Implement rate limiting on auth endpoints
- Add MFA support
- Regular security audits of auth flows

### 3. API Security

- Implement request validation
- Add rate limiting
- Enable CORS properly
- Use API keys/tokens with expiration

### 4. Data Security

- Encrypt sensitive data at rest
- Use TLS for all communications
- Implement proper access controls
- Regular backup and recovery testing

---

## Contact and Escalation

**Security Issues:**

- Report to: <security@example.com>
- Severity P0/P1: Immediate escalation to CTO
- Severity P2/P3: Weekly security review meeting

**Resources:**

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)

---

## Appendix: Full Alert List

### Critical Alerts (15)

1. #235 - Starlette DoS (CVE-2025-62727)
2. #232 - Authlib RFC violation (CVE-2025-59420)
3. #233 - Authlib DoS (CVE-2025-61920)
4. #234 - Authlib vulnerability (CVE-2025-62706)
5. #294, #303 - glob command injection (CVE-2025-64756)
6. #166 - ffmpeg (CVE-2025-9951)
7. #167 - ffmpeg (CVE-2023-49502)
8. #170 - ffmpeg (CVE-2025-1594)
9. #171 - ffmpeg (CVE-2023-6605)
10. #183 - ffmpeg (CVE-2023-50008)
11. #184 - ffmpeg (CVE-2023-50010)
12. #189 - ffmpeg (CVE-2024-31582)

### High Alerts (20+)

- js-yaml vulnerabilities (#238-241)
- webpack-dev-server (#227-228)
- BusyBox netstat (#304, #306, #308)
- curl (#237)
- pip (#199)
- Multiple ffmpeg medium severity (#168, #169, #174, #178, #179, #192, #193)

### Medium/Low Alerts (45+)

- System library vulnerabilities (systemd, glibc, util-linux, etc.)
- BusyBox tar (#305, #307, #309)
- Python (#236)
- Various low-severity CVEs in base images

---

**Document Version:** 1.0
**Last Updated:** 2025-11-25
**Next Review:** 2025-12-02
