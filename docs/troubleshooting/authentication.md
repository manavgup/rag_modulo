# Authentication Troubleshooting Guide

This guide covers authentication and authorization issues in RAG Modulo, including JWT token problems, OIDC integration errors, and permission debugging.

## Table of Contents

- [Overview](#overview)
- [JWT Authentication Issues](#jwt-authentication-issues)
- [OIDC Integration Problems](#oidc-integration-problems)
- [Permission & Authorization Errors](#permission--authorization-errors)
- [Session Management Issues](#session-management-issues)
- [Development Mode (SKIP_AUTH)](#development-mode-skip_auth)
- [Production Security Validation](#production-security-validation)

## Overview

RAG Modulo supports multiple authentication methods:

1. **JWT Authentication**: Token-based auth for API access
2. **OIDC Integration**: IBM W3ID single sign-on
3. **Development Mode**: Auth bypass for testing (SKIP_AUTH)

**Key Files**:
- `./backend/auth/` - Authentication logic
- `./backend/auth/oidc.py` - OIDC integration
- `./backend/core/authentication_middleware.py` - Request authentication
- `./backend/main.py` - Security validation

**Configuration** (`.env`):
```bash
# JWT Settings
JWT_SECRET_KEY=your-secure-jwt-secret-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# OIDC Settings
OIDC_DISCOVERY_ENDPOINT=https://w3id.sso.ibm.com/auth/sps/samlidp2/saml20
OIDC_AUTH_URL=https://w3id.sso.ibm.com/pkmsoidc/authorize
OIDC_TOKEN_URL=https://w3id.sso.ibm.com/pkmsoidc/token
IBM_CLIENT_ID=your-client-id
IBM_CLIENT_SECRET=your-client-secret

# Development
SKIP_AUTH=false  # NEVER true in production!
```

## JWT Authentication Issues

### Issue 1: "Invalid token" or "Token expired"

**Symptoms**:
```bash
$ curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/collections
{
  "detail": "Invalid authentication credentials"
}
```

**Diagnosis**:

```bash
# Decode JWT to check expiration
# Install jwt-cli: cargo install jwt-cli
jwt decode $TOKEN

# Or use Python
python3 << EOF
import jwt
token = "$TOKEN"
try:
    decoded = jwt.decode(token, options={"verify_signature": False})
    print(f"User: {decoded.get('sub')}")
    print(f"Expires: {decoded.get('exp')}")
except Exception as e:
    print(f"Error: {e}")
EOF
```

**Common Causes & Solutions**:

**A) Token Expired**:

```python
# Default expiration: 24 hours (1440 minutes)
# Check .env
JWT_EXPIRATION_MINUTES=1440

# Increase expiration time (not recommended for production)
JWT_EXPIRATION_MINUTES=10080  # 7 days

# OR request new token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"password"}' \
  | jq -r '.access_token'
```

**B) Invalid JWT Secret**:

```bash
# Check JWT_SECRET_KEY is set
docker compose exec backend env | grep JWT_SECRET_KEY

# Verify secret matches between token creation and validation
# Generate new secret (min 32 characters)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env
JWT_SECRET_KEY=new-secret-here

# Restart backend
docker compose restart backend

# Request new token (old tokens are now invalid)
```

**C) Token Format Issues**:

```bash
# JWT format: "Bearer <token>"
# Correct:
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Incorrect:
Authorization: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Missing "Bearer"
Authorization: Bearer Bearer eyJhbGci...  # Double "Bearer"
```

**D) Token Validation Logic**:

```python
# Debug token validation
# File: backend/core/authentication_middleware.py

# Add debugging
import logging
logger = logging.getLogger(__name__)

try:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    logger.info(f"Token decoded: {payload}")
except jwt.ExpiredSignatureError:
    logger.error("Token expired")
    raise HTTPException(status_code=401, detail="Token expired")
except jwt.InvalidTokenError as e:
    logger.error(f"Invalid token: {e}")
    raise HTTPException(status_code=401, detail="Invalid token")
```

### Issue 2: "Missing Authorization Header"

**Symptoms**:
```bash
$ curl http://localhost:8000/api/collections
{
  "detail": "Not authenticated"
}
```

**Diagnosis**:

```bash
# Check if SKIP_AUTH is disabled
docker compose exec backend env | grep SKIP_AUTH
# Should be: SKIP_AUTH=false

# Verify endpoint requires authentication
curl -v http://localhost:8000/api/collections
# Look for: WWW-Authenticate: Bearer

# Check middleware is loaded
docker compose exec backend python -c "
from main import app
print([m for m in app.user_middleware if 'Authentication' in str(m)])
"
```

**Solutions**:

**A) Add Authorization Header**:

```bash
# Get token first
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"password"}' \
  | jq -r '.access_token')

# Use token in request
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/collections
```

**B) Exclude Public Endpoints** (if needed):

```python
# File: backend/core/authentication_middleware.py

# Public endpoints (no auth required)
PUBLIC_PATHS = [
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/auth/login",
    "/api/auth/register",
]

if request.url.path in PUBLIC_PATHS:
    return await call_next(request)
```

### Issue 3: Token Creation/Login Fails

**Symptoms**:
```bash
$ curl -X POST http://localhost:8000/api/auth/login \
  -d '{"username":"user@example.com","password":"password"}'
{
  "detail": "Invalid credentials"
}
```

**Diagnosis**:

```bash
# Check user exists in database
docker compose exec backend python -c "
from rag_solution.file_management.database import get_db
from rag_solution.models.user import User

db = next(get_db())
user = db.query(User).filter(User.email == 'user@example.com').first()
print(f'User found: {user is not None}')
print(f'User ID: {user.id if user else None}')
"

# Check password hashing
docker compose exec backend python -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
password = 'password'
hashed = pwd_context.hash(password)
print(f'Hashed: {hashed}')
print(f'Verify: {pwd_context.verify(password, hashed)}')
"
```

**Solutions**:

**A) Create Test User**:

```python
# File: backend/scripts/create_user.py
from rag_solution.file_management.database import get_db
from rag_solution.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
db = next(get_db())

user = User(
    email="test@example.com",
    hashed_password=pwd_context.hash("password"),
    is_active=True
)
db.add(user)
db.commit()
print(f"User created: {user.id}")
```

```bash
# Run script
docker compose exec backend python scripts/create_user.py
```

**B) Check Password Hash Algorithm**:

```python
# Ensure bcrypt is used (secure)
# File: backend/auth/ (authentication logic)

from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash password
hashed = pwd_context.hash(plain_password)

# Verify password
is_valid = pwd_context.verify(plain_password, hashed_password)
```

## OIDC Integration Problems

### Issue 1: OIDC Login Fails

**Symptoms**:
```bash
# Browser redirects to IBM W3ID but returns error
Error: invalid_client
# Or
Error: redirect_uri_mismatch
```

**Diagnosis**:

```bash
# Check OIDC configuration
docker compose exec backend env | grep OIDC

# Should have:
OIDC_DISCOVERY_ENDPOINT=https://w3id.sso.ibm.com/auth/sps/samlidp2/saml20
OIDC_AUTH_URL=https://w3id.sso.ibm.com/pkmsoidc/authorize
OIDC_TOKEN_URL=https://w3id.sso.ibm.com/pkmsoidc/token
IBM_CLIENT_ID=your-client-id
IBM_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=http://localhost:3000/auth/callback

# Test OIDC endpoints
curl -v https://w3id.sso.ibm.com/pkmsoidc/.well-known/openid-configuration
```

**Solutions**:

**A) Invalid Client ID/Secret**:

```bash
# Verify credentials with IBM W3ID admin
# https://w3id.alpha.sso.ibm.com/

# Test authentication manually
curl -X POST https://w3id.sso.ibm.com/pkmsoidc/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=$IBM_CLIENT_ID" \
  -d "client_secret=$IBM_CLIENT_SECRET"

# Should return access_token if credentials are valid
```

**B) Redirect URI Mismatch**:

```bash
# Ensure redirect URI matches exactly in:
# 1. OIDC provider configuration (IBM W3ID)
# 2. .env file
# 3. Frontend configuration

# Common mistakes:
# - http vs https
# - localhost vs 127.0.0.1
# - Missing trailing slash
# - Port mismatch

# Correct:
OIDC_REDIRECT_URI=http://localhost:3000/auth/callback

# Frontend must use same URI:
# File: frontend/.env
REACT_APP_OIDC_REDIRECT_URI=http://localhost:3000/auth/callback
```

**C) CORS Issues**:

```python
# File: backend/main.py
from core.loggingcors_middleware import LoggingCORSMiddleware

app.add_middleware(
    LoggingCORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://rag-modulo.example.com",
        "https://w3id.sso.ibm.com",  # Add OIDC provider
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue 2: OIDC Token Exchange Fails

**Symptoms**:
```bash
# After successful redirect, token exchange fails
Error: invalid_grant
# Or
Error: authorization_pending
```

**Diagnosis**:

```bash
# Check OIDC flow in logs
docker compose logs backend | grep -i oidc

# Look for:
# 1. Authorization code received
# 2. Token exchange request
# 3. Token response

# Debug token exchange
docker compose exec backend python << EOF
import requests

response = requests.post(
    "https://w3id.sso.ibm.com/pkmsoidc/token",
    data={
        "grant_type": "authorization_code",
        "code": "AUTH_CODE_HERE",
        "redirect_uri": "http://localhost:3000/auth/callback",
        "client_id": "$IBM_CLIENT_ID",
        "client_secret": "$IBM_CLIENT_SECRET",
    }
)
print(response.status_code)
print(response.json())
EOF
```

**Solutions**:

**A) Authorization Code Expired**:

```python
# Authorization codes expire quickly (usually 60-300 seconds)
# Ensure immediate token exchange after receiving code

# File: backend/auth/oidc.py
async def exchange_code_for_token(code: str):
    # Exchange IMMEDIATELY after receiving code
    response = await client.post(
        OIDC_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,  # Use immediately
            "redirect_uri": OIDC_REDIRECT_URI,
            "client_id": IBM_CLIENT_ID,
            "client_secret": IBM_CLIENT_SECRET,
        }
    )
    return response.json()
```

**B) Code Already Used**:

```python
# Authorization codes can only be used ONCE
# Don't retry token exchange with same code

# Check for duplicate requests
# File: backend/auth/oidc.py
_used_codes = set()

async def exchange_code_for_token(code: str):
    if code in _used_codes:
        raise HTTPException(status_code=400, detail="Code already used")

    _used_codes.add(code)
    # ... exchange code ...
```

### Issue 3: OIDC Token Validation Fails

**Symptoms**:
```bash
# Token received but validation fails
Error: Invalid token signature
# Or
Error: Token issuer mismatch
```

**Solutions**:

```python
# File: backend/auth/oidc.py

# Skip signature verification for id_token (IBM W3ID specific)
import jwt

id_token = token_response["id_token"]
user_info = jwt.decode(
    id_token,
    options={"verify_signature": False},  # Skip signature verification
    algorithms=["RS256"]
)

# Extract user info
user_email = user_info.get("email")
user_name = user_info.get("name")
user_id = user_info.get("sub")
```

## Permission & Authorization Errors

### Issue 1: "Access Denied" for Valid User

**Symptoms**:
```bash
$ curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/collections/some-collection-id
{
  "detail": "Access denied"
}
```

**Diagnosis**:

```bash
# Extract user ID from token
python3 << EOF
import jwt
token = "$TOKEN"
decoded = jwt.decode(token, options={"verify_signature": False})
print(f"User ID: {decoded.get('sub')}")
EOF

# Check resource ownership
docker compose exec backend python -c "
from rag_solution.file_management.database import get_db
from rag_solution.models.collection import Collection

db = next(get_db())
collection = db.query(Collection).filter(Collection.id == 'collection-id-here').first()
print(f'Owner ID: {collection.user_id if collection else None}')
"

# Compare user ID from token with resource owner ID
```

**Solutions**:

**A) Check Authorization Logic**:

```python
# File: backend/rag_solution/router/collection_router.py

@router.get("/collections/{collection_id}")
async def get_collection(
    collection_id: UUID,
    current_user: User = Depends(get_current_user)  # Extract user from token
):
    collection = db.query(Collection).filter(Collection.id == collection_id).first()

    # Check ownership
    if collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return collection
```

**B) Team/Shared Access** (if applicable):

```python
# Check if user has team access
team_member = db.query(TeamMember).filter(
    TeamMember.team_id == collection.team_id,
    TeamMember.user_id == current_user.id
).first()

if not (collection.user_id == current_user.id or team_member):
    raise HTTPException(status_code=403, detail="Access denied")
```

### Issue 2: Admin/Role-Based Access Issues

**Symptoms**:
```bash
# User needs admin access but doesn't have it
Error: Insufficient permissions
```

**Solutions**:

```python
# File: backend/rag_solution/models/user.py

# Add role-based access
class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True)
    email = Column(String, unique=True, index=True)
    is_admin = Column(Boolean, default=False)
    role = Column(String, default="user")  # user, admin, superadmin

# Check admin access
def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Use in routes
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    admin: User = Depends(require_admin)
):
    # ... delete user ...
    pass
```

## Session Management Issues

### Issue 1: Session Expires Unexpectedly

**Symptoms**:
```bash
# User logged out after short time
# Session ID not found
```

**Diagnosis**:

```bash
# Check session configuration
docker compose exec backend env | grep SESSION

# Check session middleware
docker compose exec backend python -c "
from main import app
print([m for m in app.user_middleware if 'Session' in str(m)])
"
```

**Solutions**:

```python
# File: backend/main.py
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.jwt_secret_key,
    max_age=86400,  # 24 hours (increase if needed)
    same_site="lax",
    https_only=False,  # Set True in production with HTTPS
)
```

### Issue 2: CORS Cookie Issues

**Symptoms**:
```bash
# Cookies not being set/sent in cross-origin requests
# Session not persisting
```

**Solutions**:

```python
# File: backend/main.py
app.add_middleware(
    LoggingCORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://rag-modulo.example.com",
    ],
    allow_credentials=True,  # CRITICAL for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# File: frontend/src/api/client.js
axios.defaults.withCredentials = true;  // Send cookies with requests
```

## Development Mode (SKIP_AUTH)

### Enabling Development Mode

**Use Case**: Fast local development without authentication

```bash
# File: .env
SKIP_AUTH=true
DEVELOPMENT_MODE=true

# Restart backend
docker compose restart backend

# Test without token
curl http://localhost:8000/api/collections
# Should work without Authorization header
```

**How It Works**:

```python
# File: backend/core/authentication_middleware.py

if settings.skip_auth:
    # Bypass authentication
    # Create mock user
    request.state.user = User(
        id="00000000-0000-0000-0000-000000000000",
        email="dev@example.com",
        is_active=True
    )
    return await call_next(request)
```

### Disabling Development Mode

```bash
# File: .env
SKIP_AUTH=false

# Restart backend
docker compose restart backend

# Now requires authentication
curl http://localhost:8000/api/collections
# Returns: 401 Unauthorized
```

## Production Security Validation

### Startup Security Check

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

    # Log warning if SKIP_AUTH enabled
    if settings.skip_auth:
        logger.warning("⚠️  SKIP_AUTH is enabled - authentication is bypassed!")
```

**This check PREVENTS production deployment with SKIP_AUTH enabled**

### Production Configuration

```bash
# File: .env (production)
ENVIRONMENT=production
SKIP_AUTH=false  # REQUIRED
JWT_SECRET_KEY=secure-random-string-min-32-chars  # Change from default!

# Generate secure JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Testing Authentication

```bash
# Test authentication is enforced
curl http://localhost:8000/api/collections
# Should return: 401 Unauthorized

# Test with valid token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"password"}' \
  | jq -r '.access_token')

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/collections
# Should return: 200 OK with collections
```

## Common Authentication Patterns

### Pattern 1: Extract Current User

```python
# File: backend/auth/dependencies.py

from fastapi import Depends, HTTPException
from rag_solution.models.user import User

async def get_current_user(
    authorization: str = Header(None),
    settings: Settings = Depends(get_settings)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ")[1]
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    user_id = payload.get("sub")

    db = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# Use in routes
@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {"email": current_user.email, "id": str(current_user.id)}
```

### Pattern 2: Optional Authentication

```python
# File: backend/auth/dependencies.py

async def get_optional_user(
    authorization: str = Header(None),
    settings: Settings = Depends(get_settings)
) -> User | None:
    """Return user if authenticated, None otherwise."""
    if not authorization:
        return None

    try:
        return await get_current_user(authorization, settings)
    except HTTPException:
        return None

# Use for public endpoints with optional features
@router.get("/search")
async def search(
    query: str,
    current_user: User | None = Depends(get_optional_user)
):
    # Personalize if user is authenticated
    if current_user:
        return search_with_user_context(query, current_user)
    else:
        return search_public(query)
```

## Related Documentation

- [Security Deployment Guide](../deployment/security.md) - Production security best practices
- [Debugging Guide](debugging.md) - Debug authentication issues
- [API Documentation](../api/index.md) - API authentication requirements
- [Development Workflow](../development/workflow.md) - Local development setup
