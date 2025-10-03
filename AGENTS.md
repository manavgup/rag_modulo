# RAG Modulo - AI Agent Context

## 🤖 Instructions for AI Agents

**⚡ QUICK START**: This file is high-level overview only. **You MUST read module-specific AGENTS.md files before making changes.**

### 🎯 Context Loading Protocol (CRITICAL)

**DO THIS EVERY TIME**:
```
1. Read /AGENTS.md (this file) - Project overview
2. Read relevant module AGENTS.md files - Specific patterns
3. Implement following documented patterns
4. Update AGENTS.md if you discover new patterns
```

**Example**: To add a search feature:
- Read: `/AGENTS.md`, `backend/rag_solution/services/AGENTS.md`, `backend/rag_solution/router/AGENTS.md`, `backend/rag_solution/schemas/AGENTS.md`

### AGENTS.md File Locations

When working on specific parts of the codebase, **READ the corresponding AGENTS.md file first**:

#### Backend
- **Backend Overview**: `backend/AGENTS.md`
- **Main Package**: `backend/rag_solution/AGENTS.md`
- **Services Layer**: `backend/rag_solution/services/AGENTS.md` - Read before modifying ANY service
- **Models Layer**: `backend/rag_solution/models/AGENTS.md` - Read before creating/modifying database models
- **Schemas Layer**: `backend/rag_solution/schemas/AGENTS.md` - Read before creating API schemas
- **Router Layer**: `backend/rag_solution/router/AGENTS.md` - Read before adding/modifying endpoints
- **Repository Layer**: `backend/rag_solution/repository/AGENTS.md` - Read before database operations
- **Generation Layer**: `backend/rag_solution/generation/AGENTS.md` - Read before LLM integration work
- **Retrieval Layer**: `backend/rag_solution/retrieval/AGENTS.md` - Read before vector DB operations
- **Data Ingestion**: `backend/rag_solution/data_ingestion/AGENTS.md` - Read before document processing
- **Tests**: `backend/tests/AGENTS.md` - Read before writing tests

#### Frontend
- **Frontend Overview**: `frontend/AGENTS.md`
- **Components**: `frontend/src/components/AGENTS.md` - Read before creating/modifying React components

### Context Loading Strategy

**IMPORTANT**: Always follow this pattern to avoid missing critical context:

1. **Start Here**: Read this root AGENTS.md for project overview
2. **Go Specific**: Read the relevant module's AGENTS.md before making changes
3. **Check Dependencies**: If a module uses other modules, read their AGENTS.md files too

**Example Workflow**:
```
Task: "Add a new search feature"
1. Read: /AGENTS.md (this file) - Project overview
2. Read: backend/rag_solution/services/AGENTS.md - Understand service patterns
3. Read: backend/rag_solution/router/AGENTS.md - Understand router patterns
4. Read: backend/rag_solution/schemas/AGENTS.md - Understand schema patterns
5. Implement: Follow the patterns documented in those files
```

### When to Read Multiple AGENTS.md Files

**For Full-Stack Features**:
- Root AGENTS.md
- `backend/rag_solution/services/AGENTS.md`
- `backend/rag_solution/router/AGENTS.md`
- `backend/rag_solution/schemas/AGENTS.md`
- `frontend/src/components/AGENTS.md`

**For Backend-Only Features**:
- Root AGENTS.md
- `backend/rag_solution/AGENTS.md`
- Relevant layer AGENTS.md (services, models, etc.)

**For Frontend-Only Features**:
- Root AGENTS.md
- `frontend/AGENTS.md`
- `frontend/src/components/AGENTS.md`

---

## Project Overview

RAG Modulo is a production-ready Retrieval-Augmented Generation platform providing enterprise-grade document processing, intelligent search, and AI-powered question answering with Chain of Thought reasoning.

### Technology Stack
- **Backend**: Python 3.12+ with FastAPI, SQLAlchemy, Poetry
- **Frontend**: React 18 with Tailwind CSS
- **Databases**: PostgreSQL (metadata), Milvus (vectors)
- **Infrastructure**: Docker Compose, MinIO (storage), MLFlow (tracking)
- **Testing**: pytest (92% coverage, 847/918 tests passing)

### Architecture Pattern
Service-based architecture with clean separation of concerns:
- **Router Layer** → **Service Layer** → **Repository Layer** → **Models**
- Dependency injection for testability
- Lazy initialization for performance
- Type hints throughout

## 🎯 Current Development Status

**Phase**: Post-Frontend Epic - Agentic Features & Stabilization
**Recent Completions**:
- ✅ Frontend Epic #242 (Search UI, WebSocket, Dashboard)
- ✅ Conversation Management System #243 (Chat interface)
- ✅ Chain of Thought Reasoning #136 (Enhanced RAG quality)

## 🧠 Context Management (ACE-FCA Rules)
- **Context Utilization**: Keep between 40%-60% to maintain efficiency
- **Workflow**: Research → Plan → Implement (with intentional compaction)
- **Human Engagement**: High review during research and planning phases
- **Bad Research Warning**: Poor research leads to thousands of bad lines of code
- **Verification**: Validate research before proceeding to implementation

## 📂 Project Structure

```
rag_modulo/
├── backend/                    # Python FastAPI application
│   ├── rag_solution/          # Main application package
│   │   ├── services/          # Business logic layer
│   │   ├── models/            # SQLAlchemy database models
│   │   ├── schemas/           # Pydantic validation schemas
│   │   ├── router/            # FastAPI endpoint handlers
│   │   ├── repository/        # Data access layer
│   │   ├── generation/        # LLM provider integrations
│   │   ├── retrieval/         # Vector database operations
│   │   ├── data_ingestion/    # Document processing pipeline
│   │   ├── pipeline/          # RAG pipeline orchestration
│   │   ├── query_rewriting/   # Query enhancement
│   │   └── utils/             # Utility functions
│   └── tests/                 # Comprehensive test suite
├── frontend/                   # React web application
│   └── src/
│       ├── components/        # React components (Tailwind CSS)
│       ├── services/          # API client & WebSocket
│       └── contexts/          # React context providers
├── docs/                      # Project documentation
├── deployment/                # Kubernetes & deployment configs
└── scripts/                   # Automation scripts
```

## 🔑 Key Features & Capabilities

### RAG Pipeline Features
- **Chain of Thought (CoT) Reasoning**: Automatic complex question decomposition (#136)
- **Automatic Pipeline Resolution**: No manual pipeline management required (#222)
- **Multi-LLM Support**: WatsonX, OpenAI, Anthropic with provider abstraction
- **Multiple Vector DBs**: Milvus (default), Elasticsearch, Pinecone, Weaviate, ChromaDB
- **Token Tracking**: Comprehensive usage monitoring and cost tracking
- **Source Attribution**: Document-level and chunk-level source tracking

### Frontend Features
- **Chat Interface**: WhatsApp-style conversation UI with WebSocket real-time updates
- **Search Accordions**: Visual display of documents, CoT steps, token usage
- **Dynamic Navigation**: Nested conversation menu with LLM-generated names
- **Dashboard**: Real-time analytics for collections, users, and system health
- **Document Management**: Upload, download, delete with status tracking

### Document Processing
- **Format Support**: PDF, TXT, DOCX, HTML with Docling integration
- **Hierarchical Chunking**: Semantic chunking with configurable strategies
- **Batch Processing**: Efficient multi-document ingestion
- **Metadata Extraction**: Automatic document metadata and structure analysis

## 🎯 Development Guidelines

### Code Quality Standards
- **Line Length**: 120 characters for Python
- **Type Hints**: Required throughout codebase
- **Test Coverage**: >90% required for new code
- **Linting**: Must pass ruff, mypy, pylint, pydocstyle
- **Formatting**: Use `make fix-all` before committing

### Common Development Commands
```bash
# Quick start
make run-ghcr                    # Run with pre-built images

# Development
make dev-hotreload               # Hot-reload for backend & frontend

# Testing
make test-unit-fast              # Fast unit tests
make test-integration            # Integration tests
make test testfile=path/to/test  # Specific test file

# Code quality
make quick-check                 # Fast format + lint check
make fix-all                     # Auto-fix formatting issues
make lint                        # Run all linters
```

### Service Layer Pattern (CRITICAL)
Always follow the established service layer pattern:

1. **Router** (`router/`) - HTTP endpoint handlers
   - Minimal logic, delegate to services
   - Handle request/response serialization
   - Return appropriate HTTP status codes

2. **Service** (`services/`) - Business logic
   - Orchestrate operations across repositories
   - Implement business rules and validation
   - Use dependency injection for dependencies

3. **Repository** (`repository/`) - Data access
   - Database CRUD operations
   - Query building and optimization
   - Return domain models

4. **Models** (`models/`) - SQLAlchemy ORM
   - Database table definitions
   - Relationships and constraints

5. **Schemas** (`schemas/`) - Pydantic validation
   - Request/response validation
   - Data transformation and serialization

## 🔄 Ralph + ACE-FCA Workflow Structure

### **Phase Structure (ACE-FCA)**
1. **🔍 Research Phase** (.ralph/prompts/research_*.md)
   - Understand codebase structure and dependencies
   - Validate assumptions before proceeding
   - Use context compaction to focus on key insights

2. **📋 Planning Phase** (.ralph/prompts/plan_*.md)
   - Create precise, detailed implementation plans
   - Outline exact files to edit and verification steps
   - Compress findings into actionable implementation steps

3. **⚒️ Implementation Phase** (.ralph/prompts/implement_*.md)
   - Execute plans systematically with verification
   - Compact and update context after each stage
   - Maintain high human engagement for quality

### **File Organization**
- **Context Management**: .ralph/current_context.md (compacted context)
- **Progress Tracking**: .ralph/progress.md (iteration tracking)
- **Execution Logs**: .ralph/logs/ (detailed execution history)
- **Specialized Prompts**: .ralph/prompts/ (phase-specific instructions)

## 🚀 Recent Major Features & Fixes

### Chain of Thought (CoT) Reasoning (#136)
**Location**: `backend/rag_solution/services/chain_of_thought_service.py`
- Automatic detection of complex questions requiring decomposition
- Iterative reasoning with context building across steps
- Source attribution across all reasoning steps
- Configurable via `config_metadata` in search requests
- 31 unit tests, full integration test coverage

### Automatic Pipeline Resolution (#222)
**Location**: `backend/rag_solution/services/search_service.py:_resolve_user_default_pipeline()`
- Removed `pipeline_id` from SearchInput schema
- Automatic pipeline creation for new users
- Intelligent error handling for configuration issues
- Simplified CLI and API interfaces

### Conversation System
**Components**:
- `models/conversation_session.py`, `conversation_message.py`, `conversation_summary.py`
- `services/conversation_service.py` - CRUD, naming, summarization
- `router/conversation_router.py` - 10 REST endpoints
- `router/websocket_router.py` - Real-time messaging
- Frontend: Dynamic sidebar navigation with LLM-generated conversation names

### Dashboard & Analytics
**Location**: `services/dashboard_service.py`, `router/dashboard_router.py`
- Real-time collection, user, file, and search statistics
- Recent activity tracking
- Frontend integration at `/dashboard`

### **Issue #242: Agentic RAG Frontend Epic** (Status: ✅ COMPLETE)
- **✅ COMPLETED**: Enhanced Search Interface with accordion displays (documents, token tracking, CoT reasoning)
- **✅ COMPLETED**: Real-time Communication (WebSocket + REST API fallback)
- **✅ COMPLETED**: Smart Data Display (document name resolution, responsive design)
- **✅ COMPLETED**: Advanced Collection Analytics (dashboard at /dashboard)
- **✅ COMPLETED**: Batch processing for multiple documents
- **✅ COMPLETED**: Conversation messaging system (WebSocket-based with full persistence via ConversationService)
- **✅ COMPLETED**: Conversation management UI and REST API (session CRUD, conversation switching)
- **🚫 EXCLUDED**: IBM Carbon Design (moving to Tailwind), Agent Orchestration (later), Multi-collection chat

**Implementation Progress: 100% of practical scope completed**
- **US-1.1**: Basic Chat Interface ✅ **COMPLETE** (WebSocket + ConversationService integration)
- **US-1.2**: Context-Aware Conversations ✅ **COMPLETE** (full conversation management system)
- **US-3.2**: Advanced Collection Analytics ✅ **COMPLETE**
- **US-3.3**: Collaborative Collection Management (optional)

**Final Implementation Status**
- **✅ COMPLETE**: Full WebSocket conversation system with ConversationService integration
- **✅ COMPLETE**: Complete models, schemas, repositories, and services for conversations
- **✅ COMPLETE**: REST API router for conversation CRUD operations (10 endpoints)
- **✅ COMPLETE**: Frontend conversation management UI (sidebar, switching, history, persistence)
- **✅ COMPLETE**: Session-aware WebSocket integration with context preservation

### **Infrastructure Foundation** (Status: ✅ Complete)
- **✅ COMPLETED**: Tailwind frontend replaces IBM Carbon design
- **✅ COMPLETED**: Frontend Dockerfile created (`frontend/Dockerfile`)
- **✅ COMPLETED**: Docker-compose updated for new frontend
- **✅ COMPLETED**: API client service (`frontend/src/services/apiClient.ts`)
- **✅ COMPLETED**: WebSocket client (`frontend/src/services/websocketClient.ts`)
- **✅ COMPLETED**: Frontend builds successfully (95.11 kB optimized)

### **Issue #243: Conversational Chat Interface** (Status: ✅ Core Features Implemented)
- **Scope**: WhatsApp-style chat for document Q&A with WebSocket integration
- **Priority**: Critical (foundation for agentic features)
- **✅ COMPLETED**: Chat functionality with real API integration
- **✅ COMPLETED**: Search endpoint optimization and icon improvements
- **✅ COMPLETED**: WebSocket fallback to REST API implementation
- **🔧 REMAINING**: TypeScript compilation fixes, final UI polish

### **Issue #244: Agent Discovery & Orchestration** (Status: Planned)
- **Scope**: Agent marketplace, configuration UI, execution monitoring
- **Dependencies**: Issue #243 completion
- **Technology**: IBM MCP Context Forge integration
- **Status**: Ready for Phase 3 implementation

### **Issue #245: Architecture Decision** (Status: ✅ Resolved)
- **✅ DECISION**: IBM MCP Context Forge selected
- **✅ IMPACT**: Architecture decision enables all agentic capabilities
- **Status**: Approved and documented

## 📊 Recent Implementation Details (September 29, 2025)

### **Critical Bug Fixes Completed**
1. **Collection Creation 422 Error** (`backend/rag_solution/repository/user_collection_repository.py`)
   - **Issue**: N+1 query generating 425 UUIDs causing database overload
   - **Solution**: Implemented eager loading with `joinedload()` for collections and files
   - **Impact**: Collection creation now works seamlessly

2. **Frontend Type Safety** (`frontend/src/services/apiClient.ts`)
   - **Issue**: Collection status type missing 'completed' value
   - **Solution**: Updated union types to include all valid status values
   - **Impact**: Eliminated TypeScript compilation errors

3. **Mock Data to Real API Integration** (`frontend/src/components/modals/LightweightCreateCollectionModal.tsx`)
   - **Issue**: Collection creation was creating mock data instead of calling backend
   - **Solution**: Replaced mock creation with real `apiClient.createCollection()` calls
   - **Impact**: Collections now properly persist to database

4. **Dashboard Runtime Error** (`frontend/src/components/dashboard/LightweightDashboard.tsx`)
   - **Issue**: `toLocaleString()` called on undefined values causing runtime crashes
   - **Solution**: Added null checks with nullish coalescing (`stats?.property ?? 0`)
   - **Impact**: Dashboard now loads without runtime errors and displays proper default values

### **Feature Implementations Completed**
1. **Enhanced Search Functionality** (`frontend/src/components/search/LightweightSearchInterface.tsx`)
   - **UI Enhancement**: Changed search icon to paper airplane for better UX
   - **Reliability**: Added REST API fallback when WebSocket fails
   - **Error Handling**: Comprehensive error handling with user notifications

2. **Document Management** (`frontend/src/components/collections/LightweightCollectionDetail.tsx`)
   - **Delete Functionality**: Individual document deletion with confirmation
   - **Download Functionality**: Direct document download with proper URL handling
   - **Status Management**: Proper document status updates and error handling

3. **Dashboard Implementation** (Backend: Schema + Service + Router Pattern)
   - **Schema**: `backend/rag_solution/schemas/dashboard_schema.py` - Data validation
   - **Service**: `backend/rag_solution/services/dashboard_service.py` - Business logic with real DB queries
   - **Router**: `backend/rag_solution/router/dashboard_router.py` - API endpoints
   - **Frontend**: Already integrated with `apiClient.getDashboardStats()` and `apiClient.getRecentActivity()`

4. **Hot-Reload Development Environment Optimization** (DevOps Enhancement)
   - **Backend**: Created `backend/Dockerfile.dev` with uvicorn auto-reload (`--reload --reload-dir /app`)
   - **Frontend**: Enhanced `frontend/Dockerfile.dev` with React HMR (Fast Refresh, file polling)
   - **Docker Compose**: Updated `docker-compose.hotreload.yml` with optimized development containers
   - **Makefile**: Enhanced `make dev-hotreload` with comprehensive development commands
   - **Impact**: Both frontend React changes and backend Python changes now hot-reload instantly

### **Current Issues Recently Resolved** ✅
1. **✅ TypeScript Compilation Errors** (`frontend/src/components/collections/LightweightCollectionDetail.tsx`)
   - **Issue**: Variable name collision: `document` parameter conflicts with global `document` object
   - **Solution**: Renamed parameter from `document` to `file` to avoid DOM API conflicts
   - **Status**: Fixed in previous session

2. **✅ Backend Linting** (All created/modified Python files)
   - **Issue**: Pass ruff, mypy, pylint, and pydocstyle checks
   - **Solution**: Fixed all linting issues in dashboard_service.py, dashboard_router.py, dashboard_schema.py
   - **Status**: All Python files now pass linting checks

3. **✅ Dashboard Runtime Errors** (`frontend/src/components/dashboard/LightweightDashboard.tsx`)
   - **Issue**: `toLocaleString()` runtime errors on undefined values
   - **Solution**: Added comprehensive null checks with nullish coalescing
   - **Status**: Dashboard now loads without errors

### **Development Environment Status** ✅
- **✅ Hot-Reload**: Both frontend and backend hot-reload working optimally
- **✅ Dashboard API**: All endpoints responding correctly (stats and activity)
- **✅ Frontend Compilation**: No TypeScript errors, webpack compiling successfully
- **✅ Backend Health**: uvicorn auto-reload active, all services healthy

## ⚠️ Known Issues & Important Notes

### Current Known Issues
1. **Authentication System** - OIDC integration needs fixing (blocking some admin features)
2. **Test Failures** - 1 integration test failure in `test_router_registration_integration.py`
3. **Podcast Router** - API prefix inconsistency (fixed in recent commits)

### Important Architecture Decisions

#### Multi-Database Pattern
- **PostgreSQL**: User management, collections, conversations, metadata
- **Milvus**: Vector embeddings and similarity search
- **MinIO**: Document storage and file management
- **Separation of Concerns**: Clear boundaries between operational and vector data

#### LLM Provider Abstraction
**Location**: `backend/rag_solution/generation/providers/`
- Common interface for all LLM providers
- Provider-specific implementations for WatsonX, OpenAI, Anthropic
- Automatic fallback and error handling
- Token usage tracking across all providers

#### Lazy Initialization Pattern
Used throughout service layer to avoid circular dependencies:
```python
@property
def dependency_service(self) -> DependencyService:
    if self._dependency_service is None:
        self._dependency_service = DependencyService(self.db, self.settings)
    return self._dependency_service
```

### Environment Variables
**Critical**: Must be set in `.env` file
- `COLLECTIONDB_*`: PostgreSQL connection
- `VECTOR_DB`: Vector database type (default: milvus)
- `MILVUS_*`: Milvus configuration
- `WATSONX_*` or `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`: LLM provider credentials
- `JWT_SECRET_KEY`: Authentication secret

### Testing Strategy
**Test Markers**:
- `@pytest.mark.unit`: Fast unit tests (no external dependencies)
- `@pytest.mark.integration`: Integration tests (requires services)
- `@pytest.mark.api`: API endpoint tests
- `@pytest.mark.performance`: Performance benchmarks

**Coverage Requirements**:
- New code: >90% coverage
- Critical paths (search, auth): 100% coverage
- Use `make test-unit-fast` for rapid feedback

### **Next Phase Recommendations**
1. **Test and validate** all implemented features end-to-end
2. **Performance optimization** for dashboard API responses
3. **Enhanced error handling** for edge cases
4. **Begin Phase 2**: Agent Discovery and Advanced Features

## Phase 2: GitHub Issue Discovery
After completing the priority issues, discover other open issues:
1. Search GitHub repository for open issues
2. Prioritize by: importance, complexity, dependencies, labels
3. Focus on: bug fixes, feature requests, improvements
4. Skip: documentation-only, questions, duplicates

## Your Mission
1. **Phase 1**: Analyze and implement Issues #242, #243, #244
2. **Phase 2**: Discover other GitHub issues and prioritize them
3. **Phase 3**: Implement issues systematically by priority

## 🤖 Agent Development Instructions

### **Quality Gates (Must Follow)**
- **Pre-Commit**: Always run `make pre-commit-run` and tests before committing
- **Test Coverage**: Add comprehensive tests for new features (>90% coverage)
- **Code Patterns**: Follow existing patterns in `rag_solution/` and `webui/src/`
- **Branch Strategy**: Create feature branches for each issue (`feature/issue-XXX`)
- **Commit Messages**: Descriptive commits following conventional format

### **Development Workflow**
1. **Research First**: Use appropriate research prompt for thorough analysis
2. **Plan Before Code**: Create detailed implementation plan with verification steps
3. **Implement Systematically**: Execute plan with frequent verification and testing
4. **Context Compaction**: Update .ralph/current_context.md with compressed findings
5. **Progress Tracking**: Document progress in .ralph/progress.md after each iteration

### **Technology Stack Commands**
- **Python**: `poetry run <command>` for all Python operations
- **Frontend**: `npm run dev` for React development
- **Testing**: `make test-unit-fast`, `make test-integration`
- **Linting**: `make lint`, `make fix-all` - Any files created or edited should pass linting checks from ruff, mypy, pylint, and pydocstyle

### **Docker Compose Commands (V2 Required)**
**⚠️ IMPORTANT: Always use `docker compose` (V2) not `docker-compose` (V1)**

**Development Workflow:**
- **Local Development**: `docker compose -f docker-compose.dev.yml up -d`
- **Build Development**: `docker compose -f docker-compose.dev.yml build backend`
- **Production Testing**: `make run-ghcr` (uses pre-built GHCR images)
- **Stop Services**: `docker compose -f docker-compose.dev.yml down`

**File Structure:**
- `docker-compose.yml` - Production (uses GHCR pre-built images)
- `docker-compose.dev.yml` - Development (builds locally from source)
- `docker-compose-infra.yml` - Infrastructure services (Postgres, Milvus, MinIO)

**Why Development Uses Separate File:**
The production `docker-compose.yml` uses `image:` with pre-built GHCR images, while development requires `build:` to include local code changes. This prevents the common error where `docker compose build` attempts to build from a file that only references pre-built images.

## 📊 Context Management (ACE-FCA Principles)

### **Context Utilization Rules**
- **Target Range**: 40%-60% context window utilization
- **Compaction Strategy**: Compress technical details into key actionable insights
- **Focus Discipline**: Work on ONE issue at a time to maintain quality
- **Format Standards**: Use bullet points and structured formats for clarity

### **Research Phase Context Management**
- **Validate Early**: Confirm research direction before deep implementation
- **Risk Awareness**: Poor research → thousands of bad lines of code
- **Insight Extraction**: Focus on understanding codebase structure and dependencies
- **Compression**: Distill findings into implementation-ready insights

### **Implementation Phase Context Management**
- **Plan Adherence**: Follow detailed plans created during planning phase
- **Verification Points**: Test and validate after each implementation stage
- **Context Updates**: Compact and update context after verified progress
- **Human Engagement**: Maintain high human review, especially for critical decisions

### **Context State Tracking**
- **Current State**: .ralph/current_context.md (compacted current context)
- **Progress History**: .ralph/progress.md (iteration progress tracking)
- **Detailed Logs**: .ralph/logs/ (full execution logs for debugging)
- **Phase Context**: .ralph/prompts/ (specialized context for each development phase)

## Success Criteria
- All tests pass
- Code follows project style
- Security guidelines followed
- Documentation updated
- Issues properly implemented
- Progress tracked in .ralph/progress.md

## 🔄 Ralph + ACE-FCA Execution Workflow

### **Iteration Structure (ralph-runner.sh)**
1. **Context Loading**: Combine AGENTS.md + current issue context
2. **Phase Execution**: Run appropriate research/plan/implement prompt
3. **Verification**: Run tests and validate implementation
4. **Context Compaction**: Update context with key findings and next steps
5. **Progress Tracking**: Log iteration results and prepare for next cycle

### **Phase-Specific Workflows**

#### **🔍 Research Phase**
- **Prompt**: `.ralph/prompts/research_*.md`
- **Goal**: Understand codebase, dependencies, implementation requirements
- **Output**: Compacted research findings with implementation readiness assessment
- **Validation**: Confirm research accuracy before proceeding to planning

#### **📋 Planning Phase**
- **Prompt**: `.ralph/prompts/plan_*.md`
- **Goal**: Create detailed, executable implementation plan
- **Output**: Step-by-step plan with files to edit, tests to add, verification steps
- **Human Review**: High engagement to ensure plan quality and feasibility

#### **⚒️ Implementation Phase**
- **Prompt**: `.ralph/prompts/implement_*.md`
- **Goal**: Execute plan systematically with continuous verification
- **Output**: Working code with tests, documentation updates, progress tracking
- **Quality Gates**: Lint, tests, code review before considering complete

### **Context Compaction Strategy**
- **After Research**: Compress findings into key insights and implementation requirements
- **After Planning**: Compress plan into essential steps and verification criteria
- **After Implementation**: Compress results into completed features and next actions
- **Continuous**: Maintain 40%-60% context utilization throughout all phases

## File Structure Reference

ralph/
├── prompts/
│ ├── research_features.md # Feature research and analysis
│ ├── research_documentation.md # Documentation research
│ ├── plan_features.md # Feature implementation planning
│ ├── plan_documentation.md # Documentation planning
│ ├── implement_features.md # Feature implementation
│ └── implement_documentation.md # Documentation implementation
├── logs/
│ ├── ralph.log # Main execution log
│ └── claude_output_.log # Claude execution logs
├── context/
│ └── current_context.md # Current context state
├── progress.md # Progress tracking
└── current_context.md # Combined context for Claude

## 📚 AGENTS.md Documentation System

### Purpose
AGENTS.md files provide contextual documentation for AI agents and human developers throughout the codebase. They ensure consistent understanding of module purposes, patterns, and best practices.

### File Hierarchy
```
/AGENTS.md                                    # Project overview (this file)
├── backend/AGENTS.md                         # Backend architecture
│   └── rag_solution/AGENTS.md               # Main application package
│       ├── services/AGENTS.md               # Service layer patterns
│       ├── models/AGENTS.md                 # Database models
│       ├── schemas/AGENTS.md                # API schemas
│       ├── router/AGENTS.md                 # API endpoints
│       ├── repository/AGENTS.md             # Data access
│       ├── generation/AGENTS.md             # LLM providers
│       ├── retrieval/AGENTS.md              # Vector search
│       ├── data_ingestion/AGENTS.md         # Document processing
│       ├── pipeline/AGENTS.md               # Pipeline orchestration
│       ├── query_rewriting/AGENTS.md        # Query enhancement
│       ├── file_management/AGENTS.md        # File operations
│       ├── utils/AGENTS.md                  # Utilities
│       └── tests/AGENTS.md                  # Testing guidelines
└── frontend/AGENTS.md                        # Frontend architecture
    └── src/components/AGENTS.md             # React components
```

### Version Control
**YES - Commit AGENTS.md files to Git**

These files should be version controlled because:
1. **Team Consistency**: All developers and AI agents have consistent context
2. **Living Documentation**: Evolves with the codebase
3. **Onboarding**: New team members understand architecture quickly
4. **Code Reviews**: Reviewers can reference documented patterns
5. **AI Context**: GitHub Copilot, Claude Code, and other AI tools use them

### Maintaining AGENTS.md Files

**When to Update**:
- Adding new modules/features
- Changing architectural patterns
- Discovering common pitfalls
- Adding new best practices
- Major refactoring

**What to Include**:
- Module purpose and responsibilities
- Key files and their roles
- Common patterns and examples
- Best practices and conventions
- Common pitfalls to avoid
- Links to related AGENTS.md files

**What NOT to Include**:
- Detailed API documentation (use OpenAPI/Swagger)
- Code that duplicates docstrings
- Temporary implementation notes
- Issue-specific details (use GitHub issues)

### For AI Agents: Context Loading Protocol

**Always follow this sequence**:
1. Read root `/AGENTS.md` for project overview
2. Identify which modules you'll be working with
3. Read relevant module AGENTS.md files
4. Follow the patterns documented in those files
5. Update AGENTS.md if you discover new patterns or issues

**Example**:
```
User asks: "Add user profile picture upload"

Agent should read:
1. /AGENTS.md - Project overview
2. backend/rag_solution/AGENTS.md - Application structure
3. backend/rag_solution/services/AGENTS.md - Service patterns
4. backend/rag_solution/models/AGENTS.md - Model patterns
5. backend/rag_solution/router/AGENTS.md - Endpoint patterns
6. backend/rag_solution/schemas/AGENTS.md - Schema patterns
7. frontend/src/components/AGENTS.md - Component patterns

Then implement following documented patterns.
```

## Usage Instructions
- Start with this file for project overview and context loading strategy
- Read module-specific AGENTS.md files before making changes
- Follow documented patterns strictly
- Update AGENTS.md files when discovering new patterns
- Update CHANGELOG.md in docs/
- Update documentation in docs/ folder in mkdocs format.
- Use plan.md for large changes.
