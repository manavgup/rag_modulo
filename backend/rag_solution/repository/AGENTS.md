# Repository Layer - AI Agent Context

## Overview

The repository layer provides clean data access abstraction over SQLAlchemy. Repositories encapsulate all database operations, allowing services to work with domain objects without SQL knowledge.

## Architectural Principle

**Repositories handle ONLY data access** - no business logic, only CRUD operations and queries.

## Repository Pattern

### Standard Repository Template

```python
from sqlalchemy.orm import Session
from pydantic import UUID4
from rag_solution.models.my_model import MyModel

class MyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, entity: MyModel) -> MyModel:
        """Create new entity."""
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get(self, id: UUID4) -> MyModel | None:
        """Get entity by ID."""
        return self.db.query(MyModel).filter(MyModel.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[MyModel]:
        """Get all entities with pagination."""
        return self.db.query(MyModel).offset(skip).limit(limit).all()

    def update(self, entity: MyModel) -> MyModel:
        """Update existing entity."""
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, id: UUID4) -> bool:
        """Delete entity by ID."""
        entity = self.get(id)
        if entity:
            self.db.delete(entity)
            self.db.commit()
            return True
        return False

    def find_by_field(self, field_value: str) -> list[MyModel]:
        """Custom query method."""
        return self.db.query(MyModel).filter(
            MyModel.some_field == field_value
        ).all()
```

## Key Repositories

### CollectionRepository
- Collection CRUD operations
- User access queries
- Status filtering

### FileRepository
- File CRUD operations
- Collection file queries
- Status tracking

### ConversationRepository
- Session management
- Message persistence
- User conversation queries

### UserCollectionRepository
- User-collection relationship queries
- Permission management
- N+1 query optimization with `joinedload()`

## Best Practices

### 1. Use Eager Loading to Avoid N+1 Queries
```python
from sqlalchemy.orm import joinedload

def get_with_relationships(self, id: UUID4) -> MyModel | None:
    return (
        self.db.query(MyModel)
        .options(joinedload(MyModel.related_items))
        .filter(MyModel.id == id)
        .first()
    )
```

### 2. Return Domain Objects, Not Dictionaries
```python
# ✅ GOOD
def get(self, id: UUID4) -> MyModel | None:
    return self.db.query(MyModel).filter(MyModel.id == id).first()

# ❌ BAD
def get(self, id: UUID4) -> dict | None:
    entity = self.db.query(MyModel).filter(MyModel.id == id).first()
    return entity.__dict__ if entity else None
```

### 3. No Business Logic in Repositories
```python
# ❌ BAD - business logic in repository
def get_active_items(self):
    items = self.db.query(Item).all()
    return [item for item in items if item.is_active and item.count > 0]

# ✅ GOOD - just query, business logic in service
def get_all(self):
    return self.db.query(Item).all()
```

### 4. Handle Transactions at Service Level
```python
# Repository just performs operation
def create(self, entity: MyModel) -> MyModel:
    self.db.add(entity)
    self.db.commit()  # Commit here for simple operations
    self.db.refresh(entity)
    return entity

# Service orchestrates multiple operations
def complex_operation(self):
    try:
        entity1 = self.repo1.create(data1)
        entity2 = self.repo2.create(data2)
        self.db.commit()  # Commit both together
    except Exception:
        self.db.rollback()
        raise
```

## Common Patterns

### Pagination
```python
def get_paginated(
    self,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[MyModel], int]:
    query = self.db.query(MyModel)
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return items, total
```

### Filtering
```python
def find_by_criteria(
    self,
    status: str | None = None,
    user_id: UUID4 | None = None
) -> list[MyModel]:
    query = self.db.query(MyModel)

    if status:
        query = query.filter(MyModel.status == status)

    if user_id:
        query = query.filter(MyModel.user_id == user_id)

    return query.all()
```

### Exists Check
```python
def exists(self, id: UUID4) -> bool:
    return self.db.query(MyModel).filter(MyModel.id == id).first() is not None
```

## Related Documentation

- Models: `../models/AGENTS.md`
- Services: `../services/AGENTS.md`
