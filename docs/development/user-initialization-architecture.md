# User Initialization Architecture

## Overview

This document describes the unified user initialization architecture that ensures all users (mock, OIDC, API) receive proper defaults regardless of authentication method.

## Problem Statement

**Before:** Different code paths for mock vs. OIDC users led to:
- Code duplication
- Inconsistent behavior
- Silent failures after database wipes
- Users missing prompt templates, parameters, or pipelines

**After:** Single unified code path ensures consistency and defensive initialization.

## Architecture Design

### Core Principle

**All user creation flows converge to `UserService.get_or_create_user()`** which guarantees proper initialization for both new and existing users.

### Key Components

```
┌─────────────────────────────────────────────────────┐
│                User Creation Flow                    │
└─────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────────┐      ┌─────────┐    ┌──────────┐
    │  Mock  │      │  OIDC   │    │   API    │
    │  User  │      │  User   │    │  User    │
    └────────┘      └─────────┘    └──────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ↓
         ┌─────────────────────────────────────┐
         │  UserService.get_or_create_user()   │
         │  - Single source of truth           │
         │  - Defensive initialization         │
         │  - Self-healing for missing defaults │
         └─────────────────────────────────────┘
```

## Implementation

### 1. `UserService.get_or_create_user()` - The Core Method

**Location:** `backend/rag_solution/services/user_service.py`

```python
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
            logger.warning(
                "User %s exists but missing defaults (has %d templates) - reinitializing...",
                existing_user.id,
                len(templates) if templates else 0,
            )
            user_provider_service = UserProviderService(self.db, self.settings)
            _, reinit_templates, parameters = user_provider_service.initialize_user_defaults(
                existing_user.id
            )
            logger.info(
                "Reinitialized user %s defaults: %d templates, %s parameters",
                existing_user.id,
                len(reinit_templates),
                "created" if parameters else "failed",
            )

        return existing_user
    except NotFoundError:
        # User doesn't exist, create with full initialization
        return self.create_user(user_input)
```

**Key Features:**

- ✅ **Defensive initialization**: Checks for missing defaults
- ✅ **Self-healing**: Automatically reinitializes if needed
- ✅ **Database wipe safe**: Handles users without templates
- ✅ **Unified path**: Same for all authentication methods

### 2. Mock User Initialization - Simplified

**Location:** `backend/core/mock_auth.py`

**Before (70+ lines):**
```python
def ensure_mock_user_exists(db, settings):
    # Custom user lookup
    # Custom template check
    # Custom initialization logic
    # Lots of duplicate code
    # Different from OIDC flow
```

**After (20 lines):**
```python
def ensure_mock_user_exists(db, settings, user_key="default") -> UUID:
    """Ensure mock user exists using standard user creation flow."""
    try:
        user_service = UserService(db, settings)

        # Use standardized user creation flow (same as OIDC/API users)
        user_input = UserInput(
            ibm_id=os.getenv("MOCK_USER_IBM_ID", "mock-user-ibm-id"),
            email=settings.mock_user_email,
            name=settings.mock_user_name,
            role=os.getenv("MOCK_USER_ROLE", "admin"),
        )

        logger.info("Ensuring mock user exists: %s", user_input.email)
        user = user_service.get_or_create_user(user_input)
        logger.info("Mock user ready: %s", user.id)

        return user.id

    except (ValueError, KeyError, AttributeError) as e:
        logger.error("Failed to ensure mock user exists: %s", str(e))
        return IdentityService.get_mock_user_id()
```

**Improvements:**

- ✅ **Removed ~50 lines** of duplicate code
- ✅ **Same code path** as OIDC users
- ✅ **Leverages** defensive initialization from `get_or_create_user()`
- ✅ **Simpler** and easier to maintain

### 3. User Defaults Initialization

**What gets initialized:**

1. **Prompt Templates** (3 required):
   - `RAG_QUERY` - For answering questions with RAG
   - `QUESTION_GENERATION` - For generating suggested questions
   - `PODCAST_GENERATION` - For creating podcast scripts

2. **LLM Parameters:**
   - `temperature` - Controls randomness (default: 0.7)
   - `max_new_tokens` - Maximum response length (default: 2048)
   - `top_p`, `top_k` - Sampling parameters

3. **Pipeline Configuration:**
   - Links templates and parameters
   - Sets default search/generation behavior

4. **Provider Assignment:**
   - Links user to default LLM provider (WatsonX, OpenAI, or Anthropic)

**Method:** `UserProviderService.initialize_user_defaults()`

**Location:** `backend/rag_solution/services/user_provider_service.py`

## User Creation Flows

### All Authentication Methods

| Authentication Type | Entry Point | Flow Path |
|-------------------|------------|-----------|
| **Mock User** (SKIP_AUTH=true) | `ensure_mock_user_exists()` | → `get_or_create_user()` → defensive check ✅ |
| **OIDC User** (First login) | OIDC callback handler | → `get_or_create_user()` → `create_user()` ✅ |
| **OIDC User** (Returning) | OIDC callback handler | → `get_or_create_user()` → defensive check ✅ |
| **API User** (Admin creates) | `POST /api/users/` | → `create_user()` ✅ |

**Result:** All users get proper initialization, regardless of how they're created! 🎉

## Edge Cases Handled

### 1. Database Wipe Scenario

**Problem:** User exists but prompt_templates table is empty

**Solution:**
```python
# get_or_create_user() checks template count
if not templates or len(templates) < 3:
    # Reinitialize defaults
    user_provider_service.initialize_user_defaults(user_id)
```

**Result:** Templates automatically recreated on next login/startup

### 2. Failed Initialization

**Problem:** User created but template creation failed partway

**Solution:**
```python
# Defensive check catches incomplete initialization
if not templates or len(templates) < 3:
    # Complete the initialization
    user_provider_service.initialize_user_defaults(user_id)
```

**Result:** Self-healing - fixes itself on next access

### 3. Data Migration

**Problem:** Upgraded from version without podcast templates

**Solution:**
```python
# Check for minimum template count
if len(templates) < 3:
    # Add missing templates
    user_provider_service.initialize_user_defaults(user_id)
```

**Result:** Automatic migration to latest schema

## Benefits

### Code Quality

- ✅ **DRY (Don't Repeat Yourself):** Single code path for all users
- ✅ **Maintainability:** Fix once, works for all auth methods
- ✅ **Testability:** Easier to test single flow
- ✅ **Readability:** Clear, simple logic

### Reliability

- ✅ **Consistency:** All users behave identically
- ✅ **Self-healing:** Automatically fixes missing defaults
- ✅ **Database wipe safe:** Recreates defaults on startup
- ✅ **Migration friendly:** Handles schema changes gracefully

### Developer Experience

- ✅ **No special cases:** Mock users = OIDC users = API users
- ✅ **Predictable:** Always know what to expect
- ✅ **Debuggable:** Single code path to follow
- ✅ **Documented:** Clear architecture pattern

## Testing

### Verification Steps

1. **Check template count** after user creation:
   ```sql
   SELECT COUNT(*) FROM prompt_templates WHERE user_id = '<uuid>';
   -- Expected: 3
   ```

2. **Verify template types** exist:
   ```sql
   SELECT template_type FROM prompt_templates WHERE user_id = '<uuid>';
   -- Expected: RAG_QUERY, QUESTION_GENERATION, PODCAST_GENERATION
   ```

3. **Check LLM parameters** exist:
   ```sql
   SELECT id FROM llm_parameters WHERE user_id = '<uuid>';
   -- Expected: 1 row
   ```

4. **Verify pipeline** exists:
   ```sql
   SELECT id FROM pipeline_configs WHERE user_id = '<uuid>';
   -- Expected: 1 row
   ```

### Test Scenarios

#### Scenario 1: Mock User (First Time)

```bash
# Clean database
python scripts/wipe_database.py --backup

# Start backend (SKIP_AUTH=true)
make local-dev-backend

# Verify
psql -d rag_modulo -c "SELECT COUNT(*) FROM prompt_templates;"
# Expected: 3 templates created
```

#### Scenario 2: Mock User (After Wipe)

```bash
# User exists but templates wiped
# Start backend
make local-dev-backend

# Verify defensive initialization triggered
# Check logs for: "User ... exists but missing defaults - reinitializing..."

# Verify templates recreated
psql -d rag_modulo -c "SELECT COUNT(*) FROM prompt_templates;"
# Expected: 3 templates
```

#### Scenario 3: OIDC User (First Login)

```bash
# Set SKIP_AUTH=false
# Login via IBM OIDC

# Verify user created with defaults
psql -d rag_modulo -c "SELECT COUNT(*) FROM prompt_templates WHERE user_id = '<oidc_user_id>';"
# Expected: 3 templates
```

## Migration Guide

### From Old Architecture

If you're upgrading from the old architecture with separate mock user logic:

1. **No code changes needed** in application code
2. **Database schema** unchanged
3. **Environment variables** unchanged
4. **Existing users** will be self-healed on next access

### Rollback Plan

If issues arise:

1. **Code rollback:** Revert to previous commit
2. **Database:** No schema changes, safe to rollback code
3. **Users:** Will continue working (old code compatible)

## Performance Considerations

### Cost: One Extra Query Per User Access

```python
# Added check in get_or_create_user()
templates = template_service.get_user_templates(existing_user.id)
```

**Impact:**
- **Query:** Simple SELECT with indexed user_id
- **Frequency:** Once per user login/access
- **Cost:** ~1-5ms (negligible)

**Benefits outweigh cost:**
- ✅ Prevents silent failures (hours of debugging)
- ✅ Self-healing (no manual intervention)
- ✅ Database wipe safe (automatic recovery)

### Caching Opportunity (Future)

Could cache template count per user to reduce queries:

```python
# Future optimization
if not cache.get(f"user:{user_id}:templates_ok"):
    templates = template_service.get_user_templates(user_id)
    if len(templates) >= 3:
        cache.set(f"user:{user_id}:templates_ok", True, ttl=3600)
```

## Related Documentation

- [Authentication Bypass Architecture](../features/authentication-bypass.md) - Mock authentication
- [Service Layer Design](./service-layer.md) - Service architecture patterns
- [Database Management Scripts](../../scripts/README.md) - Wipe/restore procedures

## References

- **Primary Files:**
  - `backend/rag_solution/services/user_service.py:53-103`
  - `backend/core/mock_auth.py:109-155`
  - `backend/rag_solution/services/user_provider_service.py:34-76`

- **Related Issues:**
  - GitHub #483: Enhanced health check for user defaults
  - Original bug: Missing templates after database wipe

- **Pull Requests:**
  - Refactor: Unified user initialization architecture
