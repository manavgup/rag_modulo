# Authentication Bypass Architecture

## Overview

RAG Modulo implements a clean authentication bypass mechanism for development and testing environments through a single environment variable: `SKIP_AUTH`. This allows developers to work locally without requiring IBM OIDC Provider access while maintaining the exact same authentication flow in production.

## Architecture Principles

### 1. Single Source of Truth ✅

**One environment variable controls authentication mode:**

```bash
# Backend .env
SKIP_AUTH=true   # Development/Testing
SKIP_AUTH=false  # Production (default)
```

### 2. Frontend is Authentication-Agnostic ✅

The frontend never knows whether authentication is bypassed:

- Always calls `/api/auth/userinfo` to get user data
- Stores whatever `access_token` is provided
- Makes authenticated API calls the same way
- No configuration needed in frontend `.env`

### 3. Backend Controls Everything ✅

When `SKIP_AUTH=true`:

- Backend returns mock user data
- Backend provides bypass token: `"dev-bypass-auth"`
- Backend accepts any token starting with `dev-`
- Backend creates mock user in database with full initialization

When `SKIP_AUTH=false`:

- Backend enforces IBM OIDC authentication
- Backend validates real JWT tokens
- Backend requires proper OAuth flow

## How It Works

### Development Flow (SKIP_AUTH=true)

```
┌─────────────┐
│   Frontend  │
└─────────────┘
       │
       │ 1. GET /api/auth/userinfo
       ↓
┌─────────────────────────────────────────┐
│   Backend (Authentication Middleware)   │
│   - Checks SKIP_AUTH=true              │
│   - Creates/retrieves mock user in DB  │
└─────────────────────────────────────────┘
       │
       │ 2. Returns:
       │    {
       │      "uuid": "9bae4a21-...",
       │      "email": "dev@example.com",
       │      "name": "Development User",
       │      "role": "admin",
       │      "access_token": "dev-bypass-auth",  ← Bypass token
       │      "token_type": "Bearer"
       │    }
       ↓
┌─────────────┐
│   Frontend  │
│   Stores:   │
│   - access_token: "dev-bypass-auth"    │
│   - user data in state                 │
└─────────────┘
       │
       │ 3. Subsequent requests with:
       │    Authorization: Bearer dev-bypass-auth
       ↓
┌─────────────────────────────────────────┐
│   Backend accepts (token starts with   │
│   "dev-", SKIP_AUTH=true)               │
└─────────────────────────────────────────┘
```

### Production Flow (SKIP_AUTH=false)

```
┌─────────────┐
│   Frontend  │
└─────────────┘
       │
       │ 1. GET /api/auth/userinfo (no token yet)
       ↓
┌─────────────────────────────────────────┐
│   Backend (Authentication Middleware)   │
│   - Checks SKIP_AUTH=false             │
│   - No Authorization header             │
│   - Returns 401 Unauthorized            │
└─────────────────────────────────────────┘
       │
       │ 2. Frontend redirects to IBM OIDC
       ↓
┌─────────────┐
│  IBM OIDC   │
│  Provider   │
└─────────────┘
       │
       │ 3. User authenticates, returns code
       ↓
┌─────────────┐
│   Backend   │
│   - Exchanges code for token           │
│   - Validates JWT                      │
│   - Creates/retrieves user in DB       │
│   - Returns user data + JWT            │
└─────────────────────────────────────────┘
       │
       │ 4. Frontend stores JWT
       ↓
┌─────────────┐
│   Frontend  │
│   Uses JWT for all API calls           │
└─────────────┘
```

## User Initialization Architecture

### Unified User Creation (All Authentication Methods)

**Design Principle:** All users (mock, OIDC, API) use the same code path for initialization to ensure consistency and prevent silent failures.

#### Single Source: `UserService.get_or_create_user()`

All user creation flows converge to a single method that guarantees proper initialization:

```python
# backend/rag_solution/services/user_service.py

def get_or_create_user(self, user_input: UserInput) -> UserOutput:
    """Gets existing user or creates new one, ensuring all required defaults exist.

    Provides defensive initialization to handle edge cases where users may exist
    in the database but are missing required defaults (e.g., after database wipes,
    failed initializations, or data migrations).
    """
    try:
        existing_user = self.user_repository.get_by_ibm_id(user_input.ibm_id)

        # Defensive check: Ensure user has required defaults
        template_service = PromptTemplateService(self.db)
        templates = template_service.get_user_templates(existing_user.id)

        if not templates or len(templates) < 3:
            # User missing defaults - reinitialize
            user_provider_service.initialize_user_defaults(existing_user.id)

        return existing_user
    except NotFoundError:
        # User doesn't exist, create with full initialization
        return self.create_user(user_input)
```

**What gets initialized:**

1. **Prompt Templates** (3 required):
   - `RAG_QUERY` - For answering questions
   - `QUESTION_GENERATION` - For generating suggested questions
   - `PODCAST_GENERATION` - For creating podcast scripts

2. **LLM Parameters:**
   - Default generation settings (temperature, max_tokens, etc.)

3. **Pipeline Configuration:**
   - Default RAG pipeline linking templates and parameters

4. **Provider Assignment:**
   - Links user to default LLM provider (usually WatsonX)

#### Mock User Creation (Simplified)

**Before (Special Case):**
```python
# Old approach - separate logic for mock users
def ensure_mock_user_exists(db, settings):
    # Custom check for existing user
    # Custom template initialization
    # Lots of duplicate code
    # Different behavior than OIDC users
```

**After (Unified):**
```python
# New approach - uses same path as OIDC users
def ensure_mock_user_exists(db, settings):
    """Ensure mock user exists using standard user creation flow."""
    user_service = UserService(db, settings)
    user_input = UserInput(
        ibm_id=os.getenv("MOCK_USER_IBM_ID", "mock-user-ibm-id"),
        email=settings.mock_user_email,
        name=settings.mock_user_name,
        role=os.getenv("MOCK_USER_ROLE", "admin"),
    )

    # Same code path as OIDC users!
    user = user_service.get_or_create_user(user_input)
    return user.id
```

**Benefits:**

- ✅ **Consistency**: Mock and OIDC users behave identically
- ✅ **Less code**: Removed ~50 lines of duplicate logic
- ✅ **Self-healing**: Automatically fixes users missing defaults
- ✅ **Database wipe safe**: Templates recreated on next startup
- ✅ **Better tested**: Single code path = easier to test

#### All User Creation Paths

| User Type | Entry Point | Flow |
|-----------|------------|------|
| **Mock User** (SKIP_AUTH=true) | `ensure_mock_user_exists()` | → `get_or_create_user()` → defensive check |
| **OIDC User** (First login) | OIDC callback | → `get_or_create_user()` → `create_user()` |
| **OIDC User** (Returning) | OIDC callback | → `get_or_create_user()` → defensive check |
| **API User** (Admin creates) | `POST /api/users/` | → `create_user()` |

**Result:** All users get proper initialization, regardless of authentication method! 🎉

## Implementation Details

### Backend Components

#### 1. Bypass Token (Hardcoded)

**Location:** `backend/rag_solution/router/auth_router.py`

```python
# Authentication bypass token for development/testing
# When SKIP_AUTH=true, this token is returned to frontend and accepted by backend
# Hardcoded for security - not configurable to prevent production misconfiguration
BYPASS_TOKEN = "dev-bypass-auth"
```

**Why hardcoded?**

- ❌ Prevents misconfiguration in `.env` files
- ✅ Clear intent - it's a development constant
- ✅ Token value doesn't matter (any `dev-*` token works)
- ✅ Reduces configuration surface area

#### 2. Mock Token Validation

**Location:** `backend/core/mock_auth.py`

```python
def is_mock_token(token: str) -> bool:
    """Check if a token is a recognized mock token."""
    if not token:
        return False

    # Accept the hardcoded bypass token
    if token == get_mock_token():
        return True

    # Accept any token starting with "dev-"
    return bool(token.startswith("dev-"))

def get_mock_token() -> str:
    """Get the bypass authentication token."""
    return "dev-bypass-auth"
```

#### 3. Userinfo Endpoint Returns Token

**Location:** `backend/rag_solution/router/auth_router.py`

```python
@router.get("/userinfo", response_model=UserInfo)
async def get_userinfo(...):
    if is_bypass_mode_active():
        # Ensure mock user exists in database
        user_uuid = ensure_mock_user_exists(db, settings)
        user_data = create_mock_user_data(str(user_uuid))

        user_info = UserInfo(...)

        # Return user info + bypass token
        response_data = {
            **user_info.model_dump(),
            "access_token": BYPASS_TOKEN,  # ← Token provided here
            "token_type": "Bearer"
        }
        return JSONResponse(content=response_data)
```

#### 4. Production Safety Check

**Location:** `backend/main.py`

```python
def validate_production_security() -> None:
    """Validate security configuration at startup."""
    settings = get_settings()
    environment = os.getenv("ENVIRONMENT", "development").lower()

    # Prevent SKIP_AUTH in production
    if environment == "production" and settings.skip_auth:
        raise RuntimeError(
            "🚨 SECURITY ERROR: SKIP_AUTH=true is not allowed in production"
        )

    if settings.skip_auth:
        logger.warning("⚠️  SKIP_AUTH is enabled - authentication is bypassed!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate security on startup
    validate_production_security()
    ...
```

### Frontend Components

#### 1. UserInfo Interface Extended

**Location:** `frontend/src/services/apiClient.ts`

```typescript
interface UserInfo {
  sub: string;
  name: string | null;
  email: string;
  uuid: string;
  role: string | null;
  access_token?: string;  // ← Optional token from backend
  token_type?: string;
}
```

#### 2. AuthContext Stores Token

**Location:** `frontend/src/contexts/AuthContext.tsx`

```typescript
// Fetch user info from backend
const userInfo = await apiClient.getUserInfo();

// Store access token if provided (for SKIP_AUTH mode)
// Backend returns token when in bypass mode
if (userInfo.access_token) {
  localStorage.setItem('access_token', userInfo.access_token);
}

// Continue with normal user setup...
```

## Configuration

### Development Environment

**Backend `.env`:**

```bash
# Enable authentication bypass
SKIP_AUTH=true

# Mock user configuration
MOCK_USER_EMAIL=dev@example.com
MOCK_USER_NAME=Development User

# Optional: Override default mock user UUID
# MOCK_USER_ID=12345678-1234-5678-1234-567812345678
```

**Frontend:** No configuration needed! Frontend is agnostic.

### Production Environment

**Backend `.env`:**

```bash
# Disable authentication bypass (secure by default)
SKIP_AUTH=false

# IBM OIDC Configuration
IBM_CLIENT_ID=your-production-client-id
IBM_CLIENT_SECRET=your-production-client-secret
OIDC_DISCOVERY_ENDPOINT=https://your-oidc-provider/.well-known/openid-configuration
OIDC_AUTH_URL=https://your-oidc-provider/authorize
OIDC_TOKEN_URL=https://your-oidc-provider/token
```

**Frontend:** No configuration needed! Frontend is agnostic.

## Security Considerations

### ✅ Security Features

1. **Production Protection:**
   - Application refuses to start if `SKIP_AUTH=true` and `ENVIRONMENT=production`
   - Explicit runtime error with clear message
   - Prevents accidental production bypass

2. **Secure Defaults:**
   - `SKIP_AUTH` defaults to `false` in Settings
   - Must be explicitly enabled in `.env`
   - Clear warning logs when bypass is active

3. **No Hardcoded Secrets:**
   - Mock user UUID generated or retrieved from database
   - Bypass token is meaningless (just a marker)
   - All real credentials come from environment variables

### ⚠️ Important Notes

1. **Never set `SKIP_AUTH=true` in production**
   - Application will refuse to start
   - All authentication is bypassed
   - Anyone can access the system

2. **Mock token is not secret:**
   - The value `"dev-bypass-auth"` is hardcoded in source
   - It's only effective when `SKIP_AUTH=true`
   - In production, real JWT validation is enforced

3. **Environment variable:**
   - Set `ENVIRONMENT=production` in production `.env`
   - This enables the security check
   - Defaults to `development` if not set

## Testing

### Manual Testing - Development Mode

```bash
# 1. Set bypass mode
export SKIP_AUTH=true

# 2. Start backend
make dev-hotreload

# 3. Test userinfo endpoint
curl http://localhost:8000/api/auth/userinfo

# Expected response:
# {
#   "uuid": "9bae4a21-...",
#   "email": "dev@example.com",
#   "name": "Development User",
#   "role": "admin",
#   "access_token": "dev-bypass-auth",
#   "token_type": "Bearer"
# }

# 4. Test authenticated endpoint with bypass token
curl -H "Authorization: Bearer dev-bypass-auth" \
  http://localhost:8000/api/collections
```

### Manual Testing - Production Mode

```bash
# 1. Disable bypass
export SKIP_AUTH=false
export ENVIRONMENT=production

# 2. Start backend (should start successfully)
make dev-hotreload

# 3. Test without authentication (should fail)
curl http://localhost:8000/api/auth/userinfo
# Expected: 401 Unauthorized

# 4. Test bypass token (should fail)
curl -H "Authorization: Bearer dev-bypass-auth" \
  http://localhost:8000/api/collections
# Expected: 401 Unauthorized (bypass tokens not accepted)
```

### Testing Production Safety

```bash
# 1. Try to start with bad configuration
export SKIP_AUTH=true
export ENVIRONMENT=production
make dev-hotreload

# Expected: Application refuses to start with error:
# RuntimeError: 🚨 SECURITY ERROR: SKIP_AUTH=true is not allowed in production
```

## Troubleshooting

### Issue: Frontend shows "Not authenticated" error

**Solution:**

1. Verify `SKIP_AUTH=true` in backend `.env`
2. Check backend logs for: "Authentication bypass mode active"
3. Verify `/api/auth/userinfo` returns `access_token` field
4. Check browser localStorage for `access_token`

### Issue: Backend rejects bypass token

**Solution:**

1. Verify `SKIP_AUTH=true` in backend `.env`
2. Check token starts with `dev-` (e.g., `dev-bypass-auth`)
3. Verify `is_mock_token()` accepts the token
4. Check backend logs for authentication decisions

### Issue: Application won't start in production

**Expected behavior** if `SKIP_AUTH=true` and `ENVIRONMENT=production`:

```
RuntimeError: 🚨 SECURITY ERROR: SKIP_AUTH=true is not allowed in production
```

**Solution:** Set `SKIP_AUTH=false` in production `.env`

## Migration Guide

### From Old Configuration (with MOCK_TOKEN)

**Old `.env`:**

```bash
SKIP_AUTH=true
MOCK_TOKEN=dev-0000-0000-0000  # ← Remove this
```

**New `.env`:**

```bash
SKIP_AUTH=true
# MOCK_TOKEN removed - automatically handled by backend
```

**What changed:**

- ❌ Removed `MOCK_TOKEN` environment variable
- ❌ Removed `settings.mock_token` from `core/config.py`
- ✅ Backend uses hardcoded `BYPASS_TOKEN = "dev-bypass-auth"`
- ✅ Backend automatically provides token via `/api/auth/userinfo`
- ✅ Frontend automatically stores token from response

**No code changes needed** - existing deployments continue working when you update to the new configuration.

## API Reference

### GET /api/auth/userinfo

Retrieve current user information.

**When SKIP_AUTH=true:**

```http
GET /api/auth/userinfo HTTP/1.1
Host: localhost:8000
```

**Response:**

```json
{
  "sub": "test_user_id",
  "name": "Development User",
  "email": "dev@example.com",
  "uuid": "9bae4a21-718b-4c8b-bdd2-22857779a85b",
  "role": "admin",
  "access_token": "dev-bypass-auth",
  "token_type": "Bearer"
}
```

**When SKIP_AUTH=false:**

Requires `Authorization: Bearer <valid-jwt>` header, returns real user data (no `access_token` field).

## Related Configuration

### Mock User Settings

```bash
# Customize mock user (optional)
MOCK_USER_EMAIL=dev@example.com
MOCK_USER_NAME=Development User

# Override mock user UUID (optional, rarely needed)
# MOCK_USER_ID=12345678-1234-5678-1234-567812345678
```

### Environment Detection

```bash
# Set environment for security checks
ENVIRONMENT=development  # or production, staging, testing
```

## Best Practices

### ✅ DO

- Set `SKIP_AUTH=false` (or omit it) in production
- Set `ENVIRONMENT=production` in production deployments
- Use bypass mode for local development and testing
- Keep `MOCK_USER_EMAIL` and `MOCK_USER_NAME` descriptive

### ❌ DON'T

- Set `SKIP_AUTH=true` in production (application will refuse to start)
- Configure `MOCK_TOKEN` in `.env` (it's hardcoded now)
- Add `REACT_APP_SKIP_AUTH` to frontend (frontend is agnostic)
- Rely on bypass tokens in production code paths

## Security Audit Checklist

Before deploying to production:

- [ ] Verify `SKIP_AUTH=false` (or not set) in production `.env`
- [ ] Verify `ENVIRONMENT=production` in production `.env`
- [ ] Confirm IBM OIDC credentials are configured
- [ ] Test that application starts successfully
- [ ] Verify `/api/auth/userinfo` requires authentication
- [ ] Test that `dev-*` tokens are rejected

## Related Documentation

- [Configuration Guide](../configuration.md) - All environment variables
- [Authentication Overview](../architecture/authentication.md) - Full auth architecture
- [Deployment Guide](../deployment/production.md) - Production deployment
- [Security Guide](../architecture/security.md) - Security best practices
