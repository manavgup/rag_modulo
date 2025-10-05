# RAG Modulo Agentic Development - Gemini

This document outlines the development process for Gemini, an AI agent, working on the RAG Modulo project.

## 🎯 Current Mission: Agentic RAG Platform Development

**Priority:** Enhance the RAG platform with new features, fix bugs, and improve performance.

## 🧠 Development Philosophy

- **Understand First**: Before making any changes, thoroughly understand the codebase, architecture, and existing conventions.
- **Plan Thoughtfully**: Create a clear and concise plan before implementing any changes.
- **Implement Systematically**: Execute the plan in a structured manner, with regular verification and testing.
- **Test Rigorously**: Ensure all changes are covered by tests and that all tests pass.
- **Document Clearly**: Update documentation to reflect any changes made to the codebase.

## 📋 Project Context Essentials

- **Architecture**: Python FastAPI backend + React frontend.
- **Focus**: Transform basic RAG into an agentic AI platform with agent orchestration.
- **Tech Stack**: Python, FastAPI, React, Docker, a variety of vector databases.
- **Quality Standards**: >90% test coverage, clean code, and comprehensive documentation.

## 🚀 Development Workflow

### **Phase 1: Research**
- Understand the codebase structure and dependencies.
- Validate assumptions before proceeding.
- Use context compaction to focus on key insights.

### **Phase 2: Planning**
- Create precise, detailed implementation plans.
- Outline exact files to edit and verification steps.
- Compress findings into actionable implementation steps.

### **Phase 3: Implementation**
- Execute plans systematically with verification.
- Compact and update context after each stage.
- Maintain high human engagement for quality.

## 🤖 Agent Development Instructions

### **Quality Gates (Must Follow)**
- **Pre-Commit**: Always run `make pre-commit-run` and tests before committing.
- **Test Coverage**: Add comprehensive tests for new features (>90% coverage).
- **Code Patterns**: Follow existing patterns in `backend/` and `frontend/`.
- **Branch Strategy**: Create feature branches for each issue (`feature/issue-XXX`).
- **Commit Messages**: Descriptive commits following conventional format.

### **Technology Stack Commands**
- **Python**: `poetry run <command>` for all Python operations.
- **Frontend**: `npm run dev` for React development.
- **Testing**: `make test-unit-fast`, `make test-integration`.
- **Linting**: `make lint`, `make fix-all`.

### **Docker Compose Commands (V2 Required)**
- **Local Development**: `docker compose -f docker-compose.dev.yml up -d`
- **Build Development**: `docker compose -f docker-compose.dev.yml build backend`
- **Production Testing**: `make run-ghcr` (uses pre-built GHCR images)
- **Stop Services**: `docker compose -f docker-compose.dev.yml down`

## ✅ Success Criteria

- All tests pass.
- Code follows project style.
- Security guidelines followed.
- Documentation updated.
- Issues properly implemented.
