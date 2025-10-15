# Security Hardening

This guide covers security hardening strategies for RAG Modulo deployment on IBM Cloud, ensuring comprehensive protection of data, applications, and infrastructure.

## Overview

The security hardening strategy provides:

- **Defense in Depth**: Multiple layers of security controls
- **Zero Trust Architecture**: Never trust, always verify
- **Compliance**: Meet regulatory and industry standards
- **Monitoring**: Continuous security monitoring and alerting
- **Incident Response**: Rapid response to security incidents

## Security Architecture

```mermaid
graph TB
    subgraph "External Threats"
        ATTACK[Attackers]
        MALWARE[Malware]
        BOT[Botnets]
    end
    
    subgraph "Security Layers"
        WAF[Web Application Firewall]
        DDoS[DDoS Protection]
        SSL[SSL/TLS Termination]
        IAM[Identity & Access Management]
        SECRETS[Secrets Management]
        ENCRYPT[Encryption]
        MONITOR[Security Monitoring]
    end
    
    subgraph "Applications"
        FE[Frontend App]
        BE[Backend App]
    end
    
    subgraph "Data Layer"
        PG[PostgreSQL]
        OS[Object Storage]
        ZL[Zilliz Cloud]
        ES[Event Streams]
    end
    
    subgraph "Network Security"
        VPC[VPC]
        NSG[Network Security Groups]
        NLB[Network Load Balancer]
        VPN[VPN Gateway]
    end
    
    ATTACK --> WAF
    MALWARE --> DDoS
    BOT --> SSL
    
    WAF --> IAM
    DDoS --> SECRETS
    SSL --> ENCRYPT
    
    IAM --> FE
    SECRETS --> BE
    ENCRYPT --> MONITOR
    
    FE --> VPC
    BE --> NSG
    VPC --> NLB
    NSG --> VPN
    
    NLB --> PG
    VPN --> OS
    PG --> ZL
    OS --> ES
```

## Network Security

### 1. VPC Configuration

#### VPC Setup

```hcl
# VPC configuration
resource "ibm_is_vpc" "rag_modulo_vpc" {
  name           = "${var.project_name}-vpc"
  resource_group = var.resource_group_id
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "security:high"
  ]
}

# Public gateway for outbound internet access
resource "ibm_is_public_gateway" "rag_modulo_pgw" {
  name           = "${var.project_name}-pgw"
  vpc            = ibm_is_vpc.rag_modulo_vpc.id
  zone           = "${var.region}-1"
  resource_group = var.resource_group_id
}

# Subnet for applications
resource "ibm_is_subnet" "rag_modulo_subnet" {
  name            = "${var.project_name}-subnet"
  vpc             = ibm_is_vpc.rag_modulo_vpc.id
  zone            = "${var.region}-1"
  ipv4_cidr_block = "10.240.0.0/24"
  public_gateway  = ibm_is_public_gateway.rag_modulo_pgw.id
  resource_group  = var.resource_group_id
}
```

#### Network Security Groups

```hcl
# Network Security Group for applications
resource "ibm_is_security_group" "rag_modulo_sg" {
  name           = "${var.project_name}-sg"
  vpc            = ibm_is_vpc.rag_modulo_vpc.id
  resource_group = var.resource_group_id
}

# Allow HTTPS inbound
resource "ibm_is_security_group_rule" "https_inbound" {
  group     = ibm_is_security_group.rag_modulo_sg.id
  direction = "inbound"
  remote    = "0.0.0.0/0"
  tcp {
    port_min = 443
    port_max = 443
  }
}

# Allow HTTP inbound (redirected to HTTPS)
resource "ibm_is_security_group_rule" "http_inbound" {
  group     = ibm_is_security_group.rag_modulo_sg.id
  direction = "inbound"
  remote    = "0.0.0.0/0"
  tcp {
    port_min = 80
    port_max = 80
  }
}

# Allow outbound HTTPS
resource "ibm_is_security_group_rule" "https_outbound" {
  group     = ibm_is_security_group.rag_modulo_sg.id
  direction = "outbound"
  remote    = "0.0.0.0/0"
  tcp {
    port_min = 443
    port_max = 443
  }
}

# Allow outbound PostgreSQL
resource "ibm_is_security_group_rule" "postgresql_outbound" {
  group     = ibm_is_security_group.rag_modulo_sg.id
  direction = "outbound"
  remote    = "0.0.0.0/0"
  tcp {
    port_min = 5432
    port_max = 5432
  }
}
```

### 2. Load Balancer Security

#### Application Load Balancer

```hcl
# Application Load Balancer
resource "ibm_is_lb" "rag_modulo_lb" {
  name           = "${var.project_name}-lb"
  type           = "public"
  subnets        = [ibm_is_subnet.rag_modulo_subnet.id]
  resource_group = var.resource_group_id
}

# HTTPS listener
resource "ibm_is_lb_listener" "rag_modulo_https" {
  lb           = ibm_is_lb.rag_modulo_lb.id
  port         = 443
  protocol     = "https"
  certificate  = ibm_is_lb_certificate.rag_modulo_cert.crn
  default_pool = ibm_is_lb_pool.rag_modulo_pool.id
}

# SSL certificate
resource "ibm_is_lb_certificate" "rag_modulo_cert" {
  name        = "${var.project_name}-cert"
  lb          = ibm_is_lb.rag_modulo_lb.id
  certificate = var.ssl_certificate
  private_key = var.ssl_private_key
}

# Load balancer pool
resource "ibm_is_lb_pool" "rag_modulo_pool" {
  name           = "${var.project_name}-pool"
  lb             = ibm_is_lb.rag_modulo_lb.id
  algorithm      = "round_robin"
  protocol       = "https"
  health_delay   = 5
  health_retries = 2
  health_timeout = 2
  health_type    = "https"
  health_monitor = "https://backend-app.example.com/health"
}
```

## Identity and Access Management

### 1. IAM Configuration

#### Service IDs

```hcl
# Service ID for applications
resource "ibm_iam_service_id" "rag_modulo_service_id" {
  name        = "${var.project_name}-service-id"
  description = "Service ID for RAG Modulo applications"
}

# Service ID for Terraform
resource "ibm_iam_service_id" "terraform_service_id" {
  name        = "${var.project_name}-terraform-service-id"
  description = "Service ID for Terraform operations"
}
```

#### IAM Policies

```hcl
# Policy for Code Engine access
resource "ibm_iam_service_policy" "code_engine_policy" {
  iam_service_id = ibm_iam_service_id.rag_modulo_service_id.id
  roles          = ["Code Engine Developer", "Code Engine Administrator"]
  
  resources {
    service = "codeengine"
  }
}

# Policy for database access
resource "ibm_iam_service_policy" "database_policy" {
  iam_service_id = ibm_iam_service_id.rag_modulo_service_id.id
  roles          = ["Database Administrator"]
  
  resources {
    service = "databases-for-postgresql"
    resource_group_id = var.resource_group_id
  }
}

# Policy for object storage access
resource "ibm_iam_service_policy" "object_storage_policy" {
  iam_service_id = ibm_iam_service_id.rag_modulo_service_id.id
  roles          = ["Object Storage Manager"]
  
  resources {
    service = "cloud-object-storage"
    resource_group_id = var.resource_group_id
  }
}
```

### 2. API Key Management

#### API Key Rotation

```bash
#!/bin/bash
# API key rotation script

set -e

# Configuration
OLD_API_KEY="$1"
NEW_API_KEY="$2"
SERVICE_ID="$3"

if [ -z "$OLD_API_KEY" ] || [ -z "$NEW_API_KEY" ] || [ -z "$SERVICE_ID" ]; then
    echo "Usage: $0 <old_api_key> <new_api_key> <service_id>"
    exit 1
fi

# Create new API key
echo "Creating new API key..."
ibmcloud iam service-api-key-create "rag-modulo-api-key-$(date +%Y%m%d)" "$SERVICE_ID" --description "RAG Modulo API key created on $(date)"

# Update applications with new API key
echo "Updating applications with new API key..."
ibmcloud ce app update rag-modulo-backend --env "IBMCLOUD_API_KEY=$NEW_API_KEY"
ibmcloud ce app update rag-modulo-frontend --env "IBMCLOUD_API_KEY=$NEW_API_KEY"

# Verify applications are working
echo "Verifying applications..."
sleep 30
curl -f "https://backend-app.example.com/health" || exit 1
curl -f "https://frontend-app.example.com/health" || exit 1

# Delete old API key
echo "Deleting old API key..."
ibmcloud iam service-api-key-delete "$OLD_API_KEY" "$SERVICE_ID" --force

echo "API key rotation completed successfully"
```

## Secrets Management

### 1. IBM Cloud Secrets Manager

#### Secrets Configuration

```hcl
# Secrets Manager instance
resource "ibm_resource_instance" "secrets_manager" {
  name              = "${var.project_name}-secrets-manager"
  service           = "secrets-manager"
  plan              = "standard"
  location          = var.region
  resource_group_id = var.resource_group_id
}

# Database password secret
resource "ibm_sm_secret" "database_password" {
  instance_id   = ibm_resource_instance.secrets_manager.guid
  secret_type   = "arbitrary"
  name          = "rag-modulo-database-password"
  description   = "Database password for RAG Modulo"
  secret_data   = jsonencode({
    password = var.postgresql_admin_password
  })
}

# API keys secret
resource "ibm_sm_secret" "api_keys" {
  instance_id   = ibm_resource_instance.secrets_manager.guid
  secret_type   = "arbitrary"
  name          = "rag-modulo-api-keys"
  description   = "API keys for RAG Modulo"
  secret_data   = jsonencode({
    ibmcloud_api_key = var.ibmcloud_api_key
    zilliz_api_key   = var.zilliz_api_key
    event_streams_api_key = var.event_streams_api_key
  })
}
```

#### Secrets Integration

```yaml
# Ansible playbook for secrets integration
---
- name: Configure secrets management
  hosts: localhost
  gather_facts: false
  vars:
    secrets_manager_instance_id: "{{ secrets_manager_instance_id }}"
  
  tasks:
    - name: Get database password from Secrets Manager
      ansible.builtin.shell: |
        ibmcloud secrets-manager secret get "rag-modulo-database-password" \
          --instance-id "$secrets_manager_instance_id" \
          --output json | jq -r '.secret_data.password'
      register: database_password
      no_log: true
    
    - name: Get API keys from Secrets Manager
      ansible.builtin.shell: |
        ibmcloud secrets-manager secret get "rag-modulo-api-keys" \
          --instance-id "$secrets_manager_instance_id" \
          --output json | jq -r '.secret_data'
      register: api_keys
      no_log: true
    
    - name: Update application with secrets
      ansible.builtin.shell: |
        ibmcloud ce app update rag-modulo-backend \
          --env "DATABASE_PASSWORD=$database_password" \
          --env "ZILLIZ_API_KEY=$(echo '$api_keys' | jq -r '.zilliz_api_key')" \
          --env "EVENT_STREAMS_API_KEY=$(echo '$api_keys' | jq -r '.event_streams_api_key')"
      environment:
        IBMCLOUD_API_KEY: "{{ ibmcloud_api_key }}"
```

### 2. Environment Variable Security

#### Secure Environment Configuration

```yaml
# Secure environment variables
secure_env_vars:
  # Database configuration
  DATABASE_URL: "postgresql://username:${DATABASE_PASSWORD}@host:port/database?sslmode=require"
  DATABASE_PASSWORD: "{{ vault_database_password }}"
  
  # API keys
  IBMCLOUD_API_KEY: "{{ vault_ibmcloud_api_key }}"
  ZILLIZ_API_KEY: "{{ vault_zilliz_api_key }}"
  EVENT_STREAMS_API_KEY: "{{ vault_event_streams_api_key }}"
  
  # Security settings
  JWT_SECRET: "{{ vault_jwt_secret }}"
  ENCRYPTION_KEY: "{{ vault_encryption_key }}"
  
  # Production safeguards
  SKIP_AUTH: "false"
  DEBUG: "false"
  LOG_LEVEL: "INFO"
```

## Data Encryption

### 1. Encryption at Rest

#### Database Encryption

```yaml
# PostgreSQL encryption configuration
postgresql_encryption:
  enabled: true
  encryption_key: "{{ vault_database_encryption_key }}"
  key_rotation: "90d"
  
  # Encryption settings
  settings:
    ssl_mode: "require"
    ssl_cert: "{{ vault_ssl_cert }}"
    ssl_key: "{{ vault_ssl_key }}"
    ssl_ca: "{{ vault_ssl_ca }}"
```

#### Object Storage Encryption

```yaml
# Object Storage encryption configuration
object_storage_encryption:
  enabled: true
  encryption_type: "AES256"
  key_management: "ibm-cloud-key-protect"
  
  # Bucket encryption
  bucket_encryption:
    - bucket: "rag-modulo-app-data"
      encryption: "AES256"
      key_id: "{{ vault_object_storage_key_id }}"
```

### 2. Encryption in Transit

#### TLS Configuration

```yaml
# TLS configuration
tls_config:
  enabled: true
  version: "TLS 1.2"
  ciphers: "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256"
  
  # Certificate management
  certificate:
    provider: "letsencrypt"
    auto_renewal: true
    renewal_threshold: "30d"
  
  # HSTS configuration
  hsts:
    enabled: true
    max_age: "31536000"
    include_subdomains: true
    preload: true
```

#### Application TLS

```python
# Application TLS configuration
import ssl
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

# Force HTTPS redirect
app.add_middleware(HTTPSRedirectMiddleware)

# TLS configuration
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain("cert.pem", "key.pem")
ssl_context.set_ciphers("ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256")
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
```

## Application Security

### 1. Input Validation

#### Request Validation

```python
# Input validation
from pydantic import BaseModel, validator
import re

class SearchRequest(BaseModel):
    query: str
    collection_id: str
    limit: int = 10
    
    @validator('query')
    def validate_query(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Query cannot be empty')
        if len(v) > 1000:
            raise ValueError('Query too long')
        # Check for SQL injection patterns
        if re.search(r'[;\'"]', v):
            raise ValueError('Invalid characters in query')
        return v.strip()
    
    @validator('collection_id')
    def validate_collection_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9-_]+$', v):
            raise ValueError('Invalid collection ID format')
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Limit must be between 1 and 100')
        return v
```

#### SQL Injection Prevention

```python
# SQL injection prevention
import psycopg2
from psycopg2 import sql

def safe_query(cursor, query_template, params):
    """Execute query with parameterized statements"""
    try:
        cursor.execute(query_template, params)
        return cursor.fetchall()
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

# Example usage
def search_documents(collection_id: str, query: str, limit: int):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Use parameterized query
            query_template = """
                SELECT id, title, content, created_at
                FROM documents
                WHERE collection_id = %s
                AND content ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            params = (collection_id, f"%{query}%", limit)
            return safe_query(cursor, query_template, params)
```

### 2. Authentication and Authorization

#### JWT Authentication

```python
# JWT authentication
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

class JWTAuth:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_token(self, user_id: str, expires_delta: timedelta = None):
        """Create JWT token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        payload = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    jwt_auth = JWTAuth(os.getenv("JWT_SECRET"))
    payload = jwt_auth.verify_token(credentials.credentials)
    return payload["user_id"]
```

#### Role-Based Access Control

```python
# Role-based access control
from enum import Enum
from functools import wraps

class Role(Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"

def require_role(required_role: Role):
    """Decorator to require specific role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("current_user")
            user_role = get_user_role(user_id)
            
            if not has_permission(user_role, required_role):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def has_permission(user_role: Role, required_role: Role) -> bool:
    """Check if user has required permission"""
    role_hierarchy = {
        Role.ADMIN: [Role.ADMIN, Role.USER, Role.READONLY],
        Role.USER: [Role.USER, Role.READONLY],
        Role.READONLY: [Role.READONLY]
    }
    
    return required_role in role_hierarchy.get(user_role, [])

# Usage example
@app.post("/api/collections")
@require_role(Role.ADMIN)
async def create_collection(
    collection: CollectionCreate,
    current_user: str = Depends(get_current_user)
):
    # Only admins can create collections
    pass
```

### 3. Rate Limiting

#### API Rate Limiting

```python
# Rate limiting
from fastapi import FastAPI, Request
from fastapi.middleware.base import BaseHTTPMiddleware
import time
from collections import defaultdict

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        
        # Clean old requests
        self.clients[client_ip] = [
            req_time for req_time in self.clients[client_ip]
            if now - req_time < self.period
        ]
        
        # Check rate limit
        if len(self.clients[client_ip]) >= self.calls:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
        
        # Add current request
        self.clients[client_ip].append(now)
        
        response = await call_next(request)
        return response

# Apply rate limiting
app.add_middleware(RateLimitMiddleware, calls=100, period=60)
```

## Security Monitoring

### 1. Security Event Monitoring

#### Security Event Collection

```python
# Security event collection
import logging
from datetime import datetime
from typing import Dict, Any

class SecurityEventLogger:
    def __init__(self):
        self.logger = logging.getLogger("security")
        self.logger.setLevel(logging.INFO)
        
        # Create security event handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_auth_failure(self, user_id: str, ip_address: str, reason: str):
        """Log authentication failure"""
        self.logger.warning(
            f"Authentication failure - User: {user_id}, IP: {ip_address}, Reason: {reason}"
        )
    
    def log_suspicious_activity(self, activity: str, details: Dict[str, Any]):
        """Log suspicious activity"""
        self.logger.warning(
            f"Suspicious activity - {activity}: {details}"
        )
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log general security event"""
        self.logger.info(
            f"Security event - {event_type}: {details}"
        )

# Global security logger
security_logger = SecurityEventLogger()
```

#### Security Metrics

```python
# Security metrics
from prometheus_client import Counter, Histogram, Gauge

# Security event counters
auth_failures = Counter('auth_failures_total', 'Total authentication failures', ['user_id', 'reason'])
suspicious_activities = Counter('suspicious_activities_total', 'Total suspicious activities', ['activity_type'])
security_events = Counter('security_events_total', 'Total security events', ['event_type'])

# Security response time
security_response_time = Histogram('security_response_time_seconds', 'Security response time')

# Active security threats
active_threats = Gauge('active_threats', 'Number of active security threats')

# Example usage
def log_auth_failure(user_id: str, reason: str):
    auth_failures.labels(user_id=user_id, reason=reason).inc()
    security_logger.log_auth_failure(user_id, get_client_ip(), reason)

def log_suspicious_activity(activity: str, details: Dict[str, Any]):
    suspicious_activities.labels(activity_type=activity).inc()
    security_logger.log_suspicious_activity(activity, details)
```

### 2. Security Alerting

#### Alert Rules

```yaml
# Security alert rules
security_alerts:
  - name: "high_auth_failures"
    condition: "rate(auth_failures_total[5m]) > 10"
    duration: "2m"
    severity: "critical"
    description: "High rate of authentication failures"
  
  - name: "suspicious_activity_detected"
    condition: "rate(suspicious_activities_total[5m]) > 5"
    duration: "1m"
    severity: "warning"
    description: "Suspicious activity detected"
  
  - name: "security_event_spike"
    condition: "rate(security_events_total[5m]) > 20"
    duration: "5m"
    severity: "warning"
    description: "Unusual spike in security events"
```

#### Incident Response

```python
# Incident response automation
import asyncio
from datetime import datetime
from typing import List, Dict

class SecurityIncidentResponse:
    def __init__(self):
        self.active_incidents = {}
        self.response_team = ["devops@company.com", "security@company.com"]
    
    async def handle_security_alert(self, alert: Dict[str, Any]):
        """Handle security alert"""
        incident_id = f"SEC-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Create incident
        incident = {
            "id": incident_id,
            "type": alert["type"],
            "severity": alert["severity"],
            "timestamp": datetime.now(),
            "status": "open",
            "details": alert["details"]
        }
        
        self.active_incidents[incident_id] = incident
        
        # Notify response team
        await self.notify_response_team(incident)
        
        # Take automated actions
        await self.take_automated_actions(incident)
        
        return incident_id
    
    async def notify_response_team(self, incident: Dict[str, Any]):
        """Notify security response team"""
        # Send email notification
        await self.send_email_notification(incident)
        
        # Send Slack notification
        await self.send_slack_notification(incident)
    
    async def take_automated_actions(self, incident: Dict[str, Any]):
        """Take automated security actions"""
        if incident["severity"] == "critical":
            # Block suspicious IP
            await self.block_suspicious_ip(incident["details"]["ip_address"])
            
            # Increase monitoring
            await self.increase_monitoring(incident["details"]["user_id"])
            
            # Generate security report
            await self.generate_security_report(incident)

# Global incident response
incident_response = SecurityIncidentResponse()
```

## Compliance and Auditing

### 1. Audit Logging

#### Audit Event Collection

```python
# Audit logging
import json
from datetime import datetime
from typing import Dict, Any

class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # Create audit handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_user_action(self, user_id: str, action: str, resource: str, details: Dict[str, Any]):
        """Log user action"""
        audit_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "user_action",
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details,
            "ip_address": get_client_ip(),
            "user_agent": get_user_agent()
        }
        
        self.logger.info(json.dumps(audit_event))
    
    def log_system_event(self, event_type: str, details: Dict[str, Any]):
        """Log system event"""
        audit_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "system_event",
            "system_event_type": event_type,
            "details": details
        }
        
        self.logger.info(json.dumps(audit_event))
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security event"""
        audit_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "security_event",
            "security_event_type": event_type,
            "details": details
        }
        
        self.logger.info(json.dumps(audit_event))

# Global audit logger
audit_logger = AuditLogger()
```

#### Compliance Reporting

```python
# Compliance reporting
from datetime import datetime, timedelta
from typing import List, Dict

class ComplianceReporter:
    def __init__(self):
        self.audit_logger = AuditLogger()
    
    def generate_compliance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate compliance report"""
        report = {
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "user_actions": self.get_user_actions(start_date, end_date),
            "system_events": self.get_system_events(start_date, end_date),
            "security_events": self.get_security_events(start_date, end_date),
            "compliance_summary": self.get_compliance_summary(start_date, end_date)
        }
        
        return report
    
    def get_user_actions(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get user actions for compliance report"""
        # Query audit logs for user actions
        # This would typically query a database or log aggregation system
        pass
    
    def get_system_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get system events for compliance report"""
        # Query audit logs for system events
        pass
    
    def get_security_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get security events for compliance report"""
        # Query audit logs for security events
        pass
    
    def get_compliance_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get compliance summary"""
        return {
            "total_events": 0,
            "security_incidents": 0,
            "compliance_score": 100,
            "recommendations": []
        }

# Global compliance reporter
compliance_reporter = ComplianceReporter()
```

### 2. Data Privacy

#### Data Classification

```python
# Data classification
from enum import Enum
from typing import Dict, Any

class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class DataClassifier:
    def __init__(self):
        self.classification_rules = {
            "email": DataClassification.CONFIDENTIAL,
            "phone": DataClassification.CONFIDENTIAL,
            "ssn": DataClassification.RESTRICTED,
            "credit_card": DataClassification.RESTRICTED,
            "api_key": DataClassification.RESTRICTED,
            "password": DataClassification.RESTRICTED
        }
    
    def classify_data(self, data: Dict[str, Any]) -> Dict[str, DataClassification]:
        """Classify data based on content"""
        classifications = {}
        
        for key, value in data.items():
            classification = DataClassification.INTERNAL  # Default
            
            for pattern, data_class in self.classification_rules.items():
                if pattern.lower() in key.lower():
                    classification = data_class
                    break
            
            classifications[key] = classification
        
        return classifications
    
    def apply_data_protection(self, data: Dict[str, Any], classifications: Dict[str, DataClassification]) -> Dict[str, Any]:
        """Apply data protection based on classification"""
        protected_data = {}
        
        for key, value in data.items():
            classification = classifications.get(key, DataClassification.INTERNAL)
            
            if classification == DataClassification.RESTRICTED:
                # Mask or remove restricted data
                protected_data[key] = "***REDACTED***"
            elif classification == DataClassification.CONFIDENTIAL:
                # Partially mask confidential data
                if isinstance(value, str) and len(value) > 4:
                    protected_data[key] = value[:2] + "***" + value[-2:]
                else:
                    protected_data[key] = "***MASKED***"
            else:
                protected_data[key] = value
        
        return protected_data

# Global data classifier
data_classifier = DataClassifier()
```

## Security Testing

### 1. Vulnerability Scanning

#### Container Security Scanning

```yaml
# Container security scanning
container_security_scanning:
  enabled: true
  tools:
    - name: "trivy"
      image: "aquasec/trivy"
      command: "trivy image --exit-code 1 --severity HIGH,CRITICAL"
      targets:
        - "rag-modulo-backend:latest"
        - "rag-modulo-frontend:latest"
    
    - name: "dockle"
      image: "goodwithtech/dockle"
      command: "dockle --exit-code 1"
      targets:
        - "rag-modulo-backend:latest"
        - "rag-modulo-frontend:latest"
  
  schedule: "0 2 * * *"  # Daily at 2 AM
  reporting:
    - format: "json"
      output: "/reports/security-scan.json"
    - format: "html"
      output: "/reports/security-scan.html"
```

#### Application Security Testing

```yaml
# Application security testing
application_security_testing:
  enabled: true
  tools:
    - name: "owasp-zap"
      image: "owasp/zap2docker-stable"
      command: "zap-baseline.py -t https://backend-app.example.com"
    
    - name: "nikto"
      image: "sullo/nikto"
      command: "nikto -h https://frontend-app.example.com"
  
  schedule: "0 3 * * *"  # Daily at 3 AM
  reporting:
    - format: "json"
      output: "/reports/owasp-scan.json"
    - format: "html"
      output: "/reports/owasp-scan.html"
```

### 2. Penetration Testing

#### Penetration Testing Script

```bash
#!/bin/bash
# Penetration testing script

set -e

# Configuration
TARGET_URL="$1"
REPORT_DIR="/reports/penetration-test"
DATE=$(date +%Y%m%d_%H%M%S)

if [ -z "$TARGET_URL" ]; then
    echo "Usage: $0 <target_url>"
    exit 1
fi

# Create report directory
mkdir -p "$REPORT_DIR"

# Run penetration tests
echo "Running penetration tests on $TARGET_URL..."

# SQL injection testing
echo "Testing for SQL injection..."
sqlmap -u "$TARGET_URL/api/search?query=test" --batch --output-dir="$REPORT_DIR/sqlmap"

# XSS testing
echo "Testing for XSS vulnerabilities..."
xsser -u "$TARGET_URL" --output="$REPORT_DIR/xsser.txt"

# Directory traversal testing
echo "Testing for directory traversal..."
dirb "$TARGET_URL" "$REPORT_DIR/dirb.txt"

# SSL/TLS testing
echo "Testing SSL/TLS configuration..."
testssl.sh "$TARGET_URL" > "$REPORT_DIR/testssl.txt"

# Generate summary report
echo "Generating penetration test summary..."
cat > "$REPORT_DIR/summary.txt" << EOF
Penetration Test Summary
=======================
Target: $TARGET_URL
Date: $(date)
Tester: Automated Security Testing

Tests Performed:
- SQL Injection (sqlmap)
- XSS (xsser)
- Directory Traversal (dirb)
- SSL/TLS (testssl.sh)

Reports:
- SQL Injection: $REPORT_DIR/sqlmap/
- XSS: $REPORT_DIR/xsser.txt
- Directory Traversal: $REPORT_DIR/dirb.txt
- SSL/TLS: $REPORT_DIR/testssl.txt
EOF

echo "Penetration testing completed. Reports saved to $REPORT_DIR"
```

## Security Best Practices

### 1. Development Security

- **Secure Coding**: Follow secure coding practices
- **Code Review**: Security-focused code reviews
- **Dependency Management**: Regular dependency updates
- **Secret Management**: Never hardcode secrets

### 2. Deployment Security

- **Least Privilege**: Use minimal required permissions
- **Network Segmentation**: Isolate different components
- **Regular Updates**: Keep all components updated
- **Monitoring**: Continuous security monitoring

### 3. Operational Security

- **Incident Response**: Clear incident response procedures
- **Regular Audits**: Periodic security audits
- **Training**: Regular security training for team
- **Documentation**: Maintain security documentation

## Related Documentation

- [Terraform + Ansible Architecture](terraform-ansible-architecture.md)
- [IBM Cloud Code Engine Deployment](ibm-cloud-code-engine.md)
- [Managed Services Strategy](managed-services.md)
- [Monitoring and Observability](monitoring-observability.md)
- [Backup and Disaster Recovery](backup-disaster-recovery.md)
