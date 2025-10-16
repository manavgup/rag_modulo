# IBM Cloud Code Engine Deployment

This guide covers deploying RAG Modulo to IBM Cloud Code Engine using the hybrid Terraform + Ansible architecture.

## Overview

IBM Cloud Code Engine is a fully managed serverless platform that automatically scales your applications based on demand. This deployment leverages Code Engine for hosting the RAG Modulo backend and frontend applications while using managed services for data persistence.

## Architecture

```mermaid
graph TB
    subgraph "IBM Cloud Code Engine"
        CE[Code Engine Project]
        BE[Backend App]
        FE[Frontend App]
    end

    subgraph "Managed Services"
        PG[PostgreSQL]
        OS[Object Storage]
        ZL[Zilliz Cloud]
        ES[Event Streams]
    end

    subgraph "External Services"
        CR[Container Registry]
        MON[Monitoring]
    end

    CE --> BE
    CE --> FE
    BE --> PG
    BE --> OS
    BE --> ZL
    BE --> ES
    FE --> BE
    CR --> BE
    CR --> FE
    MON --> BE
    MON --> FE
```

## Prerequisites

### 1. IBM Cloud Account

- Active IBM Cloud account
- IBM Cloud CLI installed and configured
- Appropriate permissions for Code Engine and managed services

### 2. Container Registry

- IBM Cloud Container Registry (ICR) access
- Container images built and pushed to registry
- Registry credentials configured

### 3. Required Tools

- Terraform >= 1.5
- Ansible >= 6.0
- IBM Cloud CLI
- Docker (for building images)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit configuration
nano .env
```

### 3. Deploy Infrastructure

```bash
# Navigate to Terraform directory
cd deployment/terraform/environments/ibm

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file="dev.tfvars"

# Apply infrastructure
terraform apply -var-file="dev.tfvars"
```

### 4. Deploy Applications

```bash
# Navigate to Ansible directory
cd deployment/ansible

# Install collections
ansible-galaxy collection install -r requirements.yml

# Deploy applications
ansible-playbook -i inventories/ibm/hosts.yml playbooks/deploy-rag-modulo.yml
```

## Detailed Configuration

### Environment Variables

#### Development Environment

```bash
# Project configuration
PROJECT_NAME=rag-modulo
ENVIRONMENT=dev
REGION=us-south

# IBM Cloud configuration
IBMCLOUD_API_KEY=your-api-key
RESOURCE_GROUP_ID=your-resource-group-id

# Container registry
CONTAINER_REGISTRY_URL=us.icr.io
CONTAINER_REGISTRY_USERNAME=iamapikey
CONTAINER_REGISTRY_PASSWORD=your-api-key

# Image tags
BACKEND_IMAGE_TAG=v1.0.0
FRONTEND_IMAGE_TAG=v1.0.0

# Scaling (development)
BACKEND_MIN_SCALE=1
BACKEND_MAX_SCALE=3
FRONTEND_MIN_SCALE=1
FRONTEND_MAX_SCALE=2
```

#### Production Environment

```bash
# Project configuration
PROJECT_NAME=rag-modulo
ENVIRONMENT=production
REGION=us-south

# IBM Cloud configuration
IBMCLOUD_API_KEY=your-production-api-key
RESOURCE_GROUP_ID=your-production-resource-group-id

# Container registry
CONTAINER_REGISTRY_URL=us.icr.io
CONTAINER_REGISTRY_USERNAME=iamapikey
CONTAINER_REGISTRY_PASSWORD=your-production-api-key

# Image tags (production - specific versions)
BACKEND_IMAGE_TAG=v1.0.0
FRONTEND_IMAGE_TAG=v1.0.0

# Scaling (production - high availability)
BACKEND_MIN_SCALE=3
BACKEND_MAX_SCALE=20
FRONTEND_MIN_SCALE=2
FRONTEND_MAX_SCALE=10

# Production safeguards
ENABLE_PRODUCTION_SAFEGUARDS=true
```

### Terraform Configuration

#### Main Configuration

```hcl
# deployment/terraform/environments/ibm/main.tf
module "managed_services" {
  source = "../../modules/ibm-cloud/managed-services"

  project_name = var.project_name
  environment  = var.environment
  region       = var.region
  resource_group_id = data.ibm_resource_group.main.id

  # Service plans
  postgresql_plan        = var.postgresql_plan
  object_storage_plan    = var.object_storage_plan
  zilliz_plan           = var.zilliz_plan
  event_streams_plan    = var.event_streams_plan

  # PostgreSQL configuration
  postgresql_admin_password = var.postgresql_admin_password

  # Production safeguards
  enable_production_safeguards = var.enable_production_safeguards
}

module "code_engine" {
  source = "../../modules/ibm-cloud/code-engine"

  project_name = var.project_name
  environment  = var.environment
  resource_group_id = data.ibm_resource_group.main.id

  # Container registry configuration
  container_registry_url      = var.container_registry_url
  container_registry_username = var.container_registry_username
  container_registry_password = var.container_registry_password

  # Image tags
  backend_image_tag  = var.backend_image_tag
  frontend_image_tag = var.frontend_image_tag

  # Managed services integration
  postgresql_host     = module.managed_services.postgresql_host
  postgresql_port     = module.managed_services.postgresql_port
  postgresql_database = module.managed_services.postgresql_database
  postgresql_username = module.managed_services.postgresql_username
  postgresql_password = module.managed_services.postgresql_password
  postgresql_instance_id = module.managed_services.postgresql_instance_id

  # ... other service configurations
}
```

#### Environment Variables

```hcl
# deployment/terraform/environments/ibm/variables.tf
variable "project_name" {
  description = "Name of the project (used for resource naming)"
  type        = string
  default     = "rag-modulo"
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

# ... other variables
```

### Ansible Configuration

#### Playbook Structure

```yaml
# deployment/ansible/playbooks/deploy-rag-modulo.yml
---
- name: Deploy RAG Modulo to IBM Cloud Code Engine
  hosts: localhost
  gather_facts: false
  vars:
    project_name: "{{ project_name | default('rag-modulo') }}"
    environment: "{{ environment | default('dev') }}"
    region: "{{ region | default('us-south') }}"
    # ... other variables

  tasks:
    - name: Validate required variables
      ansible.builtin.assert:
        that:
          - ibmcloud_api_key is defined
          - resource_group_id is defined
          # ... other validations

    - name: Install IBM Cloud CLI
      ansible.builtin.package:
        name: "{{ item }}"
        state: present
      loop:
        - curl
        - jq

    # ... deployment tasks
```

#### Inventory Configuration

```yaml
# deployment/ansible/inventories/ibm/hosts.yml
---
all:
  children:
    ibm_cloud:
      hosts:
        localhost:
          ansible_connection: local
          ansible_python_interpreter: "{{ ansible_playbook_python }}"

    development:
      hosts:
        localhost:
          ansible_connection: local
          ansible_python_interpreter: "{{ ansible_playbook_python }}"

    production:
      hosts:
        localhost:
          ansible_connection: local
          ansible_python_interpreter: "{{ ansible_playbook_python }}"

  vars:
    ansible_connection: local
    ansible_python_interpreter: "{{ ansible_playbook_python }}"

    # IBM Cloud default settings
    region: "us-south"
    container_registry_url: "us.icr.io"
    container_registry_username: "iamapikey"
```

## Application Configuration

### Backend Application

#### Environment Variables

```bash
# Database configuration
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require

# Vector database configuration
MILVUS_HOST=zilliz-endpoint
MILVUS_API_KEY=zilliz-api-key

# Object storage configuration
MINIO_ENDPOINT=object-storage-endpoint
MINIO_ACCESS_KEY=access-key
MINIO_SECRET_KEY=secret-key
MINIO_BUCKET_NAME=bucket-name

# Messaging configuration
KAFKA_BROKERS=event-streams-endpoint
KAFKA_API_KEY=event-streams-api-key

# Application configuration
ENVIRONMENT=production
DEBUG=false
SKIP_AUTH=false
LOG_LEVEL=INFO
```

#### Health Checks

```yaml
# Health check configuration
health_check:
  type: "http"
  path: "/health"
  port: 8000
  initial_delay_seconds: 30
  period_seconds: 10
  timeout_seconds: 5
  failure_threshold: 3
  success_threshold: 1
```

### Frontend Application

#### Environment Variables

```bash
# API configuration
REACT_APP_API_URL=https://backend-app.example.com
REACT_APP_ENVIRONMENT=production
REACT_APP_DEBUG=false
```

#### Health Checks

```yaml
# Health check configuration
health_check:
  type: "http"
  path: "/"
  port: 3000
  initial_delay_seconds: 30
  period_seconds: 10
  timeout_seconds: 5
  failure_threshold: 3
  success_threshold: 1
```

## Scaling Configuration

### Auto-scaling

Code Engine automatically scales applications based on:

- **CPU Utilization**: Target 70% CPU usage
- **Memory Usage**: Target 80% memory usage
- **Request Rate**: Scale based on incoming requests

### Manual Scaling

```bash
# Scale backend application
ibmcloud ce app update rag-modulo-backend --min-scale 5 --max-scale 20

# Scale frontend application
ibmcloud ce app update rag-modulo-frontend --min-scale 3 --max-scale 10
```

### Resource Limits

#### Development

```yaml
backend:
  cpu: "0.5"
  memory: "1Gi"
  min_scale: 1
  max_scale: 3

frontend:
  cpu: "0.25"
  memory: "512Mi"
  min_scale: 1
  max_scale: 2
```

#### Production

```yaml
backend:
  cpu: "2"
  memory: "4Gi"
  min_scale: 3
  max_scale: 20

frontend:
  cpu: "1"
  memory: "2Gi"
  min_scale: 2
  max_scale: 10
```

## Monitoring and Logging

### Application Monitoring

```bash
# View application logs
ibmcloud ce app logs rag-modulo-backend
ibmcloud ce app logs rag-modulo-frontend

# View application status
ibmcloud ce app get rag-modulo-backend
ibmcloud ce app get rag-modulo-frontend
```

### Health Checks

```bash
# Check backend health
curl https://backend-app.example.com/health

# Check frontend health
curl https://frontend-app.example.com/
```

### Metrics

Code Engine provides built-in metrics for:

- **Request Rate**: Requests per second
- **Response Time**: Average response time
- **Error Rate**: Percentage of failed requests
- **Resource Usage**: CPU and memory utilization

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Symptoms:**

- Application status shows "Failed"
- No logs available

**Solutions:**

```bash
# Check application status
ibmcloud ce app get rag-modulo-backend

# View detailed logs
ibmcloud ce app logs rag-modulo-backend --follow

# Check resource limits
ibmcloud ce app get rag-modulo-backend --output json | jq '.spec.template.spec.containers[0].resources'
```

#### 2. Service Connection Issues

**Symptoms:**

- Application starts but can't connect to services
- Database connection errors

**Solutions:**

```bash
# Verify service bindings
ibmcloud ce app get rag-modulo-backend --output json | jq '.spec.template.spec.serviceBindings'

# Check environment variables
ibmcloud ce app get rag-modulo-backend --output json | jq '.spec.template.spec.containers[0].env'
```

#### 3. Scaling Issues

**Symptoms:**

- Application doesn't scale as expected
- Performance issues under load

**Solutions:**

```bash
# Check scaling configuration
ibmcloud ce app get rag-modulo-backend --output json | jq '.spec.template.spec.scale'

# Update scaling settings
ibmcloud ce app update rag-modulo-backend --min-scale 3 --max-scale 10
```

### Debug Commands

```bash
# Get application details
ibmcloud ce app get rag-modulo-backend --output json

# View recent logs
ibmcloud ce app logs rag-modulo-backend --tail 100

# Check service bindings
ibmcloud ce app get rag-modulo-backend --output json | jq '.spec.template.spec.serviceBindings'

# View environment variables
ibmcloud ce app get rag-modulo-backend --output json | jq '.spec.template.spec.containers[0].env'
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

### 1. Network Security

- All communications use HTTPS/TLS
- Private endpoints for managed services
- VPC integration for network isolation

### 2. Access Control

- IAM roles with least privilege
- Service-to-service authentication
- API key rotation

### 3. Data Protection

- Encryption at rest and in transit
- Secure secret management
- Regular security updates

## Cost Optimization

### 1. Resource Optimization

- Right-size applications based on usage
- Use auto-scaling to match demand
- Monitor resource utilization

### 2. Storage Optimization

- Use appropriate storage classes
- Implement lifecycle policies
- Regular cleanup of unused data

### 3. Monitoring

- Track costs in real-time
- Set budget alerts
- Regular cost reviews

## Next Steps

1. **Customize Configuration**: Adjust variables for your environment
2. **Deploy Infrastructure**: Use Terraform to provision resources
3. **Deploy Applications**: Use Ansible to deploy applications
4. **Configure Monitoring**: Set up monitoring and alerting
5. **Test Deployment**: Verify all components are working correctly

## Related Documentation

- [Terraform + Ansible Architecture](terraform-ansible-architecture.md)
- [Managed Services Strategy](managed-services.md)
- [Ansible Automation Guide](ansible-automation.md)
- [Monitoring and Observability](monitoring-observability.md)
- [Security Hardening](security-hardening.md)
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
