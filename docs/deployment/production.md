# Production Deployment Guide

This guide covers deploying RAG Modulo in production environments with security, scalability, and reliability considerations.

## Table of Contents

- [Production Overview](#production-overview)
- [Infrastructure Requirements](#infrastructure-requirements)
- [Security Configuration](#security-configuration)
- [Deployment Steps](#deployment-steps)
- [Monitoring & Logging](#monitoring--logging)
- [Backup & Recovery](#backup--recovery)
- [Scaling](#scaling)
- [Maintenance](#maintenance)

## Production Overview

### Production Architecture

RAG Modulo production deployment includes:

- **Load Balancer**: Nginx or cloud load balancer
- **Application Servers**: Multiple backend instances
- **Database Cluster**: PostgreSQL with replication
- **Vector Database**: Milvus cluster
- **Object Storage**: MinIO or cloud storage
- **Monitoring**: Prometheus + Grafana
- **Logging**: Centralized logging system

### Production Principles

- **Security First**: All communications encrypted, secure defaults
- **High Availability**: Redundant components, failover mechanisms
- **Scalability**: Horizontal scaling capabilities
- **Observability**: Comprehensive monitoring and logging
- **Disaster Recovery**: Backup and recovery procedures

## Infrastructure Requirements

### Minimum Requirements

- **CPU**: 8 cores per application server
- **RAM**: 32GB per application server
- **Storage**: 500GB SSD per server
- **Network**: 1Gbps bandwidth
- **Load Balancer**: 2+ instances for HA

### Recommended Requirements

- **CPU**: 16+ cores per application server
- **RAM**: 64GB+ per application server
- **Storage**: 1TB+ NVMe SSD per server
- **Network**: 10Gbps bandwidth
- **Load Balancer**: 3+ instances for HA

### External Dependencies

- **IBM WatsonX**: AI/ML services
- **SSL Certificates**: For HTTPS
- **DNS**: Domain name resolution
- **CDN**: For static assets (optional)

## Security Configuration

### Environment Security

#### Production Environment Variables

```bash
# Production settings
PRODUCTION_MODE=true
DEBUG=false
LOG_LEVEL=INFO
SECURITY_SCAN=true

# Security
JWT_SECRET_KEY=your-secure-random-secret-key-256-bits
SKIP_AUTH=false
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Database security
COLLECTIONDB_SSL_MODE=require
COLLECTIONDB_SSL_CERT=/path/to/client-cert.pem
COLLECTIONDB_SSL_KEY=/path/to/client-key.pem
COLLECTIONDB_SSL_ROOT_CERT=/path/to/ca-cert.pem

# AI Services (use production credentials)
WATSONX_APIKEY=your-production-watsonx-api-key
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_INSTANCE_ID=your-production-instance-id
```

#### SSL/TLS Configuration

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Application Security

#### Authentication & Authorization

```python
# backend/core/security.py
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
import jwt
from datetime import datetime, timedelta

security = HTTPBearer()

class SecurityConfig:
    """Production security configuration."""
    
    JWT_SECRET_KEY: str = Field(env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30
    
    def verify_token(self, token: str) -> dict:
        """Verify JWT token with production security."""
        try:
            payload = jwt.decode(
                token, 
                self.JWT_SECRET_KEY, 
                algorithms=[self.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
```

#### Input Validation

```python
# backend/core/validation.py
from pydantic import BaseModel, validator, Field
import re

class ProductionInputValidator(BaseModel):
    """Production input validation."""
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain digit')
        return v
```

## Deployment Steps

### 1. Infrastructure Setup

#### Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Configure Docker for production
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

sudo systemctl restart docker
```

#### SSL Certificate Setup

```bash
# Using Let's Encrypt
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. Application Deployment

#### Production Configuration

```bash
# Clone repository
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo

# Create production environment
cp env.example .env.prod

# Edit production configuration
nano .env.prod
```

#### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.backend
    environment:
      - PRODUCTION_MODE=true
      - DEBUG=false
      - LOG_LEVEL=INFO
    env_file:
      - .env.prod
    volumes:
      - backend_data:/mnt/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "healthcheck.py"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./webui
      dockerfile: Dockerfile.frontend
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=rag_modulo_prod
      - POSTGRES_USER=rag_user
      - POSTGRES_PASSWORD=${COLLECTIONDB_PASS}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  milvus-standalone:
    image: milvusdb/milvus:v2.3.0
    environment:
      - ETCD_ENDPOINTS=milvus-etcd:2379
    volumes:
      - milvus_data:/var/lib/milvus
    restart: unless-stopped

volumes:
  backend_data:
  postgres_data:
  milvus_data:
```

#### Deploy Application

```bash
# Build production images
make build-all

# Deploy with production configuration
docker compose -f docker-compose.prod.yml up -d

# Verify deployment
make health-check
```

### 3. Database Setup

#### PostgreSQL Configuration

```sql
-- Create production database
CREATE DATABASE rag_modulo_prod;
CREATE USER rag_user WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE rag_modulo_prod TO rag_user;

-- Configure for production
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();
```

#### Database Backup Setup

```bash
# Create backup script
cat > backup-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker exec rag_modulo-postgres-1 pg_dump -U rag_user rag_modulo_prod > $BACKUP_DIR/backup_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
EOF

chmod +x backup-db.sh

# Schedule daily backups
crontab -e
# Add: 0 2 * * * /path/to/backup-db.sh
```

## Monitoring & Logging

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alerts.yml"

scrape_configs:
  - job_name: 'rag-modulo-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'rag-modulo-postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'rag-modulo-milvus'
    static_configs:
      - targets: ['milvus-standalone:9091']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "RAG Modulo Production Dashboard",
    "panels": [
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends",
            "legendFormat": "Active connections"
          }
        ]
      }
    ]
  }
}
```

### Log Management

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:8.8.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  logstash:
    image: docker.elastic.co/logstash/logstash:8.8.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

## Backup & Recovery

### Backup Strategy

#### Database Backups

```bash
# Daily full backup
pg_dump -h postgres -U rag_user rag_modulo_prod > backup_$(date +%Y%m%d).sql

# Incremental backup (WAL files)
pg_basebackup -h postgres -U rag_user -D /backups/incremental/$(date +%Y%m%d_%H%M%S)
```

#### Application Data Backups

```bash
# Backup application data
tar -czf app_data_$(date +%Y%m%d).tar.gz volumes/

# Backup configuration
cp -r .env.prod nginx.conf /backups/config/
```

### Recovery Procedures

#### Database Recovery

```bash
# Restore from backup
psql -h postgres -U rag_user rag_modulo_prod < backup_20240101.sql

# Point-in-time recovery
pg_restore -h postgres -U rag_user -d rag_modulo_prod backup_20240101.dump
```

#### Application Recovery

```bash
# Restore application data
tar -xzf app_data_20240101.tar.gz

# Restore configuration
cp /backups/config/.env.prod .
cp /backups/config/nginx.conf .

# Restart services
docker compose -f docker-compose.prod.yml restart
```

## Scaling

### Horizontal Scaling

#### Load Balancer Configuration

```nginx
# nginx.conf for multiple backend instances
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Database Scaling

```yaml
# PostgreSQL with read replicas
services:
  postgres-master:
    image: postgres:15
    environment:
      - POSTGRES_DB=rag_modulo_prod
      - POSTGRES_USER=rag_user
      - POSTGRES_PASSWORD=${COLLECTIONDB_PASS}
    volumes:
      - postgres_master_data:/var/lib/postgresql/data

  postgres-replica:
    image: postgres:15
    environment:
      - POSTGRES_DB=rag_modulo_prod
      - POSTGRES_USER=rag_user
      - POSTGRES_PASSWORD=${COLLECTIONDB_PASS}
      - PGUSER=rag_user
    command: |
      bash -c "
      until pg_basebackup -h postgres-master -D /var/lib/postgresql/data -U rag_user -v -P -W; do
        echo 'Waiting for master to be available...'
        sleep 1s
      done
      echo 'Backup done, starting replica...'
      chmod 0700 /var/lib/postgresql/data
      postgres
      "
```

### Vertical Scaling

#### Resource Optimization

```bash
# Monitor resource usage
docker stats

# Optimize container resources
docker update --cpus="2.0" --memory="4g" rag_modulo-backend-1
```

## Maintenance

### Regular Maintenance Tasks

#### Daily Tasks

- Check system health: `make health-check`
- Review logs: `docker logs rag_modulo-backend-1`
- Monitor metrics: Check Grafana dashboard
- Verify backups: Ensure backups completed successfully

#### Weekly Tasks

- Update dependencies: `make check-deps`
- Security scan: `make security-check`
- Performance review: Analyze metrics trends
- Clean up old logs: `docker system prune`

#### Monthly Tasks

- Update system packages: `sudo apt update && sudo apt upgrade`
- Review security patches: Check for vulnerabilities
- Capacity planning: Analyze resource usage trends
- Disaster recovery test: Test backup restoration

### Update Procedures

#### Application Updates

```bash
# Pull latest changes
git pull origin main

# Build new images
make build-all

# Deploy with zero downtime
docker compose -f docker-compose.prod.yml up -d --no-deps backend

# Verify deployment
make health-check
```

#### System Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Update Docker
sudo apt install docker-ce docker-ce-cli containerd.io

# Restart services
sudo systemctl restart docker
docker compose -f docker-compose.prod.yml restart
```

## Troubleshooting

### Common Production Issues

#### High Memory Usage

```bash
# Check memory usage
docker stats

# Optimize application
# - Reduce cache sizes
# - Optimize database queries
# - Implement connection pooling
```

#### Database Performance

```sql
-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Check connection usage
SELECT count(*) FROM pg_stat_activity;
```

#### SSL Certificate Issues

```bash
# Check certificate expiration
openssl x509 -in /etc/letsencrypt/live/yourdomain.com/cert.pem -noout -dates

# Renew certificate
sudo certbot renew --dry-run
```

### Emergency Procedures

#### Service Outage

1. **Check service status**: `docker compose -f docker-compose.prod.yml ps`
2. **Check logs**: `docker logs rag_modulo-backend-1`
3. **Restart services**: `docker compose -f docker-compose.prod.yml restart`
4. **Failover**: Switch to backup servers if available
5. **Notify stakeholders**: Send incident notification

#### Data Corruption

1. **Stop services**: `docker compose -f docker-compose.prod.yml stop`
2. **Restore from backup**: Use latest known good backup
3. **Verify data integrity**: Run data validation checks
4. **Restart services**: `docker compose -f docker-compose.prod.yml start`
5. **Monitor closely**: Watch for recurring issues

## Next Steps

- [Development Guide](../development/README.md)
- [Security Guide](../security/README.md)
- [Monitoring Guide](../monitoring/README.md)
- [Disaster Recovery Plan](../disaster-recovery/README.md)
