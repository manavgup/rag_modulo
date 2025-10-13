# Deployment Testing Guide

This guide provides comprehensive instructions for testing the IBM Cloud Code Engine deployment both locally and in GitHub Actions.

## Local Testing Options

### 1. Using GitHub Actions Locally (act)

[act](https://github.com/nektos/act) allows you to run GitHub Actions locally using Docker.

#### Installation

```bash
# macOS (using Homebrew)
brew install act

# Linux/macOS (using curl)
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Windows (using Chocolatey)
choco install act-cli

# Or download from GitHub releases
# https://github.com/nektos/act/releases
```

#### Basic Usage

```bash
# List available workflows
act -l

# Run the deployment workflow
act workflow_dispatch -W .github/workflows/deploy_code_engine.yml

# Run with specific inputs
act workflow_dispatch -W .github/workflows/deploy_code_engine.yml \
  --input skip_security_scan=false

# Run with environment variables
act workflow_dispatch -W .github/workflows/deploy_code_engine.yml \
  --env IBM_CLOUD_API_KEY=your-api-key \
  --env IMAGE_URL=us.icr.io/namespace/app:test
```

#### Advanced Testing

```bash
# Test specific job
act workflow_dispatch -W .github/workflows/deploy_code_engine.yml \
  --job build-and-push-image

# Test with secrets file
act workflow_dispatch -W .github/workflows/deploy_code_engine.yml \
  --secret-file .secrets

# Dry run (show what would be executed)
act workflow_dispatch -W .github/workflows/deploy_code_engine.yml --dry-run
```

### 2. Manual Docker Testing

#### Test Docker Image Build

```bash
# Build the Code Engine image
docker build -f Dockerfile.codeengine -t rag-modulo-codeengine:test .

# Check image size
docker images rag-modulo-codeengine:test

# Test the image locally
docker run -d --name rag-modulo-test \
  -p 8000:8000 \
  -e SKIP_AUTH=true \
  -e LOG_LEVEL=DEBUG \
  rag-modulo-codeengine:test

# Wait for startup
sleep 30

# Test health endpoints
curl -f http://localhost:8000/health
curl -f http://localhost:8000/api/v1/health

# Check logs
docker logs rag-modulo-test

# Cleanup
docker stop rag-modulo-test
docker rm rag-modulo-test
```

#### Test with Environment Variables

```bash
# Create test environment file
cat > .env.test << EOF
SKIP_AUTH=true
LOG_LEVEL=DEBUG
WATSONX_APIKEY=test-key
WATSONX_INSTANCE_ID=test-instance
COLLECTIONDB_HOST=localhost
COLLECTIONDB_PORT=5432
COLLECTIONDB_NAME=test_db
COLLECTIONDB_USER=test_user
COLLECTIONDB_PASS=test_pass
VECTOR_DB=milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_USER=root
MILVUS_PASSWORD=test_pass
JWT_SECRET_KEY=test-secret-key
EOF

# Run with environment file
docker run -d --name rag-modulo-test \
  -p 8000:8000 \
  --env-file .env.test \
  rag-modulo-codeengine:test
```

### 3. Test Deployment Script

#### Prerequisites

```bash
# Install IBM Cloud CLI
curl -fsSL https://clis.cloud.ibm.com/install | sh

# Login to IBM Cloud (you'll need an API key)
ibmcloud login --apikey YOUR_API_KEY

# Set target region and resource group
ibmcloud target -r us-south -g Default
```

#### Test Script Validation

```bash
# Test script syntax
bash -n scripts/deploy_codeengine.sh

# Test with dry run (if supported)
# Note: The script doesn't have a dry-run mode, but you can test validation

# Test environment variable validation
export IBM_CLOUD_API_KEY="test-key"
export IMAGE_URL="us.icr.io/test/rag-modulo:test"
export APP_NAME="rag-modulo-test"
# ... set other required variables

# Run script (will fail at IBM Cloud login, but tests validation)
./scripts/deploy_codeengine.sh
```

### 4. Security Testing

#### Test Trivy Scanning

```bash
# Install Trivy
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Scan the built image
trivy image rag-modulo-codeengine:test

# Scan with specific severity
trivy image --severity CRITICAL,HIGH rag-modulo-codeengine:test

# Scan and save results
trivy image --format json --output trivy-results.json rag-modulo-codeengine:test

# Scan with exit code on vulnerabilities
trivy image --exit-code 1 --severity CRITICAL,HIGH rag-modulo-codeengine:test
```

#### Test Docker Security

```bash
# Check for security issues in Dockerfile
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd):/workspace \
  aquasec/trivy config /workspace/Dockerfile.codeengine

# Check for secrets in image
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --security-checks secret rag-modulo-codeengine:test
```

## GitHub Actions Testing

### 1. Test Workflow Syntax

```bash
# Validate workflow syntax
yamllint .github/workflows/deploy_code_engine.yml

# Check for common issues
actionlint .github/workflows/deploy_code_engine.yml
```

### 2. Test with Different Inputs

#### Test Security Scan Bypass

```bash
# In GitHub Actions, use these inputs:
# skip_security_scan: true
# This will skip the security scanning job
```

#### Test with Different Branches

```bash
# Test on feature branch
git checkout feature/test-deployment
# Run workflow from feature branch
```

### 3. Monitor Workflow Execution

#### Check Workflow Status

```bash
# Using GitHub CLI
gh run list --workflow=deploy_code_engine.yml

# Get specific run details
gh run view RUN_ID --log

# Download workflow logs
gh run download RUN_ID
```

#### Debug Failed Workflows

```bash
# Get detailed logs
gh run view RUN_ID --log-failed

# Rerun failed jobs
gh run rerun RUN_ID

# Rerun specific job
gh run rerun RUN_ID --job JOB_NAME
```

## Integration Testing

### 1. End-to-End Testing

#### Test Complete Deployment Flow

```bash
# 1. Build and push image
docker build -f Dockerfile.codeengine -t rag-modulo-codeengine:test .
docker tag rag-modulo-codeengine:test us.icr.io/your-namespace/rag-modulo:test
docker push us.icr.io/your-namespace/rag-modulo:test

# 2. Deploy to Code Engine
export IBM_CLOUD_API_KEY="your-api-key"
export IMAGE_URL="us.icr.io/your-namespace/rag-modulo:test"
export APP_NAME="rag-modulo-test"
# ... set other variables
./scripts/deploy_codeengine.sh

# 3. Test deployed application
APP_URL=$(ibmcloud ce app get --name rag-modulo-test --output json | jq -r '.status.latest_ready_revision_name')
curl -f "$APP_URL/health"
curl -f "$APP_URL/api/v1/health"

# 4. Cleanup
ibmcloud ce app delete --name rag-modulo-test
```

### 2. Performance Testing

#### Load Testing

```bash
# Install hey (HTTP load testing tool)
go install github.com/rakyll/hey@latest

# Test health endpoint
hey -n 1000 -c 10 http://localhost:8000/health

# Test API endpoint
hey -n 1000 -c 10 http://localhost:8000/api/v1/health
```

#### Resource Monitoring

```bash
# Monitor container resources
docker stats rag-modulo-test

# Check memory usage
docker exec rag-modulo-test ps aux

# Check disk usage
docker exec rag-modulo-test df -h
```

## Troubleshooting

### Common Issues

#### 1. Docker Build Failures

```bash
# Check build logs
docker build -f Dockerfile.codeengine -t rag-modulo-codeengine:test . 2>&1 | tee build.log

# Common fixes:
# - Check Dockerfile syntax
# - Verify all files exist
# - Check Poetry lock file
# - Ensure sufficient disk space
```

#### 2. Security Scan Failures

```bash
# Check Trivy version
trivy --version

# Update Trivy
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Check for false positives
trivy image --ignore-unfixed rag-modulo-codeengine:test
```

#### 3. Deployment Script Failures

```bash
# Enable debug mode
set -x
./scripts/deploy_codeengine.sh

# Check IBM Cloud CLI
ibmcloud version
ibmcloud target

# Test IBM Cloud connectivity
ibmcloud ce project list
```

#### 4. Application Startup Issues

```bash
# Check container logs
docker logs rag-modulo-test

# Check environment variables
docker exec rag-modulo-test env

# Test database connectivity
docker exec rag-modulo-test python -c "
from core.config import Settings
settings = Settings()
print(f'Database URL: {settings.database_url}')
"
```

### Debug Commands

#### Container Debugging

```bash
# Enter running container
docker exec -it rag-modulo-test /bin/bash

# Check Python environment
docker exec rag-modulo-test python -c "import sys; print(sys.path)"

# Check installed packages
docker exec rag-modulo-test pip list

# Check application status
docker exec rag-modulo-test ps aux
```

#### Network Debugging

```bash
# Check port binding
docker port rag-modulo-test

# Test internal connectivity
docker exec rag-modulo-test curl -f http://localhost:8000/health

# Check network configuration
docker network ls
docker network inspect bridge
```

## Best Practices

### 1. Testing Strategy

- **Always test locally first** before pushing to GitHub
- **Use different image tags** for testing vs production
- **Test with minimal secrets** to verify validation works
- **Test failure scenarios** (invalid credentials, missing secrets)
- **Verify image size** is similar to backend Dockerfile (~1.5GB)

### 2. Security Testing

- **Run security scans** on all test images
- **Check for secrets** in Docker layers
- **Verify non-root user** is being used
- **Test with different base images** if needed

### 3. Performance Testing

- **Test startup time** (should be < 30 seconds)
- **Monitor memory usage** (should be < 2GB)
- **Test under load** with realistic traffic
- **Verify auto-scaling** works correctly

### 4. Documentation

- **Document test results** for future reference
- **Keep test scripts** in version control
- **Update documentation** when tests change
- **Share test results** with team

## Continuous Testing

### 1. Pre-commit Hooks

```bash
# Add to .pre-commit-config.yaml
- repo: local
  hooks:
    - id: test-docker-build
      name: Test Docker Build
      entry: bash -c "docker build -f Dockerfile.codeengine -t rag-modulo-test ."
      language: system
      files: ^(Dockerfile\.codeengine|backend/.*)$
```

### 2. CI/CD Integration

```yaml
# Add to existing workflow
test-deployment:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Test Docker Build
      run: docker build -f Dockerfile.codeengine -t rag-modulo-test .
    - name: Test Security Scan
      run: trivy image --exit-code 1 --severity CRITICAL,HIGH rag-modulo-test
```

### 3. Automated Testing

```bash
# Create test script
#!/bin/bash
set -e

echo "Testing Docker build..."
docker build -f Dockerfile.codeengine -t rag-modulo-test .

echo "Testing security scan..."
trivy image --exit-code 1 --severity CRITICAL,HIGH rag-modulo-test

echo "Testing application startup..."
docker run -d --name rag-modulo-test -p 8000:8000 rag-modulo-test
sleep 30
curl -f http://localhost:8000/health
docker stop rag-modulo-test
docker rm rag-modulo-test

echo "All tests passed!"
```

This comprehensive testing guide ensures that your IBM Cloud Code Engine deployment is thoroughly tested before going to production.
