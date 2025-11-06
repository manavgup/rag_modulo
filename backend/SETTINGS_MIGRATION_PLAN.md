# Settings Dependency Injection Migration Plan

> **Note**: This document is outdated. The codebase has migrated from the legacy `vectordbs.utils.watsonx`
> pattern to using `LLMProviderFactory` for all LLM interactions. See Issue #219 for details.
> Legacy functions are kept for backward compatibility in specific utility contexts only.

## Overview
This document outlines all files that need to be modified to implement proper FastAPI dependency injection for settings, replacing direct `settings` imports with `get_settings()` function.

## Pattern Changes

### Old Pattern (DEPRECATED)
```python
from core.config import settings

# Module-level access (PROBLEM!)
SOME_CONSTANT = settings.some_value

class SomeClass:
    def method(self):
        value = settings.some_setting
```

### New Pattern (RECOMMENDED)

#### Pattern 1: FastAPI Route Dependency Injection
```python
from typing import Annotated
from fastapi import Depends
from core.config import Settings, get_settings

@router.get("/example")
def example_route(
    settings: Annotated[Settings, Depends(get_settings)]
):
    return {"value": settings.some_setting}
```

#### Pattern 2: Service Class Constructor Injection
```python
from core.config import Settings

class SomeService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.some_value = settings.some_setting
```

#### Pattern 3: Application Startup (Main Module)
```python
from core.config import get_settings

# For startup tasks only
settings = get_settings()
if settings.enable_feature:
    # Configure feature
```

## Files Requiring Modification

### 🔴 CRITICAL - Module-Level Settings Access (9 files)
These files access settings at import time and MUST be fixed:

1. **vectordbs/utils/watsonx.py**
   - Lines 25-26: `WATSONX_INSTANCE_ID = settings.wx_project_id`
   - Lines 25-26: `EMBEDDING_MODEL = settings.embedding_model`
   - **Fix**: Move to function parameters or class initialization

2. **vectordbs/chroma_store.py**
   - Module-level settings access
   - **Fix**: Move to class `__init__` method

3. **vectordbs/elasticsearch_store.py**
   - Module-level settings access
   - **Fix**: Move to class `__init__` method

4. **vectordbs/milvus_store.py**
   - Module-level settings access
   - **Fix**: Move to class `__init__` method

5. **vectordbs/pinecone_store.py**
   - Module-level settings access
   - **Fix**: Move to class `__init__` method

6. **vectordbs/weaviate_store.py**
   - Module-level settings access
   - **Fix**: Move to class `__init__` method

7. **rag_solution/data_ingestion/ingestion.py**
   - Module-level settings access
   - **Fix**: Move to function parameters

8. **rag_solution/data_ingestion/chunking.py**
   - Module-level settings access
   - **Fix**: Move to class initialization

9. **rag_solution/data_ingestion/base_processor.py**
   - Module-level settings access
   - **Fix**: Move to class initialization

### 🟡 HIGH PRIORITY - FastAPI Routers (8 files)
These should use `Depends(get_settings)` pattern:

10. **main.py**
    - Application startup configuration
    - **Fix**: Call `get_settings()` directly for startup

11. **rag_solution/router/health_router.py**
    - Route handlers
    - **Fix**: Add `settings: Annotated[Settings, Depends(get_settings)]`

12. **rag_solution/router/auth_router.py**
    - Authentication routes
    - **Fix**: Add `settings: Annotated[Settings, Depends(get_settings)]`

13. **core/authentication_middleware.py**
    - Middleware configuration
    - **Fix**: Pass settings to middleware constructor

14. **core/authorization.py**
    - Authorization checks
    - **Fix**: Pass settings as parameter

15. **core/loggingcors_middleware.py**
    - CORS configuration
    - **Fix**: Pass settings to middleware constructor

16. **auth/oidc.py**
    - OIDC configuration
    - **Fix**: Pass settings as parameter

17. **rag_solution/file_management/database.py**
    - Database configuration
    - **Fix**: Use function parameters or dependency injection

### 🟢 MEDIUM PRIORITY - Services (7 files)
These should receive settings via constructor:

18. **rag_solution/services/system_initialization_service.py**
    - **Fix**: Accept Settings in `__init__`

19. **rag_solution/services/question_service.py**
    - **Fix**: Accept Settings in `__init__`

20. **rag_solution/services/pipeline_service.py**
    - **Fix**: Accept Settings in `__init__`

21. **rag_solution/services/file_management_service.py**
    - **Fix**: Accept Settings in `__init__`

22. **rag_solution/services/collection_service.py**
    - **Fix**: Accept Settings in `__init__`

23. **rag_solution/generation/generator.py**
    - **Fix**: Accept Settings in class initialization

24. **core/logging_utils.py**
    - **Fix**: Already has local `get_settings()` wrapper

### 🔵 LOW PRIORITY - Test Files (23 files)
These can continue using direct imports during migration but should eventually be updated:

25. **tests/test_config_settings.py**
    - **Fix**: Use `get_settings()` in test fixtures

26. **tests/test_ci_isolation.py**
    - **Fix**: Use `get_settings()` for isolation testing

27. **tests/test_comprehensive_ci_failures.py**
    - **Fix**: Use `get_settings()` with cache clearing

28. **tests/test_atomic_test_isolation.py**
    - **Fix**: Use `get_settings()` with proper isolation

29. **tests/test_settings_only.py**
    - **Fix**: Test `get_settings()` function directly

30. **tests/test_cicd_precommit_coverage.py**
    - **Fix**: Use `get_settings()` for CI/CD tests

31. **tests/test_settings_acceptance.py**
    - **Fix**: Test settings with dependency injection

32. **tests/integration/test_ingestion.py**
    - **Fix**: Pass settings to ingestion functions

33. **tests/integration/test_weaviate_store.py**
    - **Fix**: Pass settings to store constructor

34. **tests/integration/test_user_flow.py**
    - **Fix**: Use settings injection in flow tests

35. **tests/integration/test_pinecone_store.py**
    - **Fix**: Pass settings to store constructor

36. **tests/integration/test_elasticsearch_store.py**
    - **Fix**: Pass settings to store constructor

37. **tests/integration/test_chunking.py**
    - **Fix**: Pass settings to chunking functions

38. **tests/fixtures/services.py**
    - **Fix**: Create services with injected settings

39. **tests/fixtures/pipelines.py**
    - **Fix**: Create pipelines with injected settings

40. **tests/fixtures/llm_model.py**
    - **Fix**: Create models with injected settings

41. **tests/fixtures/data.py**
    - **Fix**: Use settings for data generation

42. **tests/fixtures/collections.py**
    - **Fix**: Use settings for collection setup

43. **tests/data_ingestion/test_chunking.py**
    - **Fix**: Pass settings to chunking tests

44. **tests/api/test_health_router.py**
    - **Fix**: Mock settings with `get_settings`

45. **tests/api/test_auth_router.py**
    - **Fix**: Mock settings for auth tests

46. **tests/api/base_test.py**
    - **Fix**: Use `get_settings()` in base test class

47. **tests/core/test_settings_dependency_injection.py**
    - Already updated with proper patterns ✅

## Backward Compatibility Explained

During the migration, we maintain backward compatibility by keeping `settings = get_settings()` at the module level in `core/config.py`. This means:

### What Still Works (Temporarily)
```python
# OLD CODE - Still works during migration
from core.config import settings

def some_function():
    value = settings.rag_llm  # This still works
    url = settings.wx_url     # This still works
```

### Why It Works
- When `core/config.py` is imported, it runs `settings = get_settings()`
- This creates a global settings instance that old code can use
- The instance is cached, so all imports get the same object

### The Problems with This Approach
1. **Import-Time Execution**: Settings are loaded when ANY module imports config
2. **Test Isolation Issues**: Can't change settings between tests easily
3. **Module-Level Constants**: Code like `CONST = settings.value` runs at import time
4. **No Dependency Injection**: Can't mock or override settings for specific components

### The Migration Path
```python
# STEP 1: During migration (both work)
from core.config import settings  # Old way - still works
from core.config import get_settings, Settings  # New way - preferred

# STEP 2: Update to new pattern
from core.config import Settings, get_settings
def some_function(settings: Settings):  # Pass settings as parameter
    value = settings.rag_llm

# STEP 3: After all files migrated
# Remove the global `settings = get_settings()` line from config.py
# Old imports will break, forcing use of new pattern
```

### When to Break Backward Compatibility
Once all 47 files are migrated to use either:
- `get_settings()` directly for startup/main code
- `Depends(get_settings)` for FastAPI routes
- Constructor injection for services

Then we can remove the `settings = get_settings()` line from `config.py`.

## Migration Strategy

### Phase 1: Critical Fixes (Immediate)
1. Fix all module-level settings access (9 files)
2. These prevent proper test isolation and cause import-time execution

### Phase 2: FastAPI Routes (Week 1)
1. Update all routers to use `Depends(get_settings)`
2. Update middleware to receive settings via constructor
3. Update main.py startup configuration

### Phase 3: Services (Week 2)
1. Update all service classes to receive Settings via constructor
2. Update service factory functions to inject settings

### Phase 4: Tests (Optional)
1. Update tests to use `get_settings()` where appropriate
2. Can be done gradually as tests are modified

## Implementation Example: watsonx.py Refactor

### Current Code (PROBLEM):
```python
# vectordbs/utils/watsonx.py
from core.config import settings

# ❌ PROBLEM: These execute at module import time!
WATSONX_INSTANCE_ID = settings.wx_project_id
EMBEDDING_MODEL = settings.embedding_model

# Global clients
client = None
embeddings_client = None

def _get_client() -> APIClient:
    global client
    if client is None:
        client = APIClient(
            project_id=WATSONX_INSTANCE_ID,  # Uses global constant
            credentials=Credentials(api_key=settings.wx_api_key, url=settings.wx_url),
        )
    return client

def get_embeddings(texts, embed_client=None):
    if embed_client is None:
        embed_client = _get_embeddings_client()  # Uses global state
    # ... rest of function
```

### Refactored Code (SOLUTION):
```python
# vectordbs/utils/watsonx.py
from core.config import Settings, get_settings
from typing import Optional

class WatsonXClient:
    """Manages WatsonX connections with dependency injection."""

    _instances: dict[str, 'WatsonXClient'] = {}

    def __init__(self, settings: Settings):
        self.settings = settings
        self.watsonx_instance_id = settings.wx_project_id
        self.embedding_model = settings.embedding_model
        self._client: Optional[APIClient] = None
        self._embeddings_client: Optional[wx_Embeddings] = None

    @classmethod
    def get_instance(cls, settings: Optional[Settings] = None) -> 'WatsonXClient':
        """Get cached instance or create new one."""
        if settings is None:
            settings = get_settings()

        cache_key = settings.wx_project_id or "default"
        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls(settings)
        return cls._instances[cache_key]

    def get_client(self) -> APIClient:
        """Get or create API client."""
        if self._client is None:
            self._client = APIClient(
                project_id=self.watsonx_instance_id,
                credentials=Credentials(
                    api_key=self.settings.wx_api_key,
                    url=self.settings.wx_url
                ),
            )
        return self._client

# ✅ Updated function with settings parameter
def get_embeddings(
    texts: str | list[str],
    embed_client: wx_Embeddings | None = None,
    settings: Optional[Settings] = None
) -> EmbeddingsList:
    """Get embeddings with injected settings."""
    if settings is None:
        settings = get_settings()

    if embed_client is None:
        wx_client = WatsonXClient.get_instance(settings)
        embed_client = wx_client.get_embeddings_client()

    # ... rest of function logic
```

### Usage in FastAPI Routes:
```python
from fastapi import APIRouter, Depends
from typing import Annotated
from core.config import Settings, get_settings
from vectordbs.utils.watsonx import get_embeddings

router = APIRouter()

@router.post("/embeddings")
async def create_embeddings(
    texts: list[str],
    settings: Annotated[Settings, Depends(get_settings)]  # ✅ FastAPI injection
):
    embeddings = get_embeddings(texts, settings=settings)
    return {"embeddings": embeddings}
```

### Backward Compatibility Functions:
```python
# For gradual migration - these maintain old interface
def _get_client() -> APIClient:
    """DEPRECATED: Backward compatibility."""
    settings = get_settings()
    wx_client = WatsonXClient.get_instance(settings)
    return wx_client.get_client()

def get_embeddings_legacy(texts):
    """DEPRECATED: Use get_embeddings(texts, settings=settings) instead."""
    return get_embeddings(texts, settings=get_settings())
```

## Benefits

1. **Test Isolation**: Settings can be mocked/changed per test
2. **No Import-Time Execution**: Settings only accessed when needed
3. **Explicit Dependencies**: Clear what each component needs
4. **Better Testability**: Easy to inject test settings
5. **FastAPI Best Practices**: Follows recommended patterns

## Summary

### Total Files to Modify: 47 files

#### By Priority:
- **🔴 CRITICAL (9 files)**: Module-level constants that break test isolation
- **🟡 HIGH (8 files)**: FastAPI routes and middleware
- **🟢 MEDIUM (7 files)**: Service classes
- **🔵 LOW (23 files)**: Test files (can be done gradually)

#### Key Changes:
1. **Remove module-level settings access**: No more `CONST = settings.value` at import time
2. **Add settings parameters**: Functions accept `settings: Settings` parameter
3. **Use FastAPI injection**: Routes use `Depends(get_settings)`
4. **Class constructors**: Services accept settings in `__init__`

### The Critical Fix: watsonx.py
The `vectordbs/utils/watsonx.py` file is the most problematic because it has:
- `WATSONX_INSTANCE_ID = settings.wx_project_id` at module level
- `EMBEDDING_MODEL = settings.embedding_model` at module level
- Multiple functions that use these constants

This causes settings to be accessed every time ANY module imports watsonx utils, which breaks test isolation.

### After Migration Benefits:
1. **Perfect Test Isolation**: Each test can have different settings
2. **No Import-Time Execution**: Settings only loaded when needed
3. **Mockable**: Easy to mock settings for specific tests
4. **FastAPI Best Practices**: Proper dependency injection
5. **Explicit Dependencies**: Clear what each component needs

## Notes

- The global `settings` object remains for backward compatibility during migration
- Once all 47 files are migrated, the global `settings = get_settings()` line can be removed from config.py
- Use `get_settings.cache_clear()` in tests to reset settings between tests
- See `vectordbs/utils/watsonx_refactored.py` for complete implementation example
