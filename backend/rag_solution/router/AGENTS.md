# Router Layer - AI Agent Context

## Overview

The router layer contains FastAPI endpoint handlers. Routers define HTTP endpoints, handle request/response serialization, and delegate business logic to services.

## Architectural Principle

**Routers should be thin** - minimal logic, maximum delegation to services.

## Router Structure

### Typical Router Pattern

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.config import get_settings
from rag_solution.file_management.database import get_db
from rag_solution.schemas.my_schema import MyInput, MyOutput
from rag_solution.services.my_service import MyService

router = APIRouter()

def get_service(db: Session = Depends(get_db)) -> MyService:
    return MyService(db, get_settings())

@router.post("/items", response_model=MyOutput, status_code=201)
async def create_item(
    input: MyInput,
    service: MyService = Depends(get_service)
) -> MyOutput:
    """Create a new item."""
    try:
        return service.create_item(input)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/items/{item_id}", response_model=MyOutput)
async def get_item(
    item_id: UUID4,
    service: MyService = Depends(get_service)
) -> MyOutput:
    """Retrieve item by ID."""
    return service.get_item(item_id)
```

## Key Routers

### search_router.py
- `POST /api/v1/search`: Execute RAG search

### collection_router.py
- `POST /api/v1/collections`: Create collection
- `GET /api/v1/collections`: List collections
- `GET /api/v1/collections/{id}`: Get collection
- `PUT /api/v1/collections/{id}`: Update collection
- `DELETE /api/v1/collections/{id}`: Delete collection

### conversation_router.py
- `POST /api/v1/conversations`: Create session
- `GET /api/v1/conversations`: List sessions
- `POST /api/v1/conversations/{id}/messages`: Add message
- `GET /api/v1/conversations/{id}/messages`: Get messages

### websocket_router.py
- `WS /ws/chat`: WebSocket for real-time messaging

### dashboard_router.py
- `GET /api/v1/dashboard/stats`: Get system statistics
- `GET /api/v1/dashboard/activity`: Get recent activity

## Best Practices

### 1. Use Dependency Injection
```python
# ✅ GOOD - Service injected
@router.get("/items")
async def get_items(service: MyService = Depends(get_service)):
    return service.get_items()

# ❌ BAD - Service created in handler
@router.get("/items")
async def get_items(db: Session = Depends(get_db)):
    service = MyService(db, get_settings())
    return service.get_items()
```

### 2. Handle Errors Consistently
```python
@router.post("/items")
async def create_item(input: MyInput, service: MyService = Depends(get_service)):
    try:
        return service.create_item(input)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
```

### 3. Use Response Models
```python
@router.get("/items", response_model=list[ItemResponse])
async def list_items(service: MyService = Depends(get_service)):
    return service.list_items()
```

### 4. Document Endpoints
```python
@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=201,
    summary="Create new item",
    description="Creates a new item with the provided data",
    responses={
        201: {"description": "Item created successfully"},
        400: {"description": "Invalid input"},
        404: {"description": "Collection not found"}
    }
)
async def create_item(input: ItemCreate, service: MyService = Depends(get_service)):
    """Create a new item."""
    return service.create_item(input)
```

### 5. Use Path/Query Parameters Appropriately
```python
# Path parameter for resource ID
@router.get("/items/{item_id}")
async def get_item(item_id: UUID4):
    ...

# Query parameters for filtering
@router.get("/items")
async def list_items(
    skip: int = 0,
    limit: int = 100,
    status: str | None = None
):
    ...
```

## Common Pitfalls

### ❌ Don't Put Business Logic in Routers
```python
# BAD
@router.post("/items")
async def create_item(input: ItemCreate, db: Session = Depends(get_db)):
    # Business logic in router - DON'T DO THIS
    if db.query(Item).filter(Item.name == input.name).first():
        raise HTTPException(400, "Item exists")
    item = Item(**input.dict())
    db.add(item)
    db.commit()
    return item
```

### ❌ Don't Access Repositories Directly
```python
# BAD
@router.get("/items/{item_id}")
async def get_item(item_id: UUID4, db: Session = Depends(get_db)):
    repo = ItemRepository(db)
    return repo.get(item_id)  # Skip service layer - DON'T DO THIS
```

## Router Registration

Routers are registered in `backend/main.py`:

```python
from rag_solution.router.search_router import router as search_router

app.include_router(
    search_router,
    prefix="/api/v1/search",
    tags=["search"]
)
```

## Testing Routers

```python
from fastapi.testclient import TestClient

@pytest.mark.api
def test_create_item(client: TestClient):
    response = client.post(
        "/api/v1/items",
        json={"name": "test"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "test"
```

## Related Documentation

- Services: `../services/AGENTS.md`
- Schemas: `../schemas/AGENTS.md`
