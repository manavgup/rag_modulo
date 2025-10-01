# RAG Modulo Agentic Development - Ralph + ACE-FCA Pattern

Implementing Ralph pattern with Advanced Context Engineering (ACE-FCA) for systematic issue resolution.

## 🎯 Current Mission: Agentic RAG Platform Development
**Priority Issues:** #242 (Frontend Epic), #243 (Chat Interface), #244 (Agent Orchestration)
**Next Phase:** Issue discovery and systematic implementation by priority

## 🧠 Context Management (ACE-FCA Rules)
- **Context Utilization**: Keep between 40%-60% to maintain efficiency
- **Workflow**: Research → Plan → Implement (with intentional compaction)
- **Human Engagement**: High review during research and planning phases
- **Bad Research Warning**: Poor research leads to thousands of bad lines of code
- **Verification**: Validate research before proceeding to implementation

## 📋 Project Context Essentials
- **Architecture**: Python FastAPI backend + React frontend + IBM Carbon Design
- **Focus**: Transform basic RAG into agentic AI platform with agent orchestration
- **Tech Stack**: IBM MCP Context Forge recommended for agent orchestration
- **Quality Standards**: >90% test coverage, WCAG compliance, production-ready

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

## 🚀 Current Development Phase: Critical Fixes & Dashboard Implementation ✅

### **Recent Major Accomplishments (September 30, 2025)**
- **✅ COMPLETED**: Collection creation 422 error fixed (N+1 query optimization)
- **✅ COMPLETED**: Chat functionality enhanced (search endpoint integration, icon updates)
- **✅ COMPLETED**: Document management (delete/download operations implemented)
- **✅ COMPLETED**: Dashboard system with real-time data (schema + service + router pattern)
- **✅ COMPLETED**: Frontend API integration improvements
- **✅ COMPLETED**: TypeScript compilation fixes and code linting
- **✅ COMPLETED**: Dynamic Chat Menu with nested conversation navigation
- **✅ COMPLETED**: LLM-based conversation naming and retroactive conversation updates
- **✅ COMPLETED**: Clean chat interface (removed redundant conversation tiles)
- **✅ COMPLETED**: Removed legacy Carbon Design System dependencies

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

### **Latest Session Accomplishments (September 30, 2025) - Dynamic Chat Navigation**

#### **Major Feature Implementation: Dynamic Chat Menu**
1. **Dynamic Sidebar Navigation** (`frontend/src/components/layout/LightweightSidebar.tsx`)
   - **Issue**: Conversations were standalone menu item without nested structure
   - **Solution**: Moved conversations under Chat menu with expandable structure
   - **Features**: Shows last 10 conversations, "All chats" option with ellipsis-horizontal-circle icon
   - **Impact**: Improved navigation UX with organized conversation hierarchy

2. **LLM-Based Conversation Naming** (`backend/rag_solution/services/conversation_service.py`)
   - **Issue**: Too many conversations with generic names like "New Conversation"
   - **Solution**: Added `generate_conversation_name()` using LLM to create concise titles
   - **API**: Added endpoints for single and bulk conversation renaming
   - **Impact**: Conversations now have meaningful names like "IBM Business Strategy"

3. **Clean Chat Interface** (`frontend/src/components/search/LightweightSearchInterface.tsx`)
   - **Issue**: Redundant conversations tile on chat page after implementing sidebar navigation
   - **Solution**: Removed conversations sidebar, changed grid from 4-column to single column
   - **Impact**: Clean, focused chat interface without duplicate conversation management

4. **Conversation Navigation** (URL Parameter Support)
   - **Issue**: Clicking conversations in sidebar didn't load that specific chat
   - **Solution**: Added `?session=` URL parameter handling and `loadSpecificConversation()`
   - **Features**: Loads conversation messages, collection info, and maintains state
   - **Impact**: Seamless conversation switching from sidebar

5. **Modal Integration** (`frontend/src/components/modals/AllChatsModal.tsx`)
   - **New Component**: Full modal for browsing all conversations with search functionality
   - **Features**: Search filter, date formatting, conversation selection
   - **Integration**: Connected to sidebar "All chats" option

#### **Code Quality & Maintenance**
1. **TypeScript Compilation Fixes**
   - **Issue**: Type mismatches between `ConversationSession` and `Conversation` interfaces
   - **Solution**: Aligned type definitions and fixed timestamp type from string to Date
   - **Impact**: Clean compilation without type errors

2. **Legacy Dependency Cleanup**
   - **Issue**: Unused Carbon Design System components causing compilation errors
   - **Solution**: Removed `AnalyticsDashboard.tsx` and `Dashboard.tsx` (old Carbon versions)
   - **Outcome**: Only Lightweight components remain, no external design system dependencies

3. **API Client Integration**
   - **Enhancement**: Used proper `apiClient.getConversations()` instead of generic `.get()`
   - **Notification System**: Integrated with `useNotification` context for error handling
   - **Impact**: Consistent API usage patterns throughout frontend

#### **Implementation Quality**
- **Architecture**: Followed existing service layer patterns and API conventions
- **Error Handling**: Comprehensive error handling with user notifications
- **Type Safety**: All TypeScript types properly aligned
- **State Management**: Proper React state management with useEffect patterns
- **Responsive Design**: Mobile-friendly with sidebar auto-close on small screens

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

## Usage Instructions
- Start with this file (PROMPT_ISSUES.md) for issue implementation
- Use specialized prompts in .ralph/prompts/ for specific tasks
- Monitor progress in .ralph/progress.md
- Check logs in .ralph/logs/ for execution details
- Update context in .ralph/current_context.md as needed
