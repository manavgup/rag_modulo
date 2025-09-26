# Planning Phase - Implementation Planning (ACE-FCA)

## <¯ Planning Mission
You are in the **PLANNING PHASE** of ACE-FCA workflow. Create a detailed, executable implementation plan based on completed research.

## =Ë Prerequisites
-  Research phase completed (`.ralph/research_complete.md` exists)
-  Issue thoroughly understood from research phase
-  Technical approach identified
-  Dependencies and risks assessed

## =Ê Context Management Rules
- **Target Context Utilization**: 40-60%
- **Focus**: Precise, actionable implementation steps
- **Output**: Detailed plan with verification points
- **Format**: Step-by-step execution plan

## <¯ Planning Objectives
Create a comprehensive implementation plan that can be executed systematically.

### **Plan Components Required:**
1. **Implementation Steps**: Exact sequence of actions
2. **File Modifications**: Specific files to create/edit
3. **Testing Strategy**: How to verify each step works
4. **Quality Gates**: Checkpoints and verification criteria
5. **Rollback Plan**: How to undo changes if needed

## =Ë Planning Output Requirements

### **Executive Summary**
- **Issue**: Clear statement of what's being implemented
- **Approach**: High-level implementation strategy
- **Scope**: What's included and what's not
- **Timeline**: Estimated implementation phases

### **Detailed Implementation Plan**

#### **Phase 1: Foundation Setup**
```markdown
**Step 1.1: [Specific Action]**
- **Action**: Exactly what to do
- **Files**: Specific files to create/modify
- **Commands**: Exact commands to run
- **Verification**: How to verify this step worked
- **Rollback**: How to undo if needed

**Step 1.2: [Next Action]**
- [Continue pattern...]
```

#### **Phase 2: Core Implementation**
```markdown
**Step 2.1: [Specific Action]**
- **Action**: Exactly what to do
- **Files**: Files to modify with exact changes
- **Code Changes**: Specific functions/classes to implement
- **Verification**: Tests to run, behaviors to check
- **Dependencies**: What must be completed first

**Step 2.2: [Next Action]**
- [Continue pattern...]
```

#### **Phase 3: Integration & Testing**
```markdown
**Step 3.1: Integration Testing**
- **Action**: Integration test strategy
- **Test Files**: Specific test files to create/update
- **Verification**: How to verify integration works
- **Performance**: Expected performance characteristics

**Step 3.2: Quality Assurance**
- **Linting**: Run `make lint` and fix issues
- **Testing**: Run full test suite
- **Documentation**: Update relevant docs
- **Code Review**: Self-review checklist
```

### **Quality Gates & Verification**
- **After Each Phase**: Specific tests and checks to run
- **Success Criteria**: What defines successful completion
- **Failure Handling**: What to do if verification fails
- **Rollback Triggers**: When to abort and rollback

### **Risk Mitigation**
- **Technical Risks**: Specific mitigation strategies
- **Integration Risks**: How to handle conflicts
- **Performance Risks**: Monitoring and optimization plan
- **Security Considerations**: Security review checklist

### **Testing Strategy**
```markdown
**Unit Tests**
- [ ] Test file: `tests/path/test_feature.py`
- [ ] Test coverage: >90% for new code
- [ ] Test cases: [List specific test cases]

**Integration Tests**
- [ ] Test file: `tests/integration/test_feature_integration.py`
- [ ] Test scenarios: [List integration scenarios]

**End-to-End Tests**
- [ ] User workflow testing
- [ ] Performance testing
- [ ] Error handling testing
```

##  Planning Completion Signal
When planning is complete, create a file: `.ralph/plan_complete.md` with:
```markdown
# Planning Complete - Issue #XXX

## Implementation Plan Summary
[One paragraph summary of the implementation approach]

## Plan Verification
 Step-by-step implementation plan created
 All files and changes specified
 Testing strategy defined
 Quality gates identified
 Risk mitigation planned
 Verification criteria clear

## Implementation Phases
1. **Phase 1**: [Brief description] - [X steps]
2. **Phase 2**: [Brief description] - [X steps]
3. **Phase 3**: [Brief description] - [X steps]

## Ready for Implementation
Plan is detailed, executable, and ready for systematic implementation.

## Next Phase
Ready to proceed to IMPLEMENTATION phase.
```

## <¯ Planning Best Practices
- **Be Specific**: Exact files, functions, commands
- **Be Systematic**: Logical step progression
- **Be Verifiable**: Each step has clear success criteria
- **Be Recoverable**: Clear rollback for each step
- **Be Realistic**: Achievable steps with proper estimates

## =Ý Human Review Required
This is a **high human engagement phase**. Review the plan carefully before implementation:
- Does the plan make sense technically?
- Are all steps clearly defined?
- Are verification criteria realistic?
- Are risks properly addressed?

Begin creating your detailed implementation plan now.
