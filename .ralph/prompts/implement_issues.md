# Implementation Phase - Execute Plan (ACE-FCA)

## <¯ Implementation Mission
You are in the **IMPLEMENTATION PHASE** of ACE-FCA workflow. Execute the detailed plan created in the planning phase systematically with continuous verification.

## =Ë Prerequisites
-  Research phase completed (`.ralph/research_complete.md` exists)
-  Planning phase completed (`.ralph/plan_complete.md` exists)
-  Detailed implementation plan available
-  All dependencies and requirements understood

## =Ê Context Management Rules
- **Target Context Utilization**: 40-60%
- **Focus**: Systematic execution with verification
- **Progress**: Implement ’ Verify ’ Update context ’ Next step
- **Format**: Track progress with completion checkmarks

## ¡ Implementation Approach
Execute the plan step-by-step with continuous verification and context updates.

### **Implementation Workflow:**
1. **Execute Step**: Follow the plan exactly as written
2. **Verify Completion**: Run specified tests/verification
3. **Update Progress**: Mark step complete and update context
4. **Quality Gate**: Run lint/tests before proceeding
5. **Context Compact**: Compress progress into key insights

## =Ë Current Implementation Status

### **Plan Execution Checklist**
```markdown
## Phase 1: Foundation Setup
- [ ] Step 1.1: [Action from plan] - Status: [Not started/In progress/Complete/Failed]
- [ ] Step 1.2: [Action from plan] - Status: [Not started/In progress/Complete/Failed]
- [ ] Step 1.3: [Action from plan] - Status: [Not started/In progress/Complete/Failed]

## Phase 2: Core Implementation
- [ ] Step 2.1: [Action from plan] - Status: [Not started/In progress/Complete/Failed]
- [ ] Step 2.2: [Action from plan] - Status: [Not started/In progress/Complete/Failed]

## Phase 3: Integration & Testing
- [ ] Step 3.1: [Action from plan] - Status: [Not started/In progress/Complete/Failed]
- [ ] Step 3.2: [Action from plan] - Status: [Not started/In progress/Complete/Failed]
```

## =' Implementation Guidelines

### **Step Execution Process**
1. **Read Plan Step**: Understand exactly what needs to be done
2. **Prepare Environment**: Ensure all prerequisites are met
3. **Execute Action**: Perform the specific action described
4. **Run Verification**: Execute the verification criteria from plan
5. **Update Status**: Mark step as complete or identify issues
6. **Context Update**: Update `.ralph/current_context.md` with progress

### **Quality Gates (Run After Each Step)**
```bash
# Quality verification commands
make lint                    # Code style and formatting
make test-unit-fast         # Unit tests (if available)
git status                  # Check working directory
git diff                    # Review changes made
```

### **Error Handling**
If a step fails:
1. **Stop Implementation**: Don't proceed to next step
2. **Analyze Failure**: Understand what went wrong
3. **Check Rollback**: Use rollback plan if necessary
4. **Update Context**: Document the failure and analysis
5. **Request Help**: If stuck, ask for clarification or assistance

## =Ý Progress Tracking

### **After Each Step Completion**
Update `.ralph/current_context.md` with:
```markdown
## Latest Progress - [Timestamp]
**Current Step**: [Step number and description]
**Status**: Complete/Failed
**Changes Made**: [Brief description of what was implemented]
**Verification**: [Results of verification tests]
**Next Step**: [What comes next]

## Key Implementation Insights
- [Important finding 1]
- [Important finding 2]
- [Important challenge encountered]
```

### **Context Compaction Rules**
- Keep only the most recent 3-5 steps in context
- Focus on current implementation challenges
- Highlight any deviations from the original plan
- Maintain awareness of overall progress toward issue completion

##  Implementation Completion Signal
When implementation is complete, create a file: `.ralph/implementation_complete.md` with:
```markdown
# Implementation Complete - Issue #XXX

## Implementation Summary
[One paragraph describing what was implemented]

## Completed Features
- [Feature 1 with verification status]
- [Feature 2 with verification status]
- [Feature 3 with verification status]

## Quality Verification
 All implementation steps completed
 Lint checks passing
 Unit tests passing (if applicable)
 Integration tests passing (if applicable)
 Manual verification completed
 Documentation updated
 Code reviewed

## Files Modified
- [List of files created/modified]
- [Brief description of changes in each]

## Testing Completed
- [Unit tests: X tests added/passing]
- [Integration tests: X scenarios verified]
- [Manual testing: X workflows verified]

## Issue Resolution
 All acceptance criteria met
 Implementation matches plan
 Quality standards maintained
 Ready for code review/merge

## Next Steps
Issue #XXX is complete and ready for the next issue in the queue.
```

## =¨ Critical Implementation Rules

### **Do Not Skip Steps**
- Execute the plan exactly as written
- Don't jump ahead or skip verification
- If plan needs modification, update it first

### **Verify Everything**
- Run verification criteria after each step
- Don't assume something works without testing
- Document verification results

### **Maintain Quality**
- Run lint and tests frequently
- Keep code style consistent
- Add tests for new functionality

### **Track Progress**
- Update context after each step
- Document any deviations from plan
- Keep stakeholders informed of progress

Begin systematic implementation now. Focus on one step at a time with thorough verification.
