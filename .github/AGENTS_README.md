# AGENTS.md Documentation System

## Overview

This project uses **AGENTS.md files** throughout the codebase to provide contextual documentation for AI development tools (Claude Code, GitHub Copilot, etc.) and human developers.

## Purpose

AGENTS.md files serve as **living documentation** that:
- ✅ Provides AI agents with architectural context and patterns
- ✅ Helps developers understand module responsibilities quickly
- ✅ Documents coding conventions and best practices
- ✅ Serves as onboarding material for new team members
- ✅ Ensures consistency across the codebase

## File Locations

```
/AGENTS.md                                    # Project overview
├── backend/AGENTS.md                         # Backend architecture
│   └── rag_solution/AGENTS.md               # Main application
│       ├── services/AGENTS.md               # Service layer
│       ├── models/AGENTS.md                 # Database models
│       ├── schemas/AGENTS.md                # API schemas
│       ├── router/AGENTS.md                 # API endpoints
│       └── repository/AGENTS.md             # Data access
└── frontend/AGENTS.md                        # Frontend architecture
    └── src/components/AGENTS.md             # React components
```

## How to Use

### For Developers

**Before starting work on a module:**
1. Read the root `/AGENTS.md` for project overview
2. Read the module-specific AGENTS.md file (e.g., `services/AGENTS.md`)
3. Follow the patterns documented in those files
4. Update AGENTS.md if you discover new patterns or issues

**Example workflow:**
```
Task: "Add a new search filter feature"

1. Read /AGENTS.md - Understand project architecture
2. Read backend/rag_solution/services/AGENTS.md - Service patterns
3. Read backend/rag_solution/router/AGENTS.md - API endpoint patterns
4. Read backend/rag_solution/schemas/AGENTS.md - Schema patterns
5. Implement following the documented patterns
```

### For AI Development Tools

AI tools automatically benefit from AGENTS.md files:
- **Claude Code**: Reads AGENTS.md for context when making changes
- **GitHub Copilot**: Uses AGENTS.md for better code suggestions
- **Other AI Tools**: Can reference AGENTS.md for architectural understanding

## What's Included in AGENTS.md Files

Each AGENTS.md file contains:
- **Module Purpose**: What this module does
- **Key Files**: Important files and their responsibilities
- **Patterns**: Code patterns and conventions used
- **Best Practices**: Dos and don'ts
- **Common Pitfalls**: Mistakes to avoid
- **Examples**: Code examples following patterns
- **Related Files**: Links to other relevant AGENTS.md files

## What's NOT Included

AGENTS.md files do NOT contain:
- ❌ Detailed API documentation (use OpenAPI/Swagger instead)
- ❌ Duplicate code from docstrings
- ❌ Temporary implementation notes
- ❌ Issue-specific details (use GitHub issues)
- ❌ Line-by-line code explanations

## Maintaining AGENTS.md Files

### When to Update

Update AGENTS.md files when:
- Adding new modules or major features
- Changing architectural patterns
- Discovering common pitfalls
- Adding new best practices
- Performing major refactoring
- Finding better ways to implement patterns

### How to Update

1. **Identify the file**: Find the AGENTS.md file for the module you're working on
2. **Add your changes**: Document new patterns, pitfalls, or best practices
3. **Keep it concise**: Focus on patterns and principles, not implementation details
4. **Include examples**: Show code examples of the pattern
5. **Link related files**: Reference other AGENTS.md files where relevant
6. **Commit changes**: AGENTS.md files are version controlled

### Template for New Modules

When creating a new module, create an AGENTS.md file:

```markdown
# Module Name - AI Agent Context

## Overview
Brief description of the module's purpose and responsibilities.

## Key Files
- `file1.py`: What it does
- `file2.py`: What it does

## Common Patterns

### Pattern Name
Description and example code.

## Best Practices
1. Do this
2. Don't do that

## Common Pitfalls
❌ Pitfall 1: Description
✅ Solution: How to avoid it

## Related Documentation
- Link to related AGENTS.md files
- Link to external docs if needed
```

## Version Control

**YES - AGENTS.md files should be committed to Git.**

These files are part of the codebase documentation and should be version controlled like any other documentation.

### Why Version Control?

1. **Team Consistency**: Everyone has access to the same context
2. **Historical Context**: See how patterns evolved over time
3. **Code Review**: Reviewers can see documentation changes
4. **Synchronization**: Documentation stays in sync with code
5. **Onboarding**: New developers get up-to-date documentation

## Benefits

### For the Team

- **Faster Onboarding**: New developers understand architecture quickly
- **Consistent Patterns**: Everyone follows the same conventions
- **Better Code Reviews**: Reviewers can reference documented patterns
- **Living Documentation**: Stays current with the codebase

### For AI Tools

- **Better Suggestions**: AI tools understand project patterns
- **Fewer Mistakes**: AI follows documented best practices
- **Consistent Style**: AI-generated code matches project style
- **Contextual Help**: AI provides relevant assistance

### For the Project

- **Knowledge Preservation**: Architectural decisions documented
- **Reduced Technical Debt**: Patterns prevent common mistakes
- **Improved Maintainability**: Clear module responsibilities
- **Easier Refactoring**: Understanding dependencies and patterns

## Examples

### Example 1: Adding a New Service

```markdown
Before implementing:
1. Read: /AGENTS.md (project overview)
2. Read: backend/rag_solution/services/AGENTS.md (service patterns)
3. Implement: Follow documented dependency injection pattern
4. Update: Add new service to AGENTS.md if it introduces new patterns
```

### Example 2: Creating a React Component

```markdown
Before implementing:
1. Read: /AGENTS.md (project overview)
2. Read: frontend/AGENTS.md (frontend architecture)
3. Read: frontend/src/components/AGENTS.md (component patterns)
4. Implement: Follow Tailwind CSS and state management patterns
5. Update: Document new pattern if component introduces one
```

## Questions?

If you have questions about the AGENTS.md system:
1. Check the root `/AGENTS.md` file for guidance
2. Look at existing AGENTS.md files for examples
3. Ask the team in Slack/Teams
4. Update this README if you think something is unclear

## Contributing

When contributing to AGENTS.md files:
- ✅ Keep explanations concise and focused
- ✅ Include code examples
- ✅ Document "why" not just "what"
- ✅ Link to related documentation
- ✅ Update when patterns change
- ❌ Don't duplicate docstrings or API docs
- ❌ Don't include implementation details
- ❌ Don't let files become stale

---

**Remember**: AGENTS.md files are living documentation. Keep them updated, and they'll help everyone (humans and AI) work more effectively!
