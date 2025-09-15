# Deployment Guide

This guide covers deploying RAG Modulo in various environments, from local development to production.

## Table of Contents

- [Deployment Overview](#deployment-overview)
- [Prerequisites](#prerequisites)
- [Local Deployment](#local-deployment)
- [Production Deployment](#production-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Deployment Overview

RAG Modulo is designed for containerized deployment with support for:

- **Local Development**: Docker Compose with hot reload
- **Production**: Optimized containers with security hardening
- **Cloud Platforms**: Kubernetes, Docker Swarm, cloud services
- **CI/CD Integration**: Automated deployment pipelines

## Prerequisites

### System Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 50GB+ available space
- **Network**: Stable internet connection for AI services

### Software Requirements

- **Docker**: 20.10+ with Docker Compose 2.0+
- **Make**: For deployment automation
- **Git**: For code deployment
- **curl**: For health checks

### External Services

- **IBM WatsonX**: For AI/ML capabilities
- **PostgreSQL**: Database (included in deployment)
- **Milvus**: Vector database (included in deployment)
- **MinIO**: Object storage (included in deployment)

## Local Deployment

### Quick Start

```bash
# Clone repository
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo

# Deploy locally
make run-services

# Verify deployment
curl http://localhost:8000/health
```

### Development Deployment

```bash
# Development environment with hot reload
make dev-up

# Services available at:
# - Backend: http://localhost:8000
# - Frontend: http://localhost:3000
# - MLflow: http://localhost:5001
```

### Production-like Local Deployment

```bash
# Build production images
make build-all

# Deploy with production settings
make run-ghcr

# Check status
make status
```

## Production Deployment

### Environment Setup

#### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
```

#### 2. Application Deployment

```bash
# Clone repository
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo

# Configure environment
cp env.example .env
# Edit .env with production values

# Deploy
make run-services

# Verify deployment
make health-check
```

### Production Configuration

#### Environment Variables

```bash
# Production settings
PRODUCTION_MODE=true
DEBUG=false
LOG_LEVEL=INFO

# Security
JWT_SECRET_KEY=your-secure-secret-key
SKIP_AUTH=false

# Database
COLLECTIONDB_HOST=postgres
COLLECTIONDB_NAME=rag_modulo_prod
COLLECTIONDB_USER=rag_user
COLLECTIONDB_PASS=secure-password

# AI Services
WATSONX_APIKEY=your-watsonx-api-key
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_INSTANCE_ID=your-instance-id
```

#### Security Hardening

```bash
# Use production images
make build-all

# Enable security features
export SECURITY_SCAN=true
export VULNERABILITY_CHECK=true

# Run security checks
make security-check
```

### SSL/TLS Configuration

#### Using Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone -d your-domain.com

# Configure nginx with SSL
# (See nginx configuration examples)
```

#### Using Reverse Proxy

```yaml
# docker-compose.prod.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - backend
      - frontend
```

## Cloud Deployment

### AWS Deployment

#### Using ECS

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com

# Tag and push images
docker tag rag-modulo/backend:latest your-account.dkr.ecr.us-east-1.amazonaws.com/rag-modulo-backend:latest
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/rag-modulo-backend:latest

# Deploy to ECS
aws ecs create-service --cluster rag-modulo-cluster --service-name rag-modulo-service --task-definition rag-modulo-task
```

#### Using EKS

```bash
# Create EKS cluster
eksctl create cluster --name rag-modulo-cluster --region us-east-1

# Deploy with kubectl
kubectl apply -f k8s/
```

### Google Cloud Deployment

#### Using GKE

```bash
# Create GKE cluster
gcloud container clusters create rag-modulo-cluster --zone us-central1-a

# Deploy application
kubectl apply -f k8s/
```

### Azure Deployment

#### Using AKS

```bash
# Create AKS cluster
az aks create --resource-group rag-modulo-rg --name rag-modulo-cluster --node-count 3

# Deploy application
kubectl apply -f k8s/
```

## Configuration

### Application Configuration

#### Backend Configuration

```python
# backend/core/config.py
class Settings(BaseSettings):
    # Production settings
    production_mode: bool = Field(default=False, env="PRODUCTION_MODE")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Security
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    skip_auth: bool = Field(default=False, env="SKIP_AUTH")
    
    # Database
    collectiondb_host: str = Field(default="postgres", env="COLLECTIONDB_HOST")
    collectiondb_name: str = Field(default="rag_modulo", env="COLLECTIONDB_NAME")
    
    # AI Services
    watsonx_apikey: str = Field(env="WATSONX_APIKEY")
    watsonx_url: str = Field(env="WATSONX_URL")
```

#### Frontend Configuration

```javascript
// webui/src/config.js
const config = {
  apiUrl: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  environment: process.env.NODE_ENV || 'development',
  features: {
    analytics: process.env.REACT_APP_ANALYTICS_ENABLED === 'true',
    debug: process.env.REACT_APP_DEBUG === 'true'
  }
};
```

### Database Configuration

#### PostgreSQL Setup

```sql
-- Create production database
CREATE DATABASE rag_modulo_prod;
CREATE USER rag_user WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE rag_modulo_prod TO rag_user;
```

#### Milvus Configuration

```yaml
# milvus-config.yaml
etcd:
  endpoints:
    - milvus-etcd:2379
  rootPath: by-dev
  metaPath: meta

common:
  security:
    authorizationEnabled: false
```

### Monitoring Configuration

#### Prometheus Setup

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'rag-modulo-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
```

#### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "RAG Modulo Monitoring",
    "panels": [
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      }
    ]
  }
}
```

## Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/database

# Vector database health
curl http://localhost:8000/health/vector-db

# AI service health
curl http://localhost:8000/health/ai-services
```

### Logging

#### Log Configuration

```python
# backend/core/logging.py
import logging
import sys

def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/app/logs/rag_modulo.log')
        ]
    )
```

#### Log Monitoring

```bash
# View application logs
docker logs rag_modulo-backend-1

# Follow logs in real-time
docker logs -f rag_modulo-backend-1

# View all service logs
make logs
```

### Metrics

#### Application Metrics

- **Response Time**: API endpoint performance
- **Throughput**: Requests per second
- **Error Rate**: Failed request percentage
- **Resource Usage**: CPU, memory, disk usage

#### Business Metrics

- **Document Processing**: Documents processed per hour
- **Search Performance**: Search query response time
- **User Activity**: Active users, session duration
- **AI Service Usage**: WatsonX API calls, costs

### Alerting

#### Alert Rules

```yaml
# alerts.yml
groups:
  - name: rag-modulo
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
```

## Troubleshooting

### Common Deployment Issues

#### Container Won't Start

```bash
# Check container logs
docker logs rag_modulo-backend-1

# Check container status
docker ps -a

# Restart container
docker restart rag_modulo-backend-1
```

#### Database Connection Issues

```bash
# Test database connectivity
docker exec rag_modulo-backend-1 python -c "
from core.config import Settings
from sqlalchemy import create_engine
settings = Settings()
engine = create_engine(settings.database_url)
print('Database connection successful')
"

# Check database logs
docker logs rag_modulo-postgres-1
```

#### AI Service Issues

```bash
# Test WatsonX connectivity
curl -H "Authorization: Bearer $WATSONX_APIKEY" \
     -H "Content-Type: application/json" \
     "$WATSONX_URL/v1/embeddings" \
     -d '{"input": "test", "model": "sentence-transformers/all-MiniLM-L6-v2"}'

# Check AI service logs
docker logs rag_modulo-backend-1 | grep -i watson
```

#### Performance Issues

```bash
# Check resource usage
docker stats

# Profile application
make dev-profile

# Check slow queries
docker exec rag_modulo-postgres-1 psql -U rag_user -d rag_modulo -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"
```

### Recovery Procedures

#### Database Recovery

```bash
# Backup database
docker exec rag_modulo-postgres-1 pg_dump -U rag_user rag_modulo > backup.sql

# Restore database
docker exec -i rag_modulo-postgres-1 psql -U rag_user rag_modulo < backup.sql
```

#### Application Recovery

```bash
# Rollback to previous version
git checkout previous-stable-tag
make build-all
make run-services

# Restart all services
make restart-app
```

### Support

#### Getting Help

- **Documentation**: Check this guide and inline docs
- **Issues**: Create a GitHub issue
- **Discussions**: Use GitHub Discussions
- **Logs**: Always include relevant logs when reporting issues

#### Emergency Contacts

- **Critical Issues**: Create urgent GitHub issue
- **Security Issues**: Use private security reporting
- **Performance Issues**: Include metrics and logs

## Next Steps

- [Development Guide](../development/README.md)
- [API Documentation](../api/README.md)
- [Architecture Overview](../architecture/README.md)
- [Security Guide](../security/README.md)
