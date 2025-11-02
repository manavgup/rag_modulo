# GitHub Project Board Setup Guide

## Conversation System Refactoring Project

This document provides instructions for setting up a GitHub Project board to track the conversation system refactoring phases.

---

## Project Details

**Project Name**: Conversation System Refactoring

**Description**: Multi-phase refactoring to eliminate 55% code redundancy and fix N+1 queries across the conversation system.

**Parent Issue**: [#539](https://github.com/manavgup/rag_modulo/issues/539)

---

## Create Project Board

1. Go to GitHub repository: https://github.com/manavgup/rag_modulo
2. Click on "Projects" tab
3. Click "New project"
4. Choose "Board" view
5. Name: "Conversation System Refactoring"
6. Add description (see above)

---

## Board Columns

Create the following columns:

1. **📋 Backlog** - Not yet started
2. **🚧 In Progress** - Currently being worked on
3. **👀 In Review** - PR submitted, awaiting review
4. **✅ Complete** - Merged and done

---

## Add Issues to Project

Add the following issues to the project board:

### Phase 1 & 2 (Complete)
- **PR #556** - Models & Repository Consolidation
  - Status: ✅ Complete (or 👀 In Review if not yet merged)
  - Labels: `phase-1-2`, `models`, `repository`

### Phase 3 (Service Consolidation)
- **Issue #557** - Service Consolidation
  - Status: 📋 Backlog
  - Labels: `phase-3`, `services`
  - Depends on: PR #556

### Phase 4 (Router Unification)
- **Issue #558** - Router Unification
  - Status: 📋 Backlog
  - Labels: `phase-4`, `router`, `api`
  - Depends on: #557

### Phase 5 (Testing & Validation)
- **Issue #559** - Testing & Validation
  - Status: 📋 Backlog
  - Labels: `phase-5`, `testing`
  - Depends on: #558

### Phase 6 (Frontend Migration)
- **Issue #560** - Frontend Migration
  - Status: 📋 Backlog
  - Labels: `phase-6`, `frontend`
  - Depends on: #559

### Phase 7 (Cleanup & Deprecation)
- **Issue #561** - Cleanup & Deprecation Removal
  - Status: 📋 Backlog
  - Labels: `phase-7`, `cleanup`
  - Depends on: #560

---

## Project Fields (Optional Custom Fields)

Add these custom fields to track additional metadata:

1. **Phase** (Single Select)
   - Phase 1 & 2
   - Phase 3
   - Phase 4
   - Phase 5
   - Phase 6
   - Phase 7

2. **Estimated Effort** (Single Select)
   - 1-2 days
   - 2-3 days
   - 3-5 days

3. **Dependencies** (Text)
   - List issue numbers this depends on

4. **Code Reduction** (Text)
   - Expected lines of code reduction

---

## Project Goals Summary

Add to project README/description:

### Overall Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Files** | 11 files | 4 files | 64% reduction |
| **Lines of Code** | 4,174 lines | ~2,514 lines | 40% reduction |
| **Database Queries** | 54 queries | 1 query | 98% reduction |
| **Response Time** | 156ms | 3ms | 98% faster |

### Per-Phase Goals

- **Phase 1 & 2**: Models & Repository consolidation ✅
- **Phase 3**: Service consolidation (2,155 → 800 lines, 63% reduction)
- **Phase 4**: Router unification (1,036 → 600 lines, 42% reduction)
- **Phase 5**: 90%+ test coverage
- **Phase 6**: Zero deprecated API usage in frontend
- **Phase 7**: Remove 9 deprecated files (~3,000 lines)

---

## Milestone Setup

Create a milestone for the overall refactoring:

**Milestone Name**: Conversation System Refactoring Complete

**Due Date**: (Set based on team capacity)

**Description**:
Complete all 7 phases of the conversation system refactoring. Achieve 64% file reduction, fix N+1 queries, and improve response time by 98%.

**Issues in Milestone**:
- #556 (Phase 1 & 2)
- #557 (Phase 3)
- #558 (Phase 4)
- #559 (Phase 5)
- #560 (Phase 6)
- #561 (Phase 7)

---

## Automation Rules (Optional)

Set up GitHub Actions or Project automation:

1. **Auto-move to "In Progress"** when issue assigned
2. **Auto-move to "In Review"** when PR created
3. **Auto-move to "Complete"** when PR merged
4. **Auto-link dependencies** when issue mentions other issues

---

## Project Board URL

After creation, the project board will be available at:
`https://github.com/manavgup/rag_modulo/projects/[number]`

---

## Next Steps

1. Create the project board following the steps above
2. Add all issues to the board
3. Set up custom fields if desired
4. Create milestone
5. Share project board URL with team
6. Use board to track refactoring progress

---

## Related Documentation

- **Refactoring Plan**: `docs/development/conversation-system-refactoring.md`
- **Parent Issue**: [#539](https://github.com/manavgup/rag_modulo/issues/539)
- **PR #556**: Phase 1 & 2 implementation
