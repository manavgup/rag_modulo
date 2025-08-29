# 🚀 Local CI Development Guide

This guide explains how to run and validate CI workflows locally before pushing to GitHub.

## 🎯 Quick Start

```bash
# Run the same checks as CI locally
make ci-local

# Set up pre-commit hooks (run once)
make setup-pre-commit

# Validate workflows can run with act
make validate-ci
```

## 🛠️ Tools Setup

### 1. Install Act (GitHub Actions locally)
```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Windows
choco install act-cli
```

### 2. Install Pre-commit (optional but recommended)
```bash
pip install pre-commit
make setup-pre-commit
```

## 📋 Available Commands

### Local CI Commands
| Command | Description | Time |
|---------|-------------|------|
| `make ci-local` | Run full local CI (lint + unit tests) | ~2-3 min |
| `make lint` | Run linting checks | ~30s |
| `make unit-tests-local` | Run unit tests | ~1-2 min |
| `make validate-ci` | Validate workflows with act | ~1 min |

### GitHub Actions Simulation
| Command | Description |
|---------|-------------|
| `act -j lint-and-unit` | Run lint/unit job locally |
| `act -j build` | Test image building |
| `act pull_request` | Simulate full PR workflow |
| `act --dryrun` | Show what would run without executing |

## 🔄 Workflow

### Before Committing
```bash
# 1. Run local checks
make ci-local

# 2. If you changed workflows, validate them
make validate-ci

# 3. Commit (pre-commit hooks will run automatically)
git commit -m "Your changes"
```

### Debugging CI Issues
```bash
# Test specific job that's failing
act -j lint-and-unit

# Run with verbose output
act -j build --verbose

# Use different runner image
act -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

## 🎯 Benefits

- **⚡ Fast Feedback**: Catch issues in ~2 minutes vs ~10 minutes on GitHub
- **💰 Cost Savings**: Reduce GitHub Actions usage
- **🔧 Better Debugging**: Full control over environment
- **✅ Confidence**: Know your changes work before pushing

## 🔍 What Gets Validated

### Pre-commit Hooks Check:
- ✅ YAML syntax in workflows
- ✅ Poetry configuration validity  
- ✅ Trailing whitespace, file endings
- ✅ JSON/TOML syntax

### Local CI (`make ci-local`) Runs:
- ✅ Ruff linting
- ✅ Unit tests (marked with `@pytest.mark.unit`)
- ✅ Fast feedback without infrastructure

### Act Validation Checks:
- ✅ Workflow syntax and structure
- ✅ Job dependencies and outputs
- ✅ Environment variables and secrets
- ✅ Docker image availability

## 🚨 Common Issues & Solutions

### Poetry Lock Issues
```bash
# If poetry.lock is out of sync
cd backend
poetry lock
```

### Docker Not Running
```bash
# Start Docker before using act
docker info  # Should show Docker status
```

### Act Permission Issues
```bash
# Use act with proper permissions
act --container-daemon-socket /var/run/docker.sock
```

## 📚 Further Reading

- [Act Documentation](https://github.com/nektos/act)
- [Pre-commit Documentation](https://pre-commit.com/)
- [GitHub Actions Best Practices](https://docs.github.com/en/actions/learn-github-actions/best-practices)