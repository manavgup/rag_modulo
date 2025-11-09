# Security Architecture

This document describes the security measures, authentication mechanisms, and best practices implemented in RAG Modulo.

## Security Overview

RAG Modulo implements a **defense-in-depth security strategy** with multiple layers of protection:

1. **Authentication**: OIDC with IBM Cloud Identity + JWT tokens
2. **Authorization**: Role-based and resource-based access control
3. **Secret Management**: 3-layer defense with scanning and validation
4. **API Security**: Input validation, SQL injection prevention, XSS protection
5. **Network Security**: HTTPS enforcement, CORS configuration
6. **Dependency Security**: Automated vulnerability scanning

## Authentication

### OIDC Authentication

RAG Modulo uses **OpenID Connect (OIDC)** with IBM Cloud Identity as the identity provider.

**Configuration** (`backend/rag_solution/auth/oidc.py`):

```python
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()

# Register IBM Cloud Identity as OIDC provider
oauth.register(
    name="ibm",
    server_metadata_url=settings.oidc_discovery_endpoint,
    client_id=settings.ibm_client_id,
    client_secret=settings.ibm_client_secret,
    client_kwargs={"scope": "openid email profile"},
    # Token validation
    validate_iss=True,
    validate_aud=True,
    validate_exp=True,
    leeway=50000,  # Time leeway for clock skew
)
```

**Environment Variables**:
```bash
OIDC_DISCOVERY_ENDPOINT=https://identity.example.com/.well-known/openid-configuration
IBM_CLIENT_ID=your_client_id
IBM_CLIENT_SECRET=your_client_secret
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### Authentication Flow

#### 1. Initial Login

```python
@router.get("/login")
async def login(request: Request):
    # Redirect to IBM Cloud Identity
    redirect_uri = request.url_for("auth_callback")
    return await oauth.ibm.authorize_redirect(request, redirect_uri)
```

#### 2. Callback Handler

```python
@router.get("/callback")
async def auth_callback(request: Request):
    # Exchange authorization code for tokens
    token = await oauth.ibm.authorize_access_token(request)

    # Validate ID token
    user_info = token.get("userinfo")

    # Extract user details
    user_data = {
        "sub": user_info.get("sub"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
    }

    # Find or create user
    user = await user_service.get_or_create_user(user_data)

    # Generate JWT token
    jwt_token = create_jwt_token(user)

    # Return token to frontend
    return {"access_token": jwt_token, "token_type": "bearer"}
```

#### 3. JWT Token Generation

```python
import jwt
from datetime import datetime, timedelta

def create_jwt_token(user: User) -> str:
    """Generate JWT token for authenticated user"""
    payload = {
        "sub": str(user.id),
        "uuid": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=24),
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return token
```

### Development Mode

For development and testing, RAG Modulo supports **mock authentication**:

```python
# .env configuration
SKIP_AUTH=true
DEVELOPMENT_MODE=true
```

**Mock Token Support**:
```python
def verify_jwt_token(token: str) -> dict[str, Any]:
    # Support mock tokens in development
    if is_mock_token(token):
        return {
            "sub": "test_user_id",
            "uuid": "test_user_id",
            "email": "test@example.com",
            "name": "Test User",
            "role": "user"
        }

    # Real JWT verification for production
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm]
    )

    return payload
```

## Authorization

### Role-Based Access Control (RBAC)

RAG Modulo implements role-based authorization with the following roles:

- **user**: Standard user with access to own resources
- **admin**: Administrative access to all resources
- **service**: Service accounts for system operations

**Role Enforcement**:
```python
def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin role for endpoint access"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    return current_user

@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: UUID4,
    admin: dict = Depends(require_admin)
):
    # Only admins can delete users
    await user_service.delete_user(user_id)
```

### Resource-Based Access Control

Users can only access resources they own or have been granted access to.

**Collection Access Verification**:
```python
def verify_collection_access(
    collection_id: UUID4,
    user_id: UUID4,
    request: Request,
    db: Session = Depends(get_db)
) -> bool:
    """Verify user has access to collection"""
    current_user = get_current_user(request)

    # Verify user is accessing their own resources
    if current_user.get("uuid") != str(user_id):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access other users' resources"
        )

    # Check collection ownership
    user_collection_service = UserCollectionService(db)
    user_collections = user_collection_service.get_user_collections(user_id)

    if not any(uc.id == collection_id for uc in user_collections):
        raise HTTPException(
            status_code=403,
            detail="No access to this collection"
        )

    return True
```

**Security Fix in SearchRouter**:
```python
@router.post("/search", response_model=SearchOutput)
async def search(
    search_input: SearchInput,
    current_user: Annotated[dict, Depends(get_current_user)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchOutput:
    # SECURITY FIX: Always use user_id from JWT token
    # NEVER trust client-provided user_id
    user_id_from_token = current_user.get("uuid")

    if not user_id_from_token:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in authentication token"
        )

    # Override client input with token value
    search_input.user_id = UUID(user_id_from_token)

    result = await search_service.search(search_input)
    return result
```

### Team-Based Access Control

Collections can be shared with teams for collaborative access.

**Team Access Verification**:
```python
async def verify_team_access(
    collection_id: UUID4,
    user_id: UUID4,
    db: Session
) -> bool:
    """Verify user has team access to collection"""
    # Get user's teams
    user_teams = await team_service.get_user_teams(user_id)

    # Get collection's teams
    collection_teams = await collection_service.get_collection_teams(
        collection_id
    )

    # Check for team overlap
    team_ids = {team.id for team in user_teams}
    collection_team_ids = {team.id for team in collection_teams}

    if team_ids.intersection(collection_team_ids):
        return True

    return False
```

## Secret Management

RAG Modulo implements a **3-layer defense-in-depth** approach to prevent secret leaks.

### Layer 1: Pre-Commit Hooks (Local)

**detect-secrets** runs on every commit (< 1 second):

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.4.0
  hooks:
    - id: detect-secrets
      args: ['--baseline', '.secrets.baseline']
      exclude: ^(tests/|docs/|\.secrets\.baseline)
```

**Supported Secret Types**:
- AWS Access Keys
- Azure Storage Keys
- Google Cloud API Keys
- OpenAI API Keys
- Anthropic API Keys
- WatsonX API Keys
- Database Passwords
- JWT Secret Keys
- GitHub/GitLab Tokens
- Private Keys (RSA, SSH)
- High-entropy strings

**Baseline Management**:
```bash
# Update baseline for false positives
detect-secrets scan --baseline .secrets.baseline

# Audit baseline
detect-secrets audit .secrets.baseline

# Commit updated baseline
git add .secrets.baseline
git commit -m "chore: update secrets baseline"
```

### Layer 2: CI Secret Scanning

**Gitleaks + TruffleHog** run on every PR (~45 seconds):

```yaml
# .github/workflows/02-security.yml
- name: Run Gitleaks
  uses: gitleaks/gitleaks-action@v2
  with:
    config: .gitleaks.toml

- name: Run TruffleHog
  uses: trufflesecurity/trufflehog@main
  with:
    path: ./
    base: ${{ github.event.pull_request.base.sha }}
```

**Zero Tolerance Policy**: CI fails immediately on any secret detection.

### Layer 3: Weekly Security Audits

**Deep vulnerability scanning** every Monday at 2:00 AM UTC:

```yaml
# .github/workflows/06-weekly-security-audit.yml
- name: Generate SBOM
  run: poetry export --format requirements.txt

- name: Scan SBOM with Trivy
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'sbom'
    severity: 'CRITICAL,HIGH'
```

### Environment Variable Security

**Never commit secrets to git**. Use environment variables:

```bash
# .env (NEVER commit this file!)
WATSONX_APIKEY=your_secret_key
OPENAI_API_KEY=your_secret_key
JWT_SECRET_KEY=your_secret_key
COLLECTIONDB_PASS=your_db_password
```

**Validation at Startup**:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    watsonx_apikey: str
    openai_api_key: str | None = None
    jwt_secret_key: str

    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator("jwt_secret_key")
    def validate_jwt_secret(cls, v):
        if len(v) < 32:
            raise ValueError("JWT secret must be at least 32 characters")
        return v
```

## API Security

### Input Validation

**Pydantic schemas** enforce strict input validation:

```python
class SearchInput(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    collection_id: UUID4
    user_id: UUID4
    config_metadata: dict[str, Any] | None = None

    # Reject unknown fields
    model_config = ConfigDict(extra="forbid")

    @validator("question")
    def validate_question(cls, v):
        # Prevent SQL injection attempts
        if any(keyword in v.lower() for keyword in ["drop", "delete", "truncate"]):
            raise ValueError("Invalid question")
        return v
```

### SQL Injection Prevention

**SQLAlchemy ORM** provides automatic parameterization:

```python
# SAFE: Parameterized query
collection = (
    self.db.query(Collection)
    .filter(Collection.id == collection_id)
    .first()
)

# UNSAFE: Never do this
# query = f"SELECT * FROM collections WHERE id = '{collection_id}'"
```

### XSS Prevention

**Frontend sanitization** with React and DOMPurify:

```typescript
import DOMPurify from 'dompurify';
import ReactMarkdown from 'react-markdown';

function SafeMarkdown({ content }: { content: string }) {
  // Sanitize HTML before rendering
  const sanitized = DOMPurify.sanitize(content);

  return (
    <ReactMarkdown
      children={sanitized}
      components={{
        // Disable dangerous components
        script: () => null,
        iframe: () => null,
      }}
    />
  );
}
```

### CSRF Protection

**JWT tokens in headers** (not cookies) prevent CSRF attacks:

```typescript
// Frontend API client
const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add JWT token to all requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### Rate Limiting

**Per-user rate limiting** prevents abuse:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/search")
@limiter.limit("10/minute")  # 10 requests per minute
async def search(request: Request, search_input: SearchInput):
    return await search_service.search(search_input)
```

## Network Security

### HTTPS Enforcement

**Production deployment** enforces HTTPS:

```python
# main.py
if not settings.development_mode:
    from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
    app.add_middleware(HTTPSRedirectMiddleware)
```

### CORS Configuration

**Controlled CORS** allows only trusted origins:

```python
from fastapi.middleware.cors import CORSMiddleware

allowed_origins = [
    "http://localhost:3000",  # Development
    "https://rag-modulo.example.com",  # Production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)
```

### Security Headers

**Middleware adds security headers**:

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # XSS protection
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline';"
    )

    return response
```

## Dependency Security

### Automated Vulnerability Scanning

**Multiple scanning tools** ensure dependency security:

#### Bandit (Python Security Linter)

```bash
# Run Bandit security scan
poetry run bandit -r backend/rag_solution/ -ll

# Check for:
# - Hardcoded passwords
# - Unsafe function calls (eval, exec)
# - Insecure cryptography
# - SQL injection vulnerabilities
```

#### Safety (Dependency Vulnerability Scanner)

```bash
# Check dependencies for known vulnerabilities
poetry run safety check

# Scans against CVE database
# Reports: CVE ID, severity, affected versions
```

#### Trivy (Container Security Scanning)

```yaml
# .github/workflows/03-build-secure.yml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ghcr.io/manavgup/rag_modulo/backend:latest
    severity: 'CRITICAL,HIGH'
    exit-code: 1  # Fail on vulnerabilities
```

### Dependency Updates

**Dependabot** automatically creates PRs for security updates:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    reviewers:
      - "security-team"
    labels:
      - "dependencies"
      - "security"
```

## Database Security

### Connection Security

**Encrypted connections** to PostgreSQL:

```python
# Database connection with SSL
DATABASE_URL = (
    f"postgresql://{settings.collectiondb_user}:"
    f"{settings.collectiondb_pass}@"
    f"{settings.collectiondb_host}:"
    f"{settings.collectiondb_port}/"
    f"{settings.collectiondb_name}"
    "?sslmode=require"  # Require SSL/TLS
)
```

### Password Hashing

**Never store plaintext passwords**:

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)
```

### Query Logging

**Sanitized logging** prevents credential leaks:

```python
import logging
import re

class SanitizedFormatter(logging.Formatter):
    """Formatter that sanitizes sensitive data"""

    def format(self, record):
        message = super().format(record)

        # Redact passwords from connection strings
        message = re.sub(
            r'password=\S+',
            'password=***REDACTED***',
            message
        )

        # Redact API keys
        message = re.sub(
            r'apikey=\S+',
            'apikey=***REDACTED***',
            message
        )

        return message
```

## Audit Logging

### Security Event Logging

**Structured logging** for security events:

```python
from core.enhanced_logging import get_logger

logger = get_logger(__name__)

def log_security_event(
    event_type: str,
    user_id: str | None,
    request: Request,
    details: dict[str, Any]
):
    """Log security-related events"""
    logger.warning(
        f"Security event: {event_type}",
        extra={
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
```

**Security Events Logged**:
- Authentication failures
- Authorization denials
- Invalid JWT tokens
- Resource access violations
- Rate limit violations
- Suspicious API patterns

## Emergency Response

### Secret Rotation Procedure

If a secret is accidentally committed:

1. **Immediate Actions** (< 5 minutes):
   ```bash
   # 1. Rotate the compromised secret IMMEDIATELY
   # 2. Update .env with new secret
   # 3. Update GitHub Secrets
   # 4. Verify old secret is revoked
   ```

2. **Git History Cleanup**:
   ```bash
   # Remove secret from git history
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch path/to/file" \
     --prune-empty --tag-name-filter cat -- --all

   # Force push to remote
   git push origin --force --all
   ```

3. **Verification**:
   ```bash
   # Verify secret is removed
   git log --all --full-history -- "*secret*"

   # Run secret scanning
   gitleaks detect --source . --verbose
   ```

### Incident Response

**Security incident response procedure**:

1. Identify and contain the incident
2. Rotate all potentially compromised credentials
3. Review audit logs for unauthorized access
4. Notify affected users if data breach occurred
5. Update security measures to prevent recurrence
6. Document incident and lessons learned

## Best Practices

### For Developers

1. **Never commit secrets** - Use environment variables
2. **Always validate input** - Use Pydantic schemas
3. **Use parameterized queries** - Never string concatenation
4. **Extract user_id from JWT** - Never trust client input
5. **Implement rate limiting** - Prevent abuse
6. **Log security events** - Enable audit trails
7. **Keep dependencies updated** - Address vulnerabilities promptly

### For Operations

1. **Use HTTPS in production** - Encrypt all traffic
2. **Rotate secrets regularly** - Quarterly rotation schedule
3. **Monitor audit logs** - Watch for suspicious activity
4. **Run security scans** - Weekly vulnerability assessments
5. **Implement backups** - Regular encrypted backups
6. **Test incident response** - Quarterly drills

## Related Documentation

- [Components](components.md) - System architecture
- [Data Flow](data-flow.md) - Request processing
- [Secret Management](../development/secret-management.md) - Detailed secret handling guide
