# Testing GitHub Actions Workflows Locally

Use `act` to test GitHub Actions workflows locally before pushing to GitHub.

## Install act

### macOS

```bash
brew install act
```

### Linux

```bash
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

### Verify Installation

```bash
act --version
```

---

## Basic Usage

### Test the CI Workflow

```bash
# Test the CI workflow (runs on pull requests)
act pull_request -W .github/workflows/ci.yml

# Test with specific event
act push -W .github/workflows/ci.yml
```

### Test IBM Code Engine Workflow

**Important:** The IBM Code Engine workflow requires secrets and will fail locally without proper setup. Use for syntax validation only.

```bash
# Syntax check (will fail at deployment step - expected)
act workflow_dispatch -W .github/workflows/ibm-code-engine-staging.yml --dryrun

# List what jobs would run
act workflow_dispatch -W .github/workflows/ibm-code-engine-staging.yml --list
```

---

## Testing with Secrets

Create a `.secrets` file (⚠️ **DO NOT commit this file**):

```bash
# .secrets
GITHUB_TOKEN=your_github_pat
IBM_CLOUD_API_KEY=your_ibm_api_key
```

**Make sure `.secrets` is in `.gitignore`:**

```bash
echo ".secrets" >> .gitignore
```

**Run with secrets:**

```bash
act workflow_dispatch -W .github/workflows/ibm-code-engine-staging.yml --secret-file .secrets
```

---

## Testing Specific Jobs

### Test Only Build Job

```bash
# Test just the build-and-push job (doesn't push images in act)
act workflow_dispatch \
  -W .github/workflows/ibm-code-engine-staging.yml \
  -j build-and-push \
  --dryrun
```

### Test All Jobs

```bash
# Run all jobs (will fail at deployment without IBM Cloud access)
act workflow_dispatch -W .github/workflows/ibm-code-engine-staging.yml
```

---

## Recommended Testing Workflow

### Before Pushing Changes

**1. Syntax Check:**
```bash
# Quick validation - checks YAML syntax and workflow structure
act --list -W .github/workflows/ibm-code-engine-staging.yml
```

**2. Dry Run Build Job:**
```bash
# Test build steps without actually running
act workflow_dispatch \
  -W .github/workflows/ibm-code-engine-staging.yml \
  -j build-and-push \
  --dryrun
```

**3. Validate CI Workflow:**
```bash
# Run CI workflow (faster, no deployment)
act pull_request -W .github/workflows/ci.yml --dryrun
```

**4. If all checks pass → Push to GitHub**

---

## Common Issues

### Issue: "Docker daemon not running"

**Solution:**
```bash
# Make sure Docker Desktop is running
docker ps
```

### Issue: "Error: unable to get git ref"

**Solution:**
```bash
# Make sure you're in the git repository root
cd /path/to/rag_modulo
git status
```

### Issue: "secrets not found"

**Solution:**
```bash
# Create .secrets file with required secrets
# OR use --secret flag:
act workflow_dispatch -s GITHUB_TOKEN=ghp_xxx
```

### Issue: "Platform not supported"

**Solution:**
```bash
# Use specific platform
act -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

---

## What act Can and Cannot Test

### ✅ Can Test Locally

- YAML syntax validation
- Workflow structure
- Job dependencies
- Step ordering
- Basic shell commands
- Docker builds (if you have Docker)

### ❌ Cannot Test Locally

- **Actual deployments** (requires real IBM Cloud/GitHub access)
- **GitHub-hosted secrets** (need to provide via `.secrets` file)
- **GitHub-specific features** (OIDC, deployment environments)
- **Large builds** (act runs in containers, limited resources)
- **Cache actions** (GHA cache is GitHub-hosted)

---

## Best Practices

### For Quick Validation

```bash
# Just check if workflow is valid
act --list
```

### For Comprehensive Testing

```bash
# Test build job with actual execution (no push)
act workflow_dispatch -j build-and-push
```

### For CI Validation

```bash
# Test the full CI pipeline
act pull_request -W .github/workflows/ci.yml
```

---

## Alternative: GitHub CLI (for real testing)

If you want to test on GitHub's actual infrastructure:

```bash
# Install GitHub CLI
brew install gh

# Trigger workflow manually on GitHub
gh workflow run ibm-code-engine-staging.yml

# Watch the run
gh run watch
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `act --list` | List all workflows and jobs |
| `act --list -W workflow.yml` | List jobs in specific workflow |
| `act --dryrun` | Validate without running |
| `act workflow_dispatch` | Trigger workflow_dispatch event |
| `act pull_request` | Trigger pull_request event |
| `act push` | Trigger push event |
| `act -j job-name` | Run specific job |
| `act --secret-file .secrets` | Use secrets from file |

---

## Example: Full Pre-Push Validation

```bash
#!/bin/bash
# scripts/test-workflows.sh

echo "🧪 Testing workflows locally before push..."

echo "1️⃣ Validating workflow syntax..."
act --list -W .github/workflows/ibm-code-engine-staging.yml
if [ $? -ne 0 ]; then
  echo "❌ Workflow syntax validation failed"
  exit 1
fi

echo "2️⃣ Testing CI workflow..."
act pull_request -W .github/workflows/ci.yml --dryrun
if [ $? -ne 0 ]; then
  echo "❌ CI workflow validation failed"
  exit 1
fi

echo "3️⃣ Testing Code Engine workflow structure..."
act workflow_dispatch -W .github/workflows/ibm-code-engine-staging.yml --dryrun
if [ $? -ne 0 ]; then
  echo "❌ Code Engine workflow validation failed"
  exit 1
fi

echo "✅ All workflow validations passed!"
echo "🚀 Safe to push to GitHub"
```

Make it executable:
```bash
chmod +x scripts/test-workflows.sh
./scripts/test-workflows.sh
```

---

## Resources

- [act Documentation](https://github.com/nektos/act)
- [GitHub Actions Local Testing](https://docs.github.com/en/actions/using-workflows/about-workflows)
- [act Docker Images](https://github.com/catthehacker/docker_images)
