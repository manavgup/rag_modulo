# Secret Management Guide

**Audience**: Developers
**Purpose**: How to safely handle secrets, API keys, and credentials in RAG Modulo

---

## Quick Start (5 Minutes)

### ✅ Golden Rules
1. **NEVER** commit secrets to git
2. **ALWAYS** use environment variables for secrets
3. **CHECK** `.secrets.baseline` before committing
4. **RUN** `make pre-commit-run` before pushing

### 🚨 If You See a Secret Detection Error

**Pre-commit blocked your commit?**
```bash
# 1. Remove the secret from your code
# 2. Add to .env (never commit .env)
# 3. Reference in env.example with placeholder

# If false positive:
detect-secrets audit .secrets.baseline  # Mark as false positive
git add .secrets.baseline
```

**CI/CD failed with secret detection?**
1. **ROTATE** the exposed secret immediately (top priority!)
2. Remove from git history: See [Git History Cleanup](#git-history-cleanup)
3. Fix the code to use environment variables
4. Push the fix

---

## Secret Scanning System Architecture

RAG Modulo uses **three layers** of secret detection for defense-in-depth:

```
┌─────────────────────────────────────────────────────────────┐
│                    Layer 1: Pre-commit Hooks                │
│  Tool: detect-secrets (with .secrets.baseline)              │
│  Speed: < 1 second                                          │
│  Scope: Staged files only                                   │
│  Purpose: Fast local feedback before commit                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Layer 2: Local Testing                   │
│  Tool: Gitleaks (via make pre-commit-run)                   │
│  Speed: 1-2 seconds                                         │
│  Scope: Staged files only                                   │
│  Purpose: Pattern-based detection before push               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Layer 3: CI/CD Pipeline                  │
│  Tools: Gitleaks + TruffleHog                               │
│  Speed: 30-45 seconds                                       │
│  Scope: Full git history                                    │
│  Purpose: Comprehensive scan, BLOCKS merges                 │
└─────────────────────────────────────────────────────────────┘
```

### Why Three Tools?

| Tool | Strength | Detection Method |
|------|----------|------------------|
| **detect-secrets** | Low false positives, fast | Heuristics + baseline |
| **Gitleaks** | Custom patterns, configurable | Regex + keywords |
| **TruffleHog** | High accuracy | Entropy + verification |

**Combined**: Maximum coverage with minimal false positives

---

## Supported Secret Types

RAG Modulo detects 20+ secret types:

### Cloud Provider Secrets
- **AWS**: Access keys, secret keys (AKIA*, ASIA*)
- **Azure**: Storage keys, subscription keys, connection strings
- **GCP**: Service account keys (JSON), API keys

### LLM Provider Keys
- **OpenAI**: API keys (sk-*), Project keys (sk-proj-*)
- **Anthropic**: API keys (sk-ant-*)
- **WatsonX**: API keys, instance IDs
- **Google Gemini**: API keys (AIza*)

### Infrastructure Secrets
- **PostgreSQL**: Database passwords
- **MinIO**: Root username/password
- **MLFlow**: Tracking credentials
- **JWT**: Secret keys

### Version Control
- **GitHub**: Personal access tokens, app tokens, fine-grained tokens
- **GitLab**: Access tokens

### Generic Detection
- **High-entropy strings**: Base64-encoded secrets (4.5+ entropy)
- **Private keys**: SSH, PGP, RSA keys (-----BEGIN PRIVATE KEY-----)

**Full configuration**: `.gitleaks.toml`

---

## Local Development Workflow

### 1. Environment Setup

```bash
# Copy example env file
cp env.example .env

# Add your secrets (NEVER commit .env)
vim .env
```

**`.env` structure**:
```bash
# LLM Provider (choose one)
RAG_LLM=watsonx
WATSONX_APIKEY=your_actual_api_key_here
WATSONX_INSTANCE_ID=your_instance_id

# Or use OpenAI
RAG_LLM=openai
OPENAI_API_KEY=sk-your_actual_key_here

# Database
COLLECTIONDB_PASSWORD=strong_password_here

# Security
JWT_SECRET_KEY=generate_random_256_bit_key
```

**Generate secure secrets**:
```bash
# JWT secret (256-bit random)
openssl rand -base64 32

# PostgreSQL password
openssl rand -hex 16
```

### 2. Pre-commit Hook Activation

```bash
# Install pre-commit hooks (one-time setup)
pip install pre-commit
pre-commit install

# Manual run (optional)
pre-commit run --all-files
```

**What runs on commit?**
- ✅ detect-secrets (with baseline)
- ✅ Ruff formatting
- ✅ Trailing whitespace check
- ✅ YAML/JSON validation
- ✅ Private key detection

**What runs on push?**
- ✅ MyPy type checking
- ✅ Pylint code quality
- ✅ Unit tests (fast)

### 3. Local Testing Before Push

```bash
# Run all pre-commit checks manually
make pre-commit-run

# Check for secrets specifically (matches CI)
# Gitleaks scans staged files in Step 1/10 of pre-commit-run
```

**Expected output**:
```
Step 1/10: Security - Detecting secrets and sensitive data...
  🔐 Checking for hardcoded secrets with Gitleaks (staged files only - FAST)...
  ℹ️  Scanning staged files only (~1 second)...
  ✅ No secrets in staged files
```

---

## CI/CD Integration

### GitHub Actions Workflow

**File**: `.github/workflows/02-security.yml`

**Triggers**:
- Every pull request to main
- Every push to main
- Manual workflow dispatch

**What happens**:
1. **Gitleaks**: Scans entire git history for secrets
2. **TruffleHog**: Scans for verified secrets (--only-verified)
3. **Result**: **FAIL** = PR blocked, **PASS** = merge allowed

**Important**: CI now **fails on ANY secret detection** (no `continue-on-error`)

### Viewing CI Results

```bash
# Check PR status
gh pr checks <pr-number>

# View security scan logs
gh run view <run-id> --job "🔐 Gitleaks Secret Scanning"
```

---

## False Positive Handling

### Legitimate Secrets in Test Fixtures

**Problem**: Test files use fake API keys that trigger detection

**Solution**: Update `.secrets.baseline`

```bash
# Generate updated baseline
detect-secrets scan --baseline .secrets.baseline

# Audit and mark false positives
detect-secrets audit .secrets.baseline

# Navigate with arrow keys, press:
# - 'y' = Real secret (will block commit)
# - 'n' = False positive (allow)
# - 's' = Skip for now

# Commit the updated baseline
git add .secrets.baseline
git commit -m "chore: update secrets baseline"
```

### Allowlisting Paths

**Problem**: Documentation contains example secrets (README.md, env.example)

**Solution**: Add to `.gitleaks.toml` allowlist

```toml
[allowlist]
paths = [
    '''env\.example''',           # Example env files
    '''docs/.*\.md''',             # Documentation
    '''tests/fixtures/.*''',       # Test fixtures
    '''deployment/k8s/.*/secrets/.*''',  # K8s secret templates
]
```

**Pattern syntax**: [Go regex](https://github.com/google/re2/wiki/Syntax)

---

## Adding New Secret Patterns

### When to Add a Pattern

- New LLM provider integration (e.g., Cohere, HuggingFace)
- New cloud provider (e.g., DigitalOcean, Linode)
- New internal service with API keys

### How to Add a Pattern

**1. Define regex pattern in `.gitleaks.toml`**:
```toml
[[rules]]
    id = "cohere-api-key"
    description = "Cohere API Key"
    regex = '''[a-zA-Z0-9]{40}'''
    keywords = ["cohere", "COHERE_API_KEY"]
    tags = ["key", "Cohere"]
```

**2. Test the pattern**:
```bash
# Create test file with fake secret
echo "COHERE_API_KEY=abc123..." > test_secret.txt

# Run Gitleaks
gitleaks detect --source . --config .gitleaks.toml

# Expected: Should detect the pattern
```

**3. Add to env.example**:
```bash
# LLM Provider: Cohere
COHERE_API_KEY=your_cohere_api_key_here
```

**4. Update this documentation** (Supported Secret Types section)

---

## Git History Cleanup

### If a Secret Was Committed

**⚠️ WARNING**: This rewrites git history. Coordinate with your team.

### Method 1: BFG Repo-Cleaner (Recommended)

```bash
# Install BFG
brew install bfg

# Clone a fresh copy
git clone --mirror https://github.com/your-org/rag_modulo.git
cd rag_modulo.git

# Replace secret in all history
echo "sk-actual_secret_key_here" > ../secrets.txt
bfg --replace-text ../secrets.txt

# Verify and force push
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force

# Everyone must re-clone
```

### Method 2: git-filter-repo (Fine-grained)

```bash
# Install git-filter-repo
pip install git-filter-repo

# Remove file from history
git filter-repo --path .env --invert-paths

# Force push
git push origin --force --all
```

### Method 3: GitHub Secret Scanning Remediation

1. GitHub automatically detects secrets in public repos
2. Navigate to **Settings → Security → Secret scanning**
3. Review alerts and rotate secrets
4. Follow GitHub's guided remediation

---

## Emergency Response Playbook

### Secret Detected in CI

**Time-sensitive! Follow this exact order:**

**1. Rotate the secret IMMEDIATELY** (< 5 minutes)
```bash
# OpenAI
https://platform.openai.com/api-keys → Revoke → Create new

# WatsonX
IBM Cloud Console → API Keys → Delete → Create new

# GitHub
Settings → Developer settings → Tokens → Delete → Generate new
```

**2. Update local .env with new secret**

**3. Update CI/CD secrets** (if using GitHub Secrets)
```bash
# Via GitHub UI
Settings → Secrets and variables → Actions → Update secret

# Or via CLI
gh secret set OPENAI_API_KEY < secret.txt
```

**4. Clean git history** (see [Git History Cleanup](#git-history-cleanup))

**5. Verify rotation**
```bash
# Test old secret doesn't work
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer sk-old_key" \
# Expected: 401 Unauthorized

# Test new secret works
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer sk-new_key" \
# Expected: 200 OK
```

**6. Document incident** (internal security log)

---

## GitHub Secret Scanning (Optional)

### Enabling GitHub Secret Scanning

**Requirements**:
- GitHub Advanced Security (free for public repos, paid for private)
- Repository admin access

**Steps**:
1. Navigate to repository **Settings**
2. **Security → Code security and analysis**
3. Enable **"Secret scanning"**
4. Enable **"Push protection"** (recommended)

**Custom patterns**:
1. **Settings → Security → Secret scanning**
2. **Custom patterns → New pattern**
3. Example:
   ```
   Pattern: MYAPP_API_KEY=[a-zA-Z0-9]{32}
   Test string: MYAPP_API_KEY=abc123def456...
   ```

**Alerts**:
- Automatic detection of leaked secrets
- Email notifications to admins
- Integration with `.gitleaks.toml` patterns

---

## Best Practices

### ✅ Do's

- ✅ Use environment variables for all secrets
- ✅ Keep `.env` in `.gitignore` (already configured)
- ✅ Reference secrets in `env.example` with placeholders
- ✅ Run `make pre-commit-run` before pushing
- ✅ Rotate secrets every 90 days
- ✅ Use different secrets for dev/staging/prod
- ✅ Document secret sources in team wiki

### ❌ Don'ts

- ❌ Hardcode secrets in Python/JavaScript files
- ❌ Commit `.env` files to git
- ❌ Share secrets via Slack/email
- ❌ Use production secrets in development
- ❌ Bypass pre-commit hooks with `--no-verify` (unless emergency)
- ❌ Store secrets in comments or documentation
- ❌ Use weak secrets like "password123"

---

## Troubleshooting

### Pre-commit hook says "command not found: gitleaks"

**Solution**:
```bash
# macOS
brew install gitleaks

# Linux
wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz
tar -xzf gitleaks_8.18.0_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/
```

### detect-secrets keeps flagging false positives

**Solution**: Use `--baseline` to track known false positives
```bash
# Update baseline
detect-secrets scan --baseline .secrets.baseline

# Audit (mark false positives)
detect-secrets audit .secrets.baseline
```

### CI failed but I can't see the secret

**Reason**: Secrets are redacted in CI logs for security

**Solution**: Run locally with verbose output
```bash
gitleaks detect --source . --config .gitleaks.toml --verbose --redact
```

### Need to bypass pre-commit hook temporarily

**Emergency only**:
```bash
git commit --no-verify -m "emergency hotfix"

# ⚠️ WARNING: Secret scanning still runs in CI
```

---

## Related Documentation

- **Production Secrets**: [Security Hardening Guide](../deployment/security-hardening.md#secrets-management)
- **CI/CD Security**: [CI/CD Security Pipeline](ci-cd-security.md)
- **Environment Setup**: [Environment Configuration](environment-setup.md)

---

## Reference

### Tools
- [detect-secrets](https://github.com/Yelp/detect-secrets) - Baseline-based detection
- [Gitleaks](https://github.com/gitleaks/gitleaks) - Pattern-based scanning
- [TruffleHog](https://github.com/trufflesecurity/trufflehog) - Entropy + verification
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) - Git history cleanup

### Configuration Files
- `.gitleaks.toml` - Gitleaks patterns and allowlists
- `.secrets.baseline` - detect-secrets false positive tracking
- `.pre-commit-config.yaml` - Pre-commit hook configuration
- `.github/workflows/02-security.yml` - CI/CD secret scanning

### Support
- **Security issues**: Report to maintainers via private channel
- **False positives**: Create PR updating `.secrets.baseline`
- **New patterns**: Create PR updating `.gitleaks.toml`

---

**Last updated**: October 2025
**Maintainer**: Security Team
