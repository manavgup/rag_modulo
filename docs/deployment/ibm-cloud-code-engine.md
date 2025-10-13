# IBM Cloud Code Engine Deployment

This document provides comprehensive instructions for deploying the RAG Modulo application to IBM Cloud Code Engine using the automated GitHub Actions workflow.

## Overview

The deployment process includes:
- **Security-first approach** with vulnerability scanning
- **Automated Docker image building** and pushing to IBM Container Registry
- **Secure deployment** to IBM Cloud Code Engine
- **Post-deployment verification** with smoke tests
- **Concurrency control** to prevent simultaneous deployments

## Prerequisites

### 1. IBM Cloud Account Setup

1. **Create IBM Cloud Account**: Sign up at [IBM Cloud](https://cloud.ibm.com)
2. **Create Resource Group**: Create a resource group for your deployment
3. **Create Container Registry Namespace**:
   ```bash
   ibmcloud cr namespace-add <your-namespace>
   ```
4. **Create Code Engine Project**:
   ```bash
   ibmcloud ce project create --name rag-modulo-project
   ```

### 2. Required IBM Cloud Services

- **IBM Cloud Container Registry** (ICR)
- **IBM Cloud Code Engine**
- **IBM Watsonx.ai** (for LLM functionality)
- **PostgreSQL Database** (external or IBM Cloud Database)
- **Milvus Vector Database** (external or IBM Cloud)

### 3. GitHub Repository Setup

Ensure your GitHub repository has the following secrets configured:

#### Required Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `IBM_CLOUD_API_KEY` | IBM Cloud API key for authentication | `abc123...` |
| `SKIP_AUTH` | Skip authentication for development | `true` or `false` |
| `OIDC_DISCOVERY_ENDPOINT` | OIDC discovery endpoint URL | `https://your-provider/.well-known/openid_configuration` |
| `IBM_CLIENT_ID` | IBM OIDC client ID | `your-client-id` |
| `IBM_CLIENT_SECRET` | IBM OIDC client secret | `your-client-secret` |
| `FRONTEND_URL` | Frontend application URL | `https://your-frontend.com` |
| `WATSONX_APIKEY` | Watsonx.ai API key | `your-watsonx-key` |
| `WATSONX_INSTANCE_ID` | Watsonx.ai instance ID | `your-instance-id` |
| `COLLECTIONDB_USER` | PostgreSQL username | `postgres` |
| `COLLECTIONDB_PASS` | PostgreSQL password | `your-db-password` |
| `COLLECTIONDB_HOST` | PostgreSQL host | `your-db-host.com` |
| `COLLECTIONDB_PORT` | PostgreSQL port | `5432` |
| `COLLECTIONDB_NAME` | PostgreSQL database name | `rag_modulo` |
| `VECTOR_DB` | Vector database type | `milvus` |
| `MILVUS_HOST` | Milvus host | `your-milvus-host.com` |
| `MILVUS_PORT` | Milvus port | `19530` |
| `MILVUS_USER` | Milvus username | `root` |
| `MILVUS_PASSWORD` | Milvus password | `your-milvus-password` |
| `JWT_SECRET_KEY` | JWT secret for authentication | `your-jwt-secret` |

#### Optional Variables

Configure these in GitHub repository variables (Settings > Secrets and variables > Actions > Variables):

| Variable Name | Description | Default |
|---------------|-------------|---------|
| `IBM_CE_APP_NAME` | Code Engine application name | `rag-modulo-app` |
| `IBM_CLOUD_REGION` | IBM Cloud region | `us-south` |
| `IBM_CR_NAMESPACE` | Container Registry namespace | `rag_modulo` |

## Deployment Process

### 1. Manual Deployment via GitHub Actions

1. **Navigate to Actions**: Go to your GitHub repository > Actions tab
2. **Select Workflow**: Click on "Deploy to IBM Cloud Code Engine"
3. **Run Workflow**: Click "Run workflow" button
4. **Configure Options**:
   - **Branch**: Select the branch to deploy (usually `main`)
   - **Skip Security Scan**: Leave unchecked (recommended)
5. **Start Deployment**: Click "Run workflow"

### 2. Deployment Steps

The workflow executes the following steps:

#### Step 1: Build and Push Image
- Builds Docker image using `Dockerfile.codeengine`
- Pushes image to IBM Container Registry
- Uses Docker layer caching for faster builds

#### Step 2: Security Scanning (Optional)
- Runs Trivy vulnerability scanner
- Uploads results to GitHub Security tab
- Fails deployment on CRITICAL/HIGH vulnerabilities
- Can be skipped with `skip_security_scan` input

#### Step 3: Deploy to Code Engine
- Authenticates with IBM Cloud
- Creates or updates Code Engine application
- Configures environment variables
- Sets resource limits (2Gi memory, 1 CPU, 1-5 scale)

#### Step 4: Smoke Testing
- Waits for application to be ready
- Tests health endpoints (`/health` and `/api/v1/health`)
- Verifies deployment success

### 3. Deployment Configuration

The application is deployed with the following configuration:

```yaml
Resources:
  Memory: 2Gi
  CPU: 1
  Min Scale: 1
  Max Scale: 5
  Port: 8000

Environment:
  PYTHONPATH: /app
  CONTAINER_ENV: 1
  LOG_LEVEL: INFO
  # Plus all application-specific variables
```

## Local Testing

### 1. Using GitHub Actions Locally (act)

Install [act](https://github.com/nektos/act) to run GitHub Actions locally:

```bash
# Install act
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run the deployment workflow locally
act workflow_dispatch -W .github/workflows/deploy_code_engine.yml

# Run with specific inputs
act workflow_dispatch -W .github/workflows/deploy_code_engine.yml --input skip_security_scan=false
```

### 2. Manual Testing

#### Test Docker Image Build

```bash
# Build the image locally
docker build -f Dockerfile.codeengine -t rag-modulo-test .

# Test the image
docker run -p 8000:8000 rag-modulo-test

# Test health endpoint
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
```

#### Test Deployment Script

```bash
# Set required environment variables
export IBM_CLOUD_API_KEY="your-api-key"
export IMAGE_URL="us.icr.io/your-namespace/rag-modulo-app:test"
export APP_NAME="rag-modulo-test"
# ... set all other required variables

# Run deployment script
chmod +x ./scripts/deploy_codeengine.sh
./scripts/deploy_codeengine.sh
```

### 3. Security Testing

#### Run Trivy Locally

```bash
# Install Trivy
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Scan the built image
trivy image rag-modulo-test

# Scan with specific severity
trivy image --severity CRITICAL,HIGH rag-modulo-test
```

## Monitoring and Troubleshooting

### 1. Application Monitoring

#### Check Application Status

```bash
# Get application details
ibmcloud ce app get --name rag-modulo-app

# Get application logs
ibmcloud ce app logs --name rag-modulo-app

# Get application revisions
ibmcloud ce revision list --app rag-modulo-app
```

#### Health Checks

- **Health Endpoint**: `https://your-app-url/health`
- **API Health**: `https://your-app-url/api/v1/health`
- **Application Logs**: Available via IBM Cloud CLI

### 2. Common Issues

#### Build Failures

**Issue**: Docker build fails
**Solutions**:
- Check Dockerfile syntax
- Verify all required files are present
- Check Poetry lock file is up to date
- Ensure sufficient disk space

#### Security Scan Failures

**Issue**: Trivy finds CRITICAL/HIGH vulnerabilities
**Solutions**:
- Update base image to latest version
- Update dependencies with `poetry update`
- Review and address specific vulnerabilities
- Use `skip_security_scan: true` for development (not recommended for production)

#### Deployment Failures

**Issue**: Code Engine deployment fails
**Solutions**:
- Verify all required secrets are set
- Check IBM Cloud API key permissions
- Ensure Container Registry namespace exists
- Verify Code Engine project is active

#### Application Startup Issues

**Issue**: Application fails to start
**Solutions**:
- Check environment variables
- Verify database connectivity
- Check vector database connectivity
- Review application logs

### 3. Rollback Procedure

If deployment fails or issues are discovered:

```bash
# List application revisions
ibmcloud ce revision list --app rag-modulo-app

# Rollback to previous revision
ibmcloud ce app update --name rag-modulo-app --image us.icr.io/namespace/app:previous-tag

# Or delete the application entirely
ibmcloud ce app delete --name rag-modulo-app
```

## Security Considerations

### 1. Secrets Management

- **Never commit secrets** to version control
- **Use GitHub Secrets** for sensitive data
- **Rotate secrets regularly**
- **Use least privilege** for IBM Cloud API keys

### 2. Container Security

- **Non-root user**: Application runs as user `backend` (UID 10001)
- **Minimal base image**: Uses Python slim image
- **No unnecessary packages**: Only essential dependencies included
- **Regular updates**: Keep base image and dependencies updated

### 3. Network Security

- **HTTPS only**: All external communication should use HTTPS
- **Environment isolation**: Use separate environments for dev/staging/prod
- **Database security**: Use encrypted connections and strong passwords

## Cost Optimization

### 1. Resource Scaling

- **Scale to zero**: Configure `min-scale: 0` for development environments
- **Right-size resources**: Monitor actual usage and adjust memory/CPU
- **Auto-scaling**: Use Code Engine's built-in auto-scaling

### 2. Image Optimization

- **Multi-stage builds**: Reduces final image size
- **Layer caching**: Reuses unchanged layers
- **CPU-only PyTorch**: Saves ~6GB compared to CUDA version

## Best Practices

### 1. Development Workflow

1. **Test locally** before pushing to GitHub
2. **Use feature branches** for development
3. **Run security scans** on all images
4. **Monitor deployments** and application health

### 2. Production Deployment

1. **Use production secrets** (never development values)
2. **Enable security scanning** (don't skip)
3. **Monitor resource usage** and costs
4. **Set up alerts** for application failures

### 3. Maintenance

1. **Regular updates**: Keep dependencies and base images updated
2. **Security patches**: Apply security updates promptly
3. **Backup strategy**: Ensure data is backed up
4. **Documentation**: Keep deployment docs updated

## Support and Resources

### 1. IBM Cloud Documentation

- [IBM Cloud Code Engine](https://cloud.ibm.com/docs/codeengine)
- [IBM Container Registry](https://cloud.ibm.com/docs/container-registry)
- [IBM Watsonx.ai](https://cloud.ibm.com/docs/watsonxai)

### 2. GitHub Actions

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Trivy Security Scanner](https://github.com/aquasecurity/trivy)

### 3. Project Resources

- [RAG Modulo Documentation](../index.md)
- [API Documentation](../api/index.md)
- [Troubleshooting Guide](../troubleshooting/index.md)

## Changelog

- **v1.0.0** (2025-01-13): Initial deployment implementation
- **v1.1.0** (2025-01-13): Added security scanning and smoke tests
- **v1.2.0** (2025-01-13): Fixed command injection vulnerability and improved error handling
