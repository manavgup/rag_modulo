# Security Deployment Guide

This guide covers security best practices for deploying RAG Modulo, including container security, secrets management, network policies, and compliance requirements.

## Table of Contents

- [Overview](#overview)
- [Container Security](#container-security)
- [Secrets Management](#secrets-management)
- [Network Security](#network-security)
- [Authentication & Authorization](#authentication--authorization)
- [API Security](#api-security)
- [Data Protection](#data-protection)
- [Security Scanning](#security-scanning)
- [Compliance & Auditing](#compliance--auditing)

## Overview

RAG Modulo implements defense-in-depth security with multiple layers:

1. **Pre-commit Hooks**: Detect secrets before commit (detect-secrets)
2. **CI/CD Pipeline**: Gitleaks + TruffleHog scanning
3. **Container Security**: Trivy + Bandit + Safety scanning
4. **Runtime Security**: Non-root containers, read-only filesystems
5. **Network Security**: TLS/SSL, network policies, firewalls
6. **Application Security**: JWT auth, OIDC integration, RBAC

**Security Workflow** (from CLAUDE.md):

```bash
# Local secret scanning
make security-check

# Pre-commit hooks (automatic)
detect-secrets scan --baseline .secrets.baseline

# CI/CD scanning (automatic on push)
# - Gitleaks (secrets)
# - TruffleHog (secrets)
# - Trivy (container vulnerabilities)
# - Bandit (Python security)
# - Safety (dependency vulnerabilities)
```

## Container Security

### Non-Root User Containers

**Backend Container** (`backend/Dockerfile.backend`):

```dockerfile
# Create non-root user and group
RUN groupadd --gid 10001 backend && \
    useradd --uid 10001 -g backend -M -d /nonexistent backend && \
    mkdir -p /app/logs && \
    chown -R backend:backend /app && \
    chmod -R 755 /app && \
    chmod 777 /app/logs

# Switch to non-root user
USER backend

# Security benefits:
# - Prevents privilege escalation
# - Limits filesystem access
# - Reduces attack surface
```

**Kubernetes Pod Security**:

```yaml
# backend-deployment.yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
      containers:
      - name: backend
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
              - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: tmp
        emptyDir: {}
      - name: logs
        emptyDir: {}
```

### Image Security

**Multi-Stage Builds** (reduces attack surface):

```dockerfile
# Stage 1: Builder (contains build tools, compilers)
FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y build-essential curl
# ... install dependencies ...

# Stage 2: Final runtime (minimal, no build tools)
FROM python:3.12-slim
# Copy only compiled packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Final image size: ~800MB (vs 2GB+ with build tools)
```

**Image Scanning with Trivy**:

```bash
# Scan local image
docker build -t rag-modulo-backend:test -f backend/Dockerfile.backend .
trivy image rag-modulo-backend:test

# Scan published image
trivy image ghcr.io/manavgup/rag_modulo/backend:latest

# Fail on high/critical vulnerabilities
trivy image --severity HIGH,CRITICAL --exit-code 1 rag-modulo-backend:test
```

**CI/CD Image Scanning** (`.github/workflows/03-build-secure.yml`):

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.IMAGE_NAME }}:${{ github.sha }}
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'

- name: Upload Trivy results to GitHub Security
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: 'trivy-results.sarif'
```

### Dependency Security

**Python Dependency Scanning**:

```bash
# Safety (checks known vulnerabilities)
poetry run safety check

# Bandit (static analysis for security issues)
poetry run bandit -r backend/rag_solution/ -ll

# Both run automatically in CI/CD:
# - Pre-commit hooks
# - GitHub Actions (02-security.yml)
```

**Package Updates**:

```bash
# Update dependencies (with security patches)
poetry update

# Update specific package
poetry update package-name

# Check for outdated packages
poetry show --outdated

# ALWAYS run poetry lock after updating pyproject.toml
poetry lock
```

## Secrets Management

### Secret Detection (3-Layer Defense)

**Layer 1: Pre-commit Hooks** (< 1 sec):

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.4.0
  hooks:
    - id: detect-secrets
      args: ['--baseline', '.secrets.baseline']
```

```bash
# Update baseline for false positives
detect-secrets scan --baseline .secrets.baseline
detect-secrets audit .secrets.baseline
```

**Layer 2: Local Testing** (~2 sec):

```bash
# Run before pushing
make pre-commit-run

# Includes Gitleaks scanning
gitleaks detect --source . --verbose
```

**Layer 3: CI/CD Pipeline** (~45 sec):

```yaml
# .github/workflows/02-security.yml
- name: Gitleaks Secret Scanning
  uses: gitleaks/gitleaks-action@v2
  with:
    config-path: .gitleaks.toml

- name: TruffleHog Secret Scanning
  uses: trufflesecurity/trufflehog@main
  with:
    path: ./
    base: ${{ github.event.repository.default_branch }}
    head: HEAD
```

**Supported Secret Types**:
- Cloud: AWS, Azure, GCP
- LLM APIs: OpenAI, Anthropic, WatsonX, Gemini
- Infrastructure: PostgreSQL, MinIO, MLFlow, JWT
- Version Control: GitHub, GitLab tokens

### Docker Secrets

**Docker Compose Secrets**:

```yaml
# docker-compose-production.yml
services:
  backend:
    secrets:
      - postgres_password
      - jwt_secret
      - watsonx_api_key
    environment:
      - COLLECTIONDB_PASS_FILE=/run/secrets/postgres_password
      - JWT_SECRET_KEY_FILE=/run/secrets/jwt_secret

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  watsonx_api_key:
    file: ./secrets/watsonx_api_key.txt
```

**Docker Swarm Secrets**:

```bash
# Create secrets in Swarm
echo "secure-password" | docker secret create postgres_password -
echo "secure-jwt-secret-min-32-chars" | docker secret create jwt_secret -

# Use in service
docker service create \
  --name rag-modulo-backend \
  --secret postgres_password \
  --secret jwt_secret \
  ghcr.io/manavgup/rag_modulo/backend:latest
```

### Kubernetes Secrets

**Creating Secrets**:

```bash
# From literal values
kubectl create secret generic rag-modulo-secrets \
  --from-literal=postgres-password='secure-password' \
  --from-literal=jwt-secret='secure-jwt-secret-min-32-chars' \
  --namespace=rag-modulo

# From .env file (DO NOT commit .env to git!)
kubectl create secret generic rag-modulo-secrets \
  --from-env-file=.env \
  --namespace=rag-modulo

# From files
kubectl create secret generic rag-modulo-secrets \
  --from-file=postgres-password=./secrets/postgres_password.txt \
  --from-file=jwt-secret=./secrets/jwt_secret.txt \
  --namespace=rag-modulo
```

**Using Secrets in Pods**:

```yaml
# backend-deployment.yaml
env:
- name: COLLECTIONDB_PASS
  valueFrom:
    secretKeyRef:
      name: rag-modulo-secrets
      key: postgres-password
- name: JWT_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: rag-modulo-secrets
      key: jwt-secret
```

**Encrypted Secrets with Sealed Secrets**:

```bash
# Install sealed-secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Create sealed secret (safe to commit to git)
kubectl create secret generic rag-modulo-secrets \
  --from-literal=jwt-secret='my-secret' \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

# Apply sealed secret
kubectl apply -f sealed-secret.yaml
```

### Cloud Provider Secret Managers

**AWS Secrets Manager**:

```bash
# Store secret
aws secretsmanager create-secret \
  --name rag-modulo/postgres-password \
  --secret-string "secure-password"

# Retrieve in application
aws secretsmanager get-secret-value \
  --secret-id rag-modulo/postgres-password \
  --query SecretString \
  --output text
```

**Azure Key Vault**:

```bash
# Store secret
az keyvault secret set \
  --vault-name rag-modulo-vault \
  --name postgres-password \
  --value "secure-password"

# Retrieve in application
az keyvault secret show \
  --vault-name rag-modulo-vault \
  --name postgres-password \
  --query value \
  --output tsv
```

**Google Secret Manager**:

```bash
# Store secret
echo -n "secure-password" | \
  gcloud secrets create postgres-password \
    --data-file=- \
    --replication-policy=automatic

# Retrieve in application
gcloud secrets versions access latest \
  --secret=postgres-password
```

## Network Security

### TLS/SSL Configuration

**Backend TLS** (via reverse proxy):

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.rag-modulo.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Let's Encrypt with Certbot**:

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d api.rag-modulo.example.com

# Auto-renewal (crontab)
0 0 * * * certbot renew --quiet
```

### Kubernetes Network Policies

**Deny All by Default**:

```yaml
# network-policy-deny-all.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
  namespace: rag-modulo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

**Allow Backend → Database**:

```yaml
# network-policy-backend-postgres.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-to-postgres
  namespace: rag-modulo
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 5432
```

**Allow Backend → Milvus**:

```yaml
# network-policy-backend-milvus.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-to-milvus
  namespace: rag-modulo
spec:
  podSelector:
    matchLabels:
      app: milvus
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 19530
```

**Allow Ingress → Backend**:

```yaml
# network-policy-ingress-backend.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ingress-to-backend
  namespace: rag-modulo
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
```

### Firewall Rules

**Docker Host Firewall** (iptables):

```bash
# Allow SSH (change 22 to your SSH port)
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Allow backend API (only from trusted IPs)
iptables -A INPUT -p tcp --dport 8000 -s TRUSTED_IP -j ACCEPT

# Block all other incoming
iptables -A INPUT -j DROP

# Save rules
iptables-save > /etc/iptables/rules.v4
```

**Cloud Provider Firewalls**:

```bash
# AWS Security Group
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# GCP Firewall Rule
gcloud compute firewall-rules create allow-https \
  --allow tcp:443 \
  --source-ranges 0.0.0.0/0

# Azure Network Security Group
az network nsg rule create \
  --resource-group rag-modulo-rg \
  --nsg-name rag-modulo-nsg \
  --name allow-https \
  --priority 100 \
  --destination-port-ranges 443 \
  --access Allow \
  --protocol Tcp
```

## Authentication & Authorization

### Production Security Validation

**File**: `./backend/main.py`

```python
def validate_production_security() -> None:
    """Validate security configuration to prevent dangerous misconfigurations."""
    settings = get_settings()
    environment = os.getenv("ENVIRONMENT", "development").lower()

    # CRITICAL: Prevent SKIP_AUTH in production
    if environment == "production" and settings.skip_auth:
        error_msg = (
            "🚨 SECURITY ERROR: SKIP_AUTH=true is not allowed in production. "
            "Set SKIP_AUTH=false or remove from production .env"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Log warning if SKIP_AUTH enabled in any environment
    if settings.skip_auth:
        logger.warning("⚠️  SKIP_AUTH is enabled - authentication is bypassed!")
```

**Required Configuration**:

```bash
# .env (production)
ENVIRONMENT=production
SKIP_AUTH=false  # NEVER set to true in production!
JWT_SECRET_KEY=your-secure-jwt-secret-min-32-chars

# Application will FAIL TO START if SKIP_AUTH=true in production
```

### JWT Authentication

**JWT Configuration**:

```bash
# .env
JWT_SECRET_KEY=your-secure-jwt-secret-min-32-chars-random-string
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440  # 24 hours
```

**Token Generation** (`backend/auth/`):

```python
import jwt
from datetime import datetime, timedelta

def create_access_token(user_id: str, expires_delta: timedelta = None):
    to_encode = {"sub": user_id, "type": "access"}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt
```

### OIDC Integration

**IBM W3ID Configuration**:

```bash
# .env
OIDC_DISCOVERY_ENDPOINT=https://w3id.sso.ibm.com/auth/sps/samlidp2/saml20
OIDC_AUTH_URL=https://w3id.sso.ibm.com/pkmsoidc/authorize
OIDC_TOKEN_URL=https://w3id.sso.ibm.com/pkmsoidc/token
OIDC_REDIRECT_URI=http://localhost:3000/auth/callback
IBM_CLIENT_ID=your-client-id
IBM_CLIENT_SECRET=your-client-secret
```

**OIDC Flow** (`backend/auth/oidc.py`):

```python
# 1. Redirect to IBM W3ID
authorization_url = f"{OIDC_AUTH_URL}?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}"

# 2. Exchange code for token
token_response = requests.post(
    OIDC_TOKEN_URL,
    data={
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
)

# 3. Validate token and extract user info
id_token = token_response.json()["id_token"]
user_info = jwt.decode(id_token, options={"verify_signature": False})
```

## API Security

### CORS Configuration

```python
# backend/main.py
from core.loggingcors_middleware import LoggingCORSMiddleware

app.add_middleware(
    LoggingCORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://rag-modulo.example.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limiting (Future)

```python
# Future: backend/core/rate_limiting.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/search")
@limiter.limit("10/minute")  # 10 requests per minute
async def search(request: Request, search_input: SearchInput):
    # ... search logic ...
    pass
```

### Request Validation

```python
# All endpoints use Pydantic schemas for validation
from pydantic import BaseModel, Field, UUID4

class SearchInput(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    collection_id: UUID4
    user_id: UUID4
    config_metadata: dict[str, Any] | None = None

    # Automatic validation:
    # - question: 1-1000 chars
    # - collection_id: valid UUID4
    # - user_id: valid UUID4
```

## Data Protection

### Data Encryption

**At Rest**:

```bash
# PostgreSQL: Enable transparent data encryption
# AWS RDS: Enable encryption at creation
# Azure Database: Enable encryption at creation
# Self-hosted: Use encrypted volumes (LUKS)

# Encrypt volume with LUKS
cryptsetup luksFormat /dev/sdb
cryptsetup luksOpen /dev/sdb postgres_data
mkfs.ext4 /dev/mapper/postgres_data
```

**In Transit**:

```bash
# PostgreSQL with SSL
COLLECTIONDB_SSL_MODE=require
COLLECTIONDB_SSL_CA=/path/to/ca-cert.pem

# Milvus with TLS (if supported)
MILVUS_TLS_ENABLED=true
MILVUS_TLS_CERT=/path/to/cert.pem
```

### Database Access Control

**PostgreSQL User Permissions**:

```sql
-- Create application user with minimal permissions
CREATE USER rag_app WITH PASSWORD 'secure-password';

-- Grant only necessary permissions
GRANT CONNECT ON DATABASE rag_modulo_db TO rag_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rag_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO rag_app;

-- Revoke superuser access
REVOKE ALL ON DATABASE postgres FROM rag_app;
```

### Data Retention

```sql
-- Archive old conversations (GDPR compliance)
CREATE TABLE conversations_archive AS
SELECT * FROM conversations
WHERE created_at < NOW() - INTERVAL '90 days';

DELETE FROM conversations
WHERE created_at < NOW() - INTERVAL '90 days';

-- Schedule with pg_cron
SELECT cron.schedule('archive-old-conversations', '0 2 * * 0', $$
    INSERT INTO conversations_archive
    SELECT * FROM conversations
    WHERE created_at < NOW() - INTERVAL '90 days';
    DELETE FROM conversations
    WHERE created_at < NOW() - INTERVAL '90 days';
$$);
```

## Security Scanning

### Continuous Security Scanning

**Weekly Security Audit** (`.github/workflows/06-weekly-security-audit.yml`):

```yaml
name: Weekly Security Audit
on:
  schedule:
    - cron: '0 2 * * 1'  # Monday 2:00 AM UTC
  workflow_dispatch:

jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
      - name: Full Trivy scan with SBOM
        run: trivy image --format json --output trivy-sbom.json $IMAGE

      - name: Deep Gitleaks scan
        run: gitleaks detect --source . --verbose --report-format json

      - name: Safety check (dependencies)
        run: poetry run safety check --full-report
```

### Manual Security Audits

```bash
# Full security check
make security-check

# Includes:
# - Bandit (Python security linter)
# - Safety (dependency vulnerability scanner)
# - Gitleaks (secret scanning)
# - Trivy (container scanning)
```

## Compliance & Auditing

### Audit Logging

```python
# Enhanced logging with audit trail
from core.enhanced_logging import get_logger
from core.logging_context import log_operation

logger = get_logger("rag.audit")

with log_operation(logger, "document_access", "document", doc_id, user_id=user_id):
    logger.info(
        "Document accessed",
        extra={
            "action": "read",
            "document_id": doc_id,
            "user_id": user_id,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
        }
    )
```

### Compliance Checklist

**GDPR Compliance**:
- [ ] Data encryption at rest and in transit
- [ ] User consent for data collection
- [ ] Right to access (user can export their data)
- [ ] Right to erasure (user can delete their data)
- [ ] Data retention policies (auto-delete after 90 days)
- [ ] Audit logging of data access

**SOC 2 Compliance**:
- [ ] Access controls (RBAC)
- [ ] Audit logging
- [ ] Encryption
- [ ] Vulnerability scanning
- [ ] Incident response plan

**HIPAA Compliance** (if handling health data):
- [ ] End-to-end encryption
- [ ] Access controls and authentication
- [ ] Audit trails
- [ ] Data backup and disaster recovery
- [ ] Business Associate Agreement (BAA)

## Related Documentation

- [Cloud Deployment](cloud.md) - Production deployment guide
- [Secret Management](../development/secret-management.md) - Comprehensive secret handling guide
- [Troubleshooting: Authentication](../troubleshooting/authentication.md) - Auth debugging
- [Security Hardening](security-hardening.md) - Advanced security configurations
