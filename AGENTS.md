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

## 🚀 Current Development Phase: Priority Issues

### **Issue #242: Agentic RAG Frontend Epic** (Status: Research)
- **Scope**: Transform React frontend into comprehensive agentic AI interface
- **Key Components**: Chat interface, agent orchestration UI, workflow designer
- **Dependencies**: Issues #243, #244 are sub-components of this epic

### **Issue #243: Conversational Chat Interface** (Status: Ready)
- **Scope**: WhatsApp-style chat for document Q&A with WebSocket integration
- **Priority**: Critical (foundation for agentic features)
- **Implementation**: 6 weeks, needs backend chat API coordination

### **Issue #244: Agent Discovery & Orchestration** (Status: Planning)
- **Scope**: Agent marketplace, configuration UI, execution monitoring
- **Dependencies**: Requires Issue #245 (Architecture Decision) approval
- **Technology**: IBM MCP Context Forge integration

### **Issue #245: Architecture Decision** (Status: Pending Approval)
- **Scope**: Select agent orchestration framework (Recommended: IBM MCP Context Forge)
- **Impact**: Foundational decision affecting all agentic capabilities
- **Next Step**: Architecture approval before proceeding

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
- **Docker**: `make run-ghcr` for quick testing

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
