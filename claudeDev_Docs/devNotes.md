# Development Notes

## **CRITICAL DEVELOPMENT REQUIREMENTS** 🚨

### **Core Technology Stack**
- **RAG Solution**: Highly configurable RAG solution in Python using IBM watsonx library
- **NO Dependencies**: NO dependence on langchain, Huggingface, or similar frameworks
- **Authentication**: IBM ID provider over OAuth, all authentication handled via backend
- **Containerization**: Application runs in multiple containers (see docker-compose.yml)
- **Architecture**: Backend implements repository pattern with service layer

### **Application Structure**
- **Backend Code**: Located in `./backend` directory
- **Frontend Code**: Located in `./webui` directory
- **Frontend Framework**: IBM Carbon React framework
- **Packaging**: Entire program packaged in separate containers

### **Python Development Standards**
- **Code Quality**: Write all code as an expert Python programmer with best practices
- **Type Checking**: Strong type checking throughout the codebase
- **Pydantic 2.0**: Use Pydantic 2.0 for data validation and serialization
- **Documentation**: Comprehensive docstrings for all classes, methods, and functions

## **DEVELOPMENT GUIDELINES** 📋

### **1. Design Patterns**
- **Factory Pattern**: Create different types of components (e.g., different vector database implementations)
- **Singleton Pattern**: Ensure single instances where appropriate (e.g., configuration managers)
- **Strategy Pattern**: Implement different strategies for various operations (e.g., chunking strategies, search strategies)
- **Observer Pattern**: Implement event-driven architectures where needed
- **Dependency Injection**: Use dependency injection to decouple components

### **2. Pydantic 2.0 Requirements**
- **Data Validation**: Use Pydantic 2.0 for all data validation and serialization
- **Schema Definition**: Define input, output, and database schemas using Pydantic models
- **Advanced Features**: Use advanced Pydantic features like:
  - `Field` for constraints and metadata
  - `Config` for model configuration
  - `model_validator` for custom validation logic
  - `model_dump` for serialization control

### **3. Modular Architecture**
- **Code Organization**: Organize code into logical modules/packages:
  - `models`: Database models and entities
  - `services`: Business logic and orchestration
  - `repositories`: Data access layer
  - `schemas`: Pydantic schemas and DTOs
  - `config`: Configuration management
  - `utils`: Utility functions and helpers
- **Dependency Injection**: Use dependency injection to decouple components
- **DRY Principle**: Do not repeat yourself - create reusable components

### **4. Error Handling**
- **Custom Exceptions**: Implement custom exception hierarchy for domain-specific errors
- **Pydantic Validation**: Use Pydantic's validation errors for meaningful feedback
- **Structured Logging**: Comprehensive logging with proper error context
- **Graceful Degradation**: Handle errors gracefully with fallback mechanisms

### **5. Testing Requirements**
- **Unit Testing**: Write unit tests for all major components using pytest
- **Mocking**: Use pytest-mock for mocking dependencies
- **Test Coverage**: Aim for comprehensive test coverage
- **Test Organization**: Organize tests to mirror the main code structure

### **6. Logging Standards**
- **Python Logging**: Use Python's logging module for all logging
- **Structured Logging**: Log important events (errors, warnings, info) with context
- **Output Configuration**: Configure logging to output to both console and file
- **Log Levels**: Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### **7. Documentation Standards**
- **Docstrings**: Add comprehensive docstrings to all classes, methods, and functions
- **Type Hints**: Use type hints (str, int, List, Optional, etc.) for clarity
- **API Documentation**: Maintain up-to-date API documentation
- **Code Comments**: Add inline comments for complex logic

### **8. Optional Features**
- **Asynchronous Operations**: Use asyncio for asynchronous operations where beneficial
- **External Integrations**: Integrate with external APIs and databases (SQLAlchemy, httpx)
- **Performance Optimization**: Implement caching, connection pooling, and other optimizations

## Architecture Patterns

### Repository Pattern
The repository pattern is used to abstract data access logic from business logic. Each entity has its own repository that handles CRUD operations.

**Example Implementation**:
```python
class CollectionRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, collection: Collection) -> Collection:
        self.db.add(collection)
        self.db.commit()
        self.db.refresh(collection)
        return collection
    
    def get_by_id(self, collection_id: int) -> Optional[Collection]:
        return self.db.query(Collection).filter(Collection.id == collection_id).first()
```

### Service Layer
The service layer contains business logic and orchestrates operations between repositories and external services.

**Example Implementation**:
```python
class CollectionService:
    def __init__(self, collection_repo: CollectionRepository, vector_store: VectorStore):
        self.collection_repo = collection_repo
        self.vector_store = vector_store
    
    def create_collection(self, collection_data: CollectionCreate) -> Collection:
        # Business logic for collection creation
        collection = Collection(**collection_data.dict())
        return self.collection_repo.create(collection)
```

### Dependency Injection
Services receive their dependencies through constructor injection, making them easily testable and decoupled.

**Example Implementation**:
```python
def get_collection_service(
    db: Session = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store)
) -> CollectionService:
    collection_repo = CollectionRepository(db)
    return CollectionService(collection_repo, vector_store)
```

### Factory Pattern
The factory pattern is used to create different types of components, such as vector database implementations.

**Example Implementation**:
```python
class VectorStoreFactory:
    @staticmethod
    def create_vector_store(store_type: str, config: dict) -> VectorStore:
        if store_type == "milvus":
            return MilvusStore(config)
        elif store_type == "elasticsearch":
            return ElasticsearchStore(config)
        elif store_type == "pinecone":
            return PineconeStore(config)
        else:
            raise ValueError(f"Unsupported vector store type: {store_type}")
```

### Strategy Pattern
The strategy pattern is used to implement different strategies for various operations, such as chunking strategies.

**Example Implementation**:
```python
class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk_document(self, document: Document) -> List[Chunk]:
        pass

class SimpleChunkingStrategy(ChunkingStrategy):
    def chunk_document(self, document: Document) -> List[Chunk]:
        # Simple chunking implementation
        pass

class SemanticChunkingStrategy(ChunkingStrategy):
    def chunk_document(self, document: Document) -> List[Chunk]:
        # Semantic chunking implementation
        pass
```

## Code Quality Standards

### Type Hints
All functions, methods, and variables should have proper type hints for clarity and IDE support.

**Example**:
```python
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

def process_documents(
    documents: List[Document],
    chunk_size: int = 1000,
    strategy: Optional[str] = None
) -> List[Chunk]:
    # Function implementation
    pass
```

### Pydantic 2.0
Use Pydantic 2.0 for data validation and serialization with modern features.

**Example**:
```python
from pydantic import BaseModel, Field, ConfigDict

class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_public: bool = Field(default=False)
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True
    )
    
    @model_validator(mode='before')
    @classmethod
    def validate_name(cls, values):
        if 'name' in values and values['name'].strip() == '':
            raise ValueError('Name cannot be empty')
        return values
```

### Docstrings
All classes, methods, and functions should have comprehensive docstrings following Google style.

**Example**:
```python
def create_collection(
    collection_data: CollectionCreate,
    user_id: int,
    db: Session
) -> Collection:
    """Create a new collection for the specified user.
    
    Args:
        collection_data: The collection data to create
        user_id: The ID of the user creating the collection
        db: Database session for the operation
        
    Returns:
        The created collection instance
        
    Raises:
        ValidationError: If the collection data is invalid
        DatabaseError: If the database operation fails
    """
    # Implementation
    pass
```

## Error Handling

### Custom Exception Hierarchy
Implement a custom exception hierarchy for domain-specific errors.

**Example**:
```python
class RAGModuloError(Exception):
    """Base exception for RAG Modulo application."""
    pass

class ValidationError(RAGModuloError):
    """Raised when data validation fails."""
    pass

class AuthenticationError(RAGModuloError):
    """Raised when authentication fails."""
    pass

class DatabaseError(RAGModuloError):
    """Raised when database operations fail."""
    pass

class VectorStoreError(RAGModuloError):
    """Raised when vector store operations fail."""
    pass
```

### Error Response Format
Use consistent error response format across the API.

**Example**:
```python
from fastapi import HTTPException
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

def raise_http_error(status_code: int, message: str, details: Optional[Dict] = None):
    raise HTTPException(
        status_code=status_code,
        detail=ErrorResponse(
            error=status_code,
            message=message,
            details=details
        ).dict()
    )
```

### Logging Strategy
Implement comprehensive logging with proper context and error tracking.

**Example**:
```python
import logging
from contextvars import ContextVar
from typing import Optional

# Context variables for request tracking
request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id: ContextVar[Optional[int]] = ContextVar('user_id', default=None)

class ContextualFormatter(logging.Formatter):
    def format(self, record):
        record.request_id = request_id.get()
        record.user_id = user_id.get()
        return super().format(record)

# Usage in services
logger = logging.getLogger(__name__)

def process_document(document_id: int):
    logger.info(f"Processing document {document_id}", extra={
        'document_id': document_id,
        'operation': 'process_document'
    })
    try:
        # Processing logic
        pass
    except Exception as e:
        logger.error(f"Failed to process document {document_id}: {str(e)}", 
                    extra={'document_id': document_id, 'error': str(e)})
        raise
```

## Testing Strategy

### Unit Testing
Write comprehensive unit tests for all major components using pytest.

**Example**:
```python
import pytest
from unittest.mock import Mock, patch
from rag_solution.services.collection_service import CollectionService
from rag_solution.schemas.collection_schema import CollectionCreate

class TestCollectionService:
    def setup_method(self):
        self.mock_repo = Mock()
        self.mock_vector_store = Mock()
        self.service = CollectionService(self.mock_repo, self.mock_vector_store)
    
    def test_create_collection_success(self):
        # Arrange
        collection_data = CollectionCreate(name="Test Collection", description="Test")
        expected_collection = Mock()
        self.mock_repo.create.return_value = expected_collection
        
        # Act
        result = self.service.create_collection(collection_data)
        
        # Assert
        assert result == expected_collection
        self.mock_repo.create.assert_called_once()
    
    def test_create_collection_validation_error(self):
        # Arrange
        collection_data = CollectionCreate(name="", description="Test")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Name cannot be empty"):
            self.service.create_collection(collection_data)
```

### Integration Testing
Test the integration between different components and external services.

**Example**:
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rag_solution.main import app
from rag_solution.database import get_db

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_create_collection_endpoint():
    response = client.post(
        "/api/collections/",
        json={"name": "Test Collection", "description": "Test"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Collection"
```

### Test Fixtures
Use pytest fixtures for common test setup and teardown.

**Example**:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rag_solution.database import Base

@pytest.fixture(scope="session")
def engine():
    engine = create_engine("sqlite:///./test.db")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()
```

## Database Design

### SQLAlchemy 2.0
Use SQLAlchemy 2.0 with modern type annotations and relationship definitions.

**Example**:
```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from rag_solution.database import Base

class Collection(Base):
    __tablename__ = "collections"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship("User", back_populates="collections")
    files: Mapped[List["File"]] = relationship("File", back_populates="collection")
```

### Database Migrations
Use Alembic for database schema migrations and version control.

**Example**:
```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from alembic import context
from rag_solution.models import Base

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        
        with context.begin_transaction():
            context.run_migrations()
```

## Common Solutions

### Authentication and Authorization
Implement OIDC authentication with JWT tokens and role-based access control.

**Example**:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from rag_solution.core.config import settings

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user
```

### Document Processing
Implement multi-format document processing with intelligent chunking.

**Example**:
```python
from abc import ABC, abstractmethod
from typing import List, BinaryIO
from rag_solution.schemas.document_schema import Document, Chunk

class DocumentProcessor(ABC):
    @abstractmethod
    def can_process(self, file_extension: str) -> bool:
        pass
    
    @abstractmethod
    def process(self, file: BinaryIO) -> Document:
        pass

class PDFProcessor(DocumentProcessor):
    def can_process(self, file_extension: str) -> bool:
        return file_extension.lower() == '.pdf'
    
    def process(self, file: BinaryIO) -> Document:
        # PDF processing logic
        pass

class DocumentProcessorFactory:
    def __init__(self):
        self.processors: List[DocumentProcessor] = [
            PDFProcessor(),
            DocxProcessor(),
            TxtProcessor(),
            XlsxProcessor()
        ]
    
    def get_processor(self, file_extension: str) -> DocumentProcessor:
        for processor in self.processors:
            if processor.can_process(file_extension):
                return processor
        raise ValueError(f"No processor found for file type: {file_extension}")
```

### Vector Database Integration
Implement abstract interface for multiple vector database backends.

**Example**:
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from rag_solution.schemas.vector_schema import Embedding, SearchResult

class VectorStore(ABC):
    @abstractmethod
    async def store_embeddings(self, embeddings: List[Embedding]) -> bool:
        pass
    
    @abstractmethod
    async def search(self, query_embedding: List[float], limit: int = 10) -> List[SearchResult]:
        pass
    
    @abstractmethod
    async def delete_embeddings(self, ids: List[str]) -> bool:
        pass

class MilvusStore(VectorStore):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Initialize Milvus connection
    
    async def store_embeddings(self, embeddings: List[Embedding]) -> bool:
        # Milvus-specific implementation
        pass
    
    async def search(self, query_embedding: List[float], limit: int = 10) -> List[SearchResult]:
        # Milvus-specific search implementation
        pass
```

### API Design
Design RESTful APIs with proper error handling and validation.

**Example**:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from rag_solution.schemas.collection_schema import CollectionCreate, CollectionResponse
from rag_solution.services.collection_service import CollectionService
from rag_solution.core.auth import get_current_user

router = APIRouter(prefix="/api/collections", tags=["collections"])

@router.post("/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection_data: CollectionCreate,
    current_user = Depends(get_current_user),
    collection_service: CollectionService = Depends(get_collection_service)
):
    """Create a new collection for the current user."""
    try:
        collection = collection_service.create_collection(
            collection_data, 
            current_user.id
        )
        return CollectionResponse.from_orm(collection)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/", response_model=List[CollectionResponse])
async def list_collections(
    current_user = Depends(get_current_user),
    collection_service: CollectionService = Depends(get_collection_service)
):
    """List all collections for the current user."""
    collections = collection_service.get_user_collections(current_user.id)
    return [CollectionResponse.from_orm(c) for c in collections]
```

## Performance Optimization

### Caching Strategy
Implement multi-layer caching for improved performance.

**Example**:
```python
from functools import lru_cache
from typing import Optional
import redis
from rag_solution.core.config import settings

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.redis_url)
    
    async def get(self, key: str) -> Optional[str]:
        return self.redis_client.get(key)
    
    async def set(self, key: str, value: str, expire: int = 3600):
        self.redis_client.setex(key, expire, value)
    
    async def delete(self, key: str):
        self.redis_client.delete(key)

# In-memory caching for frequently accessed data
@lru_cache(maxsize=128)
def get_user_permissions(user_id: int) -> List[str]:
    # Cache user permissions in memory
    pass
```

### Database Optimization
Optimize database queries and implement connection pooling.

**Example**:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Database engine with connection pooling
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Optimized queries with proper indexing
def get_collections_with_files(user_id: int, db: Session) -> List[Collection]:
    return db.query(Collection)\
        .options(joinedload(Collection.files))\
        .filter(Collection.user_id == user_id)\
        .all()
```

## Security Considerations

### Input Validation
Implement comprehensive input validation using Pydantic and custom validators.

**Example**:
```python
from pydantic import BaseModel, Field, validator
import re

class UserInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=8)
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v
```

### SQL Injection Prevention
Use parameterized queries and ORM methods to prevent SQL injection.

**Example**:
```python
# Safe - using ORM
def get_user_by_email(email: str, db: Session) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

# Safe - using parameterized queries
def get_user_by_email_raw(email: str, db: Session) -> Optional[User]:
    result = db.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": email}
    )
    return result.fetchone()
```

## Deployment and DevOps

### Docker Configuration
Use multi-stage Docker builds for optimized production images.

**Example**:
```dockerfile
# Backend Dockerfile
FROM python:3.12-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration
Use environment variables and configuration files for different environments.

**Example**:
```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "RAG Modulo"
    debug: bool = False
    database_url: str
    redis_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

### Health Checks
Implement comprehensive health checks for all services.

**Example**:
```python
from fastapi import APIRouter
from rag_solution.database import get_db
from rag_solution.core.vector_store import get_vector_store

router = APIRouter()

@router.get("/health")
async def health_check():
    """Comprehensive health check for all services."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Database health check
    try:
        db = next(get_db())
        db.execute("SELECT 1")
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Vector store health check
    try:
        vector_store = get_vector_store()
        await vector_store.health_check()
        health_status["services"]["vector_store"] = "healthy"
    except Exception as e:
        health_status["services"]["vector_store"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status
```

## Troubleshooting Common Issues

### Authentication Issues
- **JWT Token Expired**: Check token expiration and refresh logic
- **OIDC Configuration**: Verify OIDC provider settings and endpoints
- **CORS Issues**: Ensure proper CORS configuration for frontend-backend communication

### Database Connection Issues
- **Connection Pool Exhausted**: Increase pool size and implement connection recycling
- **Transaction Deadlocks**: Implement proper transaction isolation and retry logic
- **Migration Failures**: Use Alembic for safe database migrations

### Vector Database Issues
- **Connection Timeouts**: Implement connection pooling and retry mechanisms
- **Index Corruption**: Regular index maintenance and backup procedures
- **Performance Degradation**: Monitor query performance and optimize indexing

### Frontend Issues
- **Build Failures**: Check Node.js version and dependency compatibility
- **Runtime Errors**: Implement proper error boundaries and error logging
- **Performance Issues**: Use React DevTools and performance monitoring

## Best Practices Summary

1. **Follow Design Patterns**: Use established patterns for maintainable code
2. **Strong Typing**: Implement comprehensive type hints throughout
3. **Pydantic 2.0**: Use modern Pydantic features for validation
4. **Comprehensive Testing**: Write tests for all major functionality
5. **Error Handling**: Implement robust error handling and logging
6. **Security First**: Validate all inputs and prevent common vulnerabilities
7. **Performance Monitoring**: Monitor and optimize performance continuously
8. **Documentation**: Maintain up-to-date documentation and code comments
9. **Code Review**: Implement thorough code review processes
10. **Continuous Integration**: Use automated testing and deployment pipelines