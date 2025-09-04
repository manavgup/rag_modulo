# RAG Modulo

RAG Modulo is a robust, customizable Retrieval-Augmented Generation (RAG) solution that supports a wide variety of vector databases, embedding models, and document formats. The solution is designed to be flexible and not dependent on popular RAG frameworks like LangChain or LlamaIndex, allowing for greater customization and control.

## 🚨 Current Project Status: WORK IN PROGRESS

**Status**: The project has a solid architectural foundation with comprehensive implementation, but core functionality is untested due to authentication issues. This is a **work-in-progress** project that needs systematic testing and validation before production readiness.

### ✅ What's Working
- **Infrastructure**: All Docker containers running (PostgreSQL, Milvus, MLFlow, MinIO)
- **Basic Health**: Backend health endpoint responding
- **Architecture**: Solid, production-ready architecture implemented
- **Code Structure**: Comprehensive implementation across all components
- **Container Setup**: Full Docker Compose infrastructure with GHCR images

### ❌ What's NOT Working
- **Authentication System**: OIDC authentication broken - blocks all testing
- **Functionality Testing**: Cannot verify any features actually work
- **Local Development**: Local environment has dependency issues
- **Testing Framework**: pytest not available for testing

### 📊 Realistic Assessment
- **Infrastructure**: 90% complete
- **Backend Structure**: 70% complete
- **Backend Functionality**: 30% complete (untested)
- **Frontend**: 40% complete (structure only)
- **Testing**: 10% complete (framework missing)
- **Integration**: 20% complete (untested)

## Table of Contents

- [Features](#features)
- [Document Processing Flow](#document-processing-flow)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Testing](#testing)
- [CI/CD](#cicd)
- [Contributing](#contributing)
- [License](#license)

## Features

### Architecture
- Service-based architecture with clean separation of concerns
- Repository pattern for database operations
- Provider abstraction for LLM integration
- Dependency injection for better testability
- Asynchronous API for efficient operations

### Data Processing
- Support for multiple vector databases (Elasticsearch, Milvus, Pinecone, Weaviate, ChromaDB)
- Flexible document processing for various formats (PDF, TXT, DOCX, XLSX)
- Customizable chunking strategies
- Configurable embedding models
- Separation of vector storage and metadata storage

### LLM Integration
- Multiple LLM provider support (WatsonX, OpenAI, Anthropic)
- Runtime provider configuration
- Template-based prompt management
- Error handling and recovery
- Concurrent request handling

### Testing & Quality
- Comprehensive test suite with:
  - Unit tests for components
  - Integration tests for flows
  - Performance tests for scalability
  - Service-specific test suites
- Continuous Integration/Deployment
- Code quality checks
- Performance monitoring
- Security auditing

## Document Processing Flow

The following diagram illustrates how documents are processed in our RAG solution:

```mermaid
graph TD
    A[User Uploads Document] --> B[DocumentProcessor]
    B --> C{Document Type?}
    C -->|PDF| D[PdfProcessor]
    C -->|TXT| E[TxtProcessor]
    C -->|DOCX| F[WordProcessor]
    C -->|XLSX| G[ExcelProcessor]
    D --> H[Extract Text, Tables, Images]
    E --> I[Process Text]
    F --> J[Extract Paragraphs]
    G --> K[Extract Sheets and Data]
    H --> L[Chunking]
    I --> L
    J --> L
    K --> L
    L --> M[Get Embeddings]
    M --> N{Store Data}
    N -->|Vector Data| O[VectorStore]
    O --> P{Vector DB Type}
    P -->|Milvus| Q[MilvusStore]
    P -->|Elasticsearch| R[ElasticsearchStore]
    P -->|Pinecone| S[PineconeStore]
    P -->|Weaviate| T[WeaviateStore]
    P -->|ChromaDB| U[ChromaDBStore]
    N -->|Metadata| V[PostgreSQL]
    V --> W[Repository Layer]
    W --> X[Service Layer]
```

Explanation of the document processing flow:

1. A user uploads a document to the system.
2. The DocumentProcessor determines the type of document and routes it to the appropriate processor (PdfProcessor, TxtProcessor, WordProcessor, or ExcelProcessor).
3. Each processor extracts the relevant content from the document.
4. The extracted content goes through a chunking process to break it into manageable pieces.
5. Embeddings are generated for the chunked content.
6. The data is then stored in two places:
   - Vector data (embeddings) are stored in the VectorStore, which can be one of several types (Milvus, Elasticsearch, Pinecone, Weaviate, or ChromaDB).
   - Metadata is stored in PostgreSQL, accessed through the Repository Layer and Service Layer.

This architecture allows for flexibility in choosing vector databases and ensures efficient storage and retrieval of both vector data and metadata.

## Prerequisites

- Python 3.12+ (required for backend)
- Node.js 18+ (required for frontend)
- Docker and Docker Compose
- Poetry (for Python dependency management)
- npm (for frontend dependency management)

## Installation

### Quick Start (Recommended)

1. Clone the repository:
   ```sh
   git clone https://github.com/manavgup/rag-modulo.git
   cd rag-modulo
   ```

2. Set up your environment variables:
   ```sh
   cp env.example .env
   # Edit .env with your specific configuration
   ```

3. Start the application with pre-built images:
   ```sh
   make run-ghcr
   ```

### Development Setup

1. **Backend Setup**:
   ```sh
   cd backend
   poetry install --with dev
   poetry shell
   ```

2. **Frontend Setup**:
   ```sh
   cd webui
   npm install
   ```

3. **Build and Run Locally**:
   ```sh
   make build-all
   make run-app
   ```

### Environment Configuration

The system requires several environment variables. See `env.example` for the complete list. Key variables include:

- **Database**: `COLLECTIONDB_*` variables for PostgreSQL
- **Vector DB**: `VECTOR_DB`, `MILVUS_*` variables
- **LLM Providers**: `WATSONX_*`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
- **Authentication**: `IBM_CLIENT_ID`, `IBM_CLIENT_SECRET`, `OIDC_*` variables

## Usage

### Running the Application

1. **Using Pre-built Images (Recommended)**:
   ```sh
   make run-ghcr
   ```

2. **Building and Running Locally**:
   ```sh
   make run-app
   ```

3. **Access Points**:
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8000
   - **MLFlow**: http://localhost:5001
   - **MinIO Console**: http://localhost:9001

### Available Make Commands

- `make run-ghcr` - Run with pre-built GitHub Container Registry images
- `make run-app` - Build and run with local images
- `make run-services` - Start only infrastructure services
- `make stop-containers` - Stop all containers
- `make logs` - View container logs
- `make clean` - Clean up containers and volumes

### Development Commands

- `make lint` - Run code quality checks
- `make test` - Run tests (requires testfile parameter)
- `make build-all` - Build all container images
- `make pull-ghcr-images` - Pull latest images from GHCR

### CI/Development Debugging Scripts

- `scripts/test_ci_quick.sh` - Quick CI environment validation
- `scripts/test_ci_environment.sh` - Comprehensive CI simulation
- `scripts/validate_ci_fixes.py` - Validate CI-related code changes

## Project Structure

```plaintext
rag_modulo/
├── .github/workflows/ci.yml   # GitHub Actions workflow for build/test/publish
├── backend                    # Python backend application
│   ├── auth/                  # Authentication code (e.g. OIDC)
│   ├── core/                  # Config, exceptions, middleware
│   ├── rag_solution/          # Main application code
│   │   ├── data_ingestion/    # Data ingestion modules
│   │   ├── docs/             # Documentation files
│   │   ├── evaluation/       # Evaluation modules
│   │   ├── generation/       # Text generation modules
│   │   │   └── providers/    # LLM provider implementations
│   │   ├── models/          # Data models and schemas
│   │   ├── pipeline/        # RAG pipeline implementation
│   │   ├── query_rewriting/ # Query rewriting modules
│   │   ├── repository/      # Repository layer implementations
│   │   ├── retrieval/       # Data retrieval modules
│   │   ├── router/          # API route handlers
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Service layer implementations
│   ├── tests/               # Test suite
│   │   ├── integration/     # Integration tests
│   │   ├── performance/     # Performance tests
│   │   ├── services/        # Service tests
│   │   └── README.md        # Testing documentation
│   └── vectordbs/           # Vector database interfaces
├── webui/                   # Frontend code
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # Frontend services
│   │   └── config/         # Frontend configuration
├── scripts/                 # Development and debugging scripts
│   ├── test_ci_quick.sh     # Quick CI environment test
│   ├── test_ci_environment.sh # Full CI simulation
│   └── validate_ci_fixes.py # Code validation script
├── docs/                    # Documentation
│   └── fixes/              # Fix documentation
├── .env                     # Environment variables
├── .env.ci                  # CI environment configuration
├── docker-compose-infra.yml # Infrastructure services configuration
├── docker-compose.yml       # Application services configuration
├── Makefile                # Project management commands
├── requirements.txt        # Project dependencies
└── README.md              # Project documentation
```

Key architectural components:

1. Service Layer:
   - Implements business logic
   - Manages transactions
   - Handles dependencies
   - Provides clean interfaces

2. Repository Layer:
   - Data access abstraction
   - Database operations
   - Query optimization
   - Transaction management

3. Provider System:
   - LLM provider abstraction
   - Multiple provider support
   - Configuration management
   - Error handling

4. Test Organization:
   - Unit tests by component
   - Integration tests
   - Performance tests
   - Service-specific tests

## OAuth flow with IBM

The following diagram illustrates the OAuth 2.0 Authorization Code flow used in our application with IBM as the identity provider:

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant IBM_OIDC
    participant Database
    User->>Frontend: Clicks Login
    Frontend->>Backend: GET /api/auth/login
    Backend->>IBM_OIDC: Redirect to Authorization Endpoint
    IBM_OIDC->>User: Present Login Page
    User->>IBM_OIDC: Enter Credentials
    IBM_OIDC->>Backend: Redirect with Authorization Code
    Backend->>IBM_OIDC: POST /token (exchange code for tokens)
    IBM_OIDC-->>Backend: Access Token & ID Token
    Backend->>Backend: Parse ID Token
    Backend->>Database: Get or Create User
    Database-->>Backend: User Data
    Backend->>Backend: Set Session Data
    Backend->>Frontend: Redirect to Dashboard
    Frontend->>Backend: GET /api/auth/session
    Backend-->>Frontend: User Data
    Frontend->>User: Display Authenticated UI
```

## Configuration

The system uses a layered configuration approach with both environment variables and runtime configuration through services.

### Environment Configuration

Basic infrastructure settings:
```bash
# Database Configuration
VECTOR_DB=milvus                 # Vector database type
MILVUS_HOST=localhost           # Vector DB host
MILVUS_PORT=19530              # Vector DB port
DB_HOST=localhost              # PostgreSQL host
DB_PORT=5432                   # PostgreSQL port

# LLM Provider Settings
WATSONX_INSTANCE_ID=your-id    # WatsonX instance ID
WATSONX_APIKEY=your-key        # WatsonX API key
OPENAI_API_KEY=your-key        # OpenAI API key (optional)
ANTHROPIC_API_KEY=your-key     # Anthropic API key (optional)

# Application Settings
EMBEDDING_MODEL=all-minilm-l6-v2  # Default embedding model
DATA_DIR=/path/to/data           # Data directory
```

### Environment Modes

The application supports different operating modes controlled by environment variables:

#### Production Mode (default)
```bash
# All flags false or unset (default)
TESTING=false
SKIP_AUTH=false  
DEVELOPMENT_MODE=false
```
- Full authentication required
- OIDC provider registration enabled
- Production security measures enforced

#### Development/CI Mode
```bash
# Any of these set to true activates development mode
TESTING=true              # Set in CI environments
SKIP_AUTH=true           # Skip authentication entirely
DEVELOPMENT_MODE=true    # Local development without auth
```
- Authentication bypassed (test user automatically set)
- OIDC registration skipped (no external connections)
- All endpoints accessible without credentials
- Ideal for testing and local development

#### Testing with Authentication
For testing scenarios that need partial authentication:
```bash
# Use mock token for testing
Authorization: Bearer mock_token_for_testing
```

**Environment Priority**: Any of `TESTING`, `SKIP_AUTH`, or `DEVELOPMENT_MODE` being `true` will activate development mode.

### Service Configuration

Runtime configuration through services:

1. Provider Configuration:
   ```python
   provider_config = ProviderConfigInput(
       provider="watsonx",
       api_key="${WATSONX_APIKEY}",
       project_id="${WATSONX_INSTANCE_ID}",
       active=True
   )
   config_service.create_provider_config(provider_config)
   ```

2. LLM Parameters:
   ```python
   parameters = LLMParametersInput(
       name="default-params",
       provider="watsonx",
       model_id="granite-13b",
       temperature=0.7,
       max_new_tokens=1000
   )
   parameters_service.create_parameters(parameters)
   ```

3. Template Configuration:
   ```python
   template = PromptTemplateInput(
       name="rag-query",
       provider="watsonx",
       template_type=PromptTemplateType.RAG_QUERY,
       template_format="Context:\n{context}\nQuestion:{question}"
   )
   template_service.create_template(template)
   ```

4. Pipeline Configuration:
   ```python
   pipeline_config = PipelineConfigInput(
       name="default-pipeline",
       provider_id=provider.id,
       llm_parameters_id=parameters.id
   )
   pipeline_service.create_pipeline_config(pipeline_config)
   ```

For detailed configuration options and examples, see:
- [Provider Configuration](backend/rag_solution/docs/provider_configuration.md)
- [Configuration Management](backend/rag_solution/docs/configuration.md)
- [Prompt Templates](backend/rag_solution/docs/prompt_templates.md)

## Testing

⚠️ **Testing Status**: The project has a comprehensive test suite implemented, but testing is currently blocked by authentication issues. The testing framework needs to be set up and authentication fixed before tests can be run.

### Test Framework Status

- **Test Structure**: ✅ Comprehensive test suite implemented
- **Test Categories**: ✅ Unit, integration, performance, and service tests
- **Test Infrastructure**: ❌ pytest not available due to dependency issues
- **Authentication**: ❌ OIDC authentication broken - blocks all API testing

### Available Test Commands (When Fixed)

```bash
# Run specific test file
make test testfile=tests/api/test_auth.py

# Run test categories
make unit-tests
make integration-tests
make performance-tests
make api-tests

# Run with coverage
make tests
```

### Test Types (Implemented but Untested)

1. **Unit Tests**: Component-level testing
2. **Integration Tests**: End-to-end flow testing
3. **Performance Tests**: Scalability and performance testing
4. **Service Tests**: Service layer functionality testing
5. **API Tests**: REST API endpoint testing

### Testing Requirements

Before testing can begin:
1. **Fix Authentication System** - Critical blocker
2. **Set Up Local Environment** - Install dependencies
3. **Configure Test Environment** - Set up pytest and test data
4. **Validate Test Framework** - Ensure tests can run

For detailed testing information, see [Testing Documentation](backend/tests/README.md).

## CI/CD

The project uses GitHub Actions for continuous integration and deployment, with automated builds and testing. Images are published to GitHub Container Registry (GHCR).

### Current CI/CD Status

- **Build Pipeline**: ✅ Automated builds for backend and frontend
- **Image Publishing**: ✅ Images published to `ghcr.io/manavgup/rag_modulo/*`
- **Test Execution**: ⚠️ Tests implemented but blocked by authentication issues
- **Quality Checks**: ✅ Code formatting and linting automated

### CI/CD Pipeline

1. **Code Quality**: Automated linting with Ruff and MyPy
2. **Build**: Docker image builds for backend and frontend
3. **Publish**: Images pushed to GHCR with version tags
4. **Testing**: Comprehensive test suite (when authentication is fixed)

### Available Images

- `ghcr.io/manavgup/rag_modulo/backend:latest`
- `ghcr.io/manavgup/rag_modulo/frontend:latest`
- `ghcr.io/manavgup/rag_modulo/backend:test-latest`

### Pipeline Stages

1. Code Quality
   ```yaml
   quality:
     steps:
       - name: Code Formatting
         run: black backend/
       - name: Type Checking
         run: mypy backend/
       - name: Linting
         run: flake8 backend/
       - name: Import Sorting
         run: isort backend/
   ```

2. Testing
   ```yaml
   test:
     steps:
       - name: Unit Tests
         run: pytest backend/tests/services/
       - name: Integration Tests
         run: pytest backend/tests/integration/
       - name: Performance Tests
         run: |
           pytest backend/tests/performance/ \
             --html=performance-report.html
       - name: Coverage Report
         run: |
           pytest --cov=backend/rag_solution \
             --cov-report=xml \
             --cov-fail-under=80
   ```

3. Security
   ```yaml
   security:
     steps:
       - name: Dependency Scan
         run: safety check
       - name: SAST Analysis
         run: bandit -r backend/
       - name: Secret Detection
         run: detect-secrets scan
   ```

4. Build & Deploy
   ```yaml
   deploy:
     steps:
       - name: Build Images
         run: docker-compose build
       - name: Run Tests in Container
         run: docker-compose run test
       - name: Push Images
         run: docker-compose push
   ```

### Quality Gates

The pipeline enforces several quality gates:

1. Code Quality
   - No formatting errors
   - No type checking errors
   - No linting violations
   - Proper import sorting

2. Testing
   - All tests must pass
   - 80% minimum coverage
   - Performance tests within thresholds
   - No integration test failures

3. Security
   - No critical vulnerabilities
   - No exposed secrets
   - Clean SAST scan

4. Service Requirements
   - Service tests pass
   - API contracts validated
   - Configuration validated
   - Performance metrics met

For detailed CI/CD configuration, see:
- [Workflow Configuration](.github/workflows/ci.yml)
- [Docker Compose Configuration](docker-compose.yml)
- [Test Configuration](backend/pytest.ini)

## Contributing

Contributions are welcome! Please follow these guidelines when contributing to the project.

### Development Guidelines

1. Service Layer Architecture
   - Follow the service-based architecture pattern
   - Implement new features as services
   - Use dependency injection
   - Follow repository pattern for data access
   - Document service interfaces

2. Code Style
   - Use type hints
   - Write comprehensive docstrings
   - Follow PEP 8 guidelines
   - Use async/await where appropriate
   - Handle errors properly

3. Testing Requirements
   - Write unit tests for services
   - Add integration tests for flows
   - Include performance tests for critical paths
   - Maintain test coverage above 80%
   - Document test scenarios

### Contribution Process

1. Fork and Clone
   ```bash
   git clone https://github.com/yourusername/rag-modulo.git
   cd rag-modulo
   ```

2. Set Up Development Environment
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   
   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. Create Feature Branch
   ```bash
   git checkout -b feature/YourFeature
   ```

4. Development Workflow
   - Write tests first (TDD)
   - Implement feature
   - Run test suite
   - Update documentation
   - Run linters

5. Testing
   ```bash
   # Run all tests
   pytest
   
   # Run specific test types
   pytest backend/tests/services/  # Service tests
   pytest backend/tests/integration/  # Integration tests
   pytest backend/tests/performance/  # Performance tests
   
   # Check coverage
   pytest --cov=backend/rag_solution
   ```

6. Submit Changes
   - Push changes to your fork
   - Create pull request
   - Fill out PR template
   - Respond to reviews

### Documentation

When adding new features:
1. Update service documentation
2. Add configuration examples
3. Update testing documentation
4. Include performance considerations
5. Document API changes

For detailed development guidelines, see:
- [Development Guide](backend/rag_solution/docs/development_prompt.md)
- [Testing Guide](backend/tests/README.md)
- [Configuration Guide](backend/rag_solution/docs/configuration.md)

## 🗺️ Project Roadmap

### Current Phase: Critical Blockers (Weeks 1-2)

**Priority**: Fix authentication system and set up testing framework

1. **Fix Authentication System** (CRITICAL)
   - Debug OIDC authentication middleware
   - Fix JWT token validation
   - Test authentication endpoints
   - Verify user login/logout flows

2. **Fix Local Development Environment**
   - Install missing Python dependencies
   - Configure local environment variables
   - Set up local testing framework
   - Verify local development workflow

3. **Install Testing Framework**
   - Install pytest and testing tools
   - Configure test environment
   - Verify test framework works
   - Set up basic test structure

### Next Phase: Core Functionality Testing (Weeks 3-6)

1. **Test Backend Core** - API endpoints, database operations, service layer
2. **Test Frontend Components** - React components, routing, state management
3. **Test Core RAG Functionality** - Document processing, vector search, question generation
4. **Test Data Integration** - Vector database operations, data synchronization

### Future Phases: Refinement and Production (Weeks 7-12)

1. **User Experience Refinement** - Polish UI, optimize performance
2. **Production Deployment** - Set up production infrastructure, monitoring
3. **Agentic AI Enhancement** - Transform into autonomous AI system (Weeks 13-24)

## 🚨 Known Issues

### Critical Issues
- **Authentication System**: OIDC authentication broken - blocks all testing
- **Local Development**: Dependency issues preventing local development
- **Testing Framework**: pytest not available for testing

### Medium Priority Issues
- **Functionality Testing**: All RAG features exist but are untested
- **Integration Testing**: Frontend-backend integration not verified
- **Performance Testing**: Cannot measure actual performance metrics

### Low Priority Issues
- **Documentation**: Some API documentation may be outdated
- **Error Handling**: Error recovery mechanisms not tested

## 🤝 Contributing

**⚠️ Important**: Before contributing, please note that the project is currently in a work-in-progress state with critical authentication issues. We recommend waiting until the authentication system is fixed before making significant contributions.

### Development Guidelines

1. **Service Layer Architecture**
   - Follow the service-based architecture pattern
   - Implement new features as services
   - Use dependency injection
   - Follow repository pattern for data access

2. **Code Style**
   - Use type hints throughout
   - Write comprehensive docstrings
   - Follow PEP 8 guidelines
   - Use async/await where appropriate

3. **Testing Requirements**
   - Write unit tests for services
   - Add integration tests for flows
   - Include performance tests for critical paths
   - Maintain test coverage above 80%

### Contribution Process

1. **Fork and Clone**
2. **Set Up Development Environment** (when authentication is fixed)
3. **Create Feature Branch**
4. **Development Workflow** - Write tests first (TDD)
5. **Testing** - Run test suite
6. **Submit Changes** - Create pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Critical Issues (Current Blockers)

#### Authentication System Not Working

**Problem**: OIDC authentication is broken, blocking all API testing and functionality verification.

**Symptoms**:
- Login attempts fail
- API endpoints return authentication errors
- Cannot test any RAG functionality

**Status**: This is the #1 priority issue that needs to be resolved before any other development can proceed.

#### Local Development Environment Issues

**Problem**: Dependency issues preventing local development setup.

**Symptoms**:
- Poetry installation fails
- pytest not available
- Import errors in local environment

**Temporary Workaround**: Use Docker containers for development:
```bash
make run-ghcr  # Use pre-built images
```

#### Testing Framework Not Available

**Problem**: pytest and testing tools not properly installed.

**Symptoms**:
- `make test` commands fail
- Cannot run any tests
- Test coverage reports unavailable

**Status**: Depends on fixing local development environment.

### Container Issues

#### Service Health Check Failures

If services fail to become healthy:
```bash
# Check service logs
make logs

# Restart services
make stop-containers
make run-services

# Check individual container health
docker compose ps
```

#### GHCR Image Pull Issues

If you have issues pulling images from GitHub Container Registry:
```bash
# Login to GHCR (if needed)
docker login ghcr.io

# Pull latest images
make pull-ghcr-images
```

### Performance Issues

For large datasets or high concurrency:
- Increase memory limits in docker-compose files
- Adjust vector database configuration
- Monitor resource usage with `docker stats`

### Getting Help

1. **Check the logs**: `make logs` to see container logs
2. **Verify environment**: Ensure all required environment variables are set
3. **Check container health**: `docker compose ps` to see service status
4. **Review documentation**: Check the detailed documentation in `claudeDev_Docs/`

### Known Workarounds

- **For Development**: Use `make run-ghcr` instead of local builds
- **For Testing**: Wait for authentication system to be fixed
- **For Local Setup**: Use Docker containers until local environment is fixed
