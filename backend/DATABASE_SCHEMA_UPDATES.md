# Database Schema Updates

## Overview

This project uses **SQLAlchemy's declarative approach** for database schema management, not traditional migration tools like Alembic.

## How Schema Changes Work

### Automatic Table Creation

When the application starts (`main.py:126`), it calls:

```python
Base.metadata.create_all(bind=engine)
```

This automatically creates all tables defined in SQLAlchemy models that:

1. Are registered with `Base` (inherit from `Base = declarative_base()`)
2. Are imported in `rag_solution/models/__init__.py`

### Adding New Tables

To add a new table:

1. **Create the model** in `rag_solution/models/{model_name}.py`

   ```python
   from rag_solution.file_management.database import Base
   from sqlalchemy import Column, String, UUID

   class MyNewModel(Base):
       __tablename__ = "my_new_table"
       id = Column(UUID, primary_key=True)
       name = Column(String, nullable=False)
   ```

2. **Import in models/**init**.py**

   ```python
   from rag_solution.models.my_new_model import MyNewModel

   __all__ = [
       # ... existing models
       "MyNewModel",
   ]
   ```

3. **Restart the application** - table will be auto-created

### Modifying Existing Tables

**⚠️ IMPORTANT**: SQLAlchemy's `create_all()` does **NOT** modify existing tables. It only creates new tables that don't exist.

To modify existing tables (add columns, change types, etc.):

#### Option 1: Development/Testing (Recommended)

For local development or testing environments:

1. **Drop the database** and recreate it:

   ```bash
   # Using Docker
   docker compose down -v
   docker compose up -d postgres

   # Using local PostgreSQL
   psql -U postgres -c "DROP DATABASE rag_modulo_db;"
   psql -U postgres -c "CREATE DATABASE rag_modulo_db;"
   ```

2. **Restart the application** - all tables will be recreated with new schema

#### Option 2: Production (Manual SQL)

For production environments with existing data:

1. **Write SQL migration script**:

   ```sql
   -- Example: Add column to existing table
   ALTER TABLE voices ADD COLUMN new_field VARCHAR(255);

   -- Example: Modify column type
   ALTER TABLE voices ALTER COLUMN status TYPE VARCHAR(50);
   ```

2. **Apply manually** using psql or database admin tools

3. **Update the SQLAlchemy model** to match the new schema

4. **Test thoroughly** before deploying

### Best Practices

1. **Development**: Use Docker volumes for database persistence during development

   ```bash
   docker compose down    # Stop containers but keep data
   docker compose down -v # Stop containers AND delete data (fresh start)
   ```

2. **Production**:
   - Test schema changes in staging environment first
   - Back up database before making changes
   - Consider downtime requirements for large migrations
   - Document all manual SQL migrations

3. **CI/CD**:
   - Integration tests create fresh databases automatically
   - No manual migration scripts needed for tests

## Custom Voice Feature Schema

### Voices Table

The `voices` table was added in this update:

```python
class Voice(Base):
    __tablename__ = "voices"

    voice_id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    gender = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="uploading", index=True)
    provider_voice_id = Column(String(255))
    provider_name = Column(String(50))
    sample_file_url = Column(String(500), nullable=False)
    sample_file_size = Column(Integer)
    quality_score = Column(Integer)
    error_message = Column(Text)
    times_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime)
```

**Deployment**:

- ✅ **Development/Testing**: Table auto-created on next application start
- ✅ **Production**: Table auto-created if database is fresh
- ⚠️ **Existing Production**: If database already exists, table will be auto-created (CREATE TABLE IF NOT EXISTS)

No manual migration needed - table will be created automatically when application starts.

## Future: Migration to Alembic

If the project grows and needs more sophisticated migration management, consider migrating to Alembic:

1. Initialize Alembic
2. Generate initial migration from existing models
3. Use `alembic revision --autogenerate` for future changes
4. Apply with `alembic upgrade head`

Benefits:

- Version-controlled schema changes
- Rollback capability
- Easier production deployments
- Better collaboration on schema changes

Trade-offs:

- More complexity
- Requires migration scripts in CI/CD
- Extra setup/maintenance overhead
