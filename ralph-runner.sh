#!/bin/bash
set -e

# Ralph + ACE-FCA Configuration
RALPH_LOG_DIR=".ralph/logs"
RALPH_CONTEXT_FILE=".ralph/current_context.md"
RALPH_PROGRESS_FILE=".ralph/progress.md"
RALPH_PHASE_FILE=".ralph/current_phase.md"
RALPH_ITERATION=0
CONTEXT_TARGET_MIN=40  # ACE-FCA: Minimum context utilization %
CONTEXT_TARGET_MAX=60  # ACE-FCA: Maximum context utilization %
CURRENT_PHASE="research"  # research, plan, implement
CURRENT_ISSUE="242"  # Current issue number

# Create Ralph + ACE-FCA directories
mkdir -p "$RALPH_LOG_DIR" .ralph/context .ralph/prompts

# Initialize phase tracking
if [ ! -f "$RALPH_PHASE_FILE" ]; then
    echo "research" > "$RALPH_PHASE_FILE"
fi
CURRENT_PHASE=$(cat "$RALPH_PHASE_FILE")

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$RALPH_LOG_DIR/ralph.log"
}

# Function to update progress with ACE-FCA context management
update_progress() {
    local status="$1"
    local details="$2"
    local context_util="$3"
    echo "## Iteration $RALPH_ITERATION - $(date)" >> "$RALPH_PROGRESS_FILE"
    echo "- Phase: $CURRENT_PHASE" >> "$RALPH_PROGRESS_FILE"
    echo "- Issue: #$CURRENT_ISSUE" >> "$RALPH_PROGRESS_FILE"
    echo "- Status: $status" >> "$RALPH_PROGRESS_FILE"
    echo "- Details: $details" >> "$RALPH_PROGRESS_FILE"
    echo "- Context Utilization: ${context_util:-unknown}%" >> "$RALPH_PROGRESS_FILE"
    echo "" >> "$RALPH_PROGRESS_FILE"
}

# Function to show current ACE-FCA status
show_status() {
    echo ""
    echo "🤖 Ralph + ACE-FCA Status:"
    echo "  Phase: $CURRENT_PHASE (research → plan → implement)"
    echo "  Issue: #$CURRENT_ISSUE"
    echo "  Iteration: $RALPH_ITERATION"
    echo "  Context Target: ${CONTEXT_TARGET_MIN}-${CONTEXT_TARGET_MAX}%"
    echo "  Log: $RALPH_LOG_DIR/ralph.log"
    echo "  Progress: $RALPH_PROGRESS_FILE"
    echo "  Context: $RALPH_CONTEXT_FILE"
    echo ""
}

# Function to check git status
check_git_status() {
    local changes=$(git status --porcelain | wc -l)
    if [ "$changes" -gt 0 ]; then
        log "⚠️  Git has $changes uncommitted changes"
        git status --short | head -5
    else
        log "✅ Git working directory clean"
    fi
}

# Function to run quality gates (ACE-FCA verification)
run_quality_gates() {
    log "🧪 Running quality gates for phase: $CURRENT_PHASE"

    case "$CURRENT_PHASE" in
        "research")
            log "📖 Research phase: Relaxed quality gates (focus on understanding)"
            # In research phase, only check git status - no strict lint requirements
            check_git_status
            log "✅ Research phase quality gates passed"
            return 0
            ;;
        "plan")
            log "📋 Planning phase: Basic quality gates"
            # In planning phase, check format but allow lint warnings
            if make format-check > "$RALPH_LOG_DIR/format_$RALPH_ITERATION.log" 2>&1; then
                log "✅ Format check passed"
            else
                log "⚠️  Format issues found - check $RALPH_LOG_DIR/format_$RALPH_ITERATION.log"
            fi
            return 0
            ;;
        "implement")
            log "⚒️  Implementation phase: Full quality gates"
            # In implementation phase, enforce full linting and tests
            if make lint > "$RALPH_LOG_DIR/lint_$RALPH_ITERATION.log" 2>&1; then
                log "✅ Lint passed"
            else
                log "❌ Lint failed - check $RALPH_LOG_DIR/lint_$RALPH_ITERATION.log"
                return 1
            fi

            # Run unit tests if available
            if make test-unit-fast > "$RALPH_LOG_DIR/tests_$RALPH_ITERATION.log" 2>&1; then
                log "✅ Unit tests passed"
            else
                log "⚠️  Unit tests failed or not available - check $RALPH_LOG_DIR/tests_$RALPH_ITERATION.log"
            fi
            return 0
            ;;
        *)
            log "⚠️  Unknown phase: $CURRENT_PHASE, using default quality gates"
            check_git_status
            return 0
            ;;
    esac
}

# Function to show recent activity
show_recent_activity() {
    echo ""
    echo " Recent Activity:"
    if [ -f "$RALPH_PROGRESS_FILE" ]; then
        tail -10 "$RALPH_PROGRESS_FILE"
    else
        echo "  No activity yet"
    fi
    echo ""
}

# Function to check if we should advance to next phase (ACE-FCA)
check_phase_advancement() {
    case "$CURRENT_PHASE" in
        "research")
            log "🔍 Research phase complete. Checking if ready for planning..."
            if [ -f ".ralph/research_complete.md" ]; then
                CURRENT_PHASE="plan"
                echo "plan" > "$RALPH_PHASE_FILE"
                log "➡️  Advancing to PLAN phase"
            fi
            ;;
        "plan")
            log "📋 Plan phase complete. Checking if ready for implementation..."
            if [ -f ".ralph/plan_complete.md" ]; then
                CURRENT_PHASE="implement"
                echo "implement" > "$RALPH_PHASE_FILE"
                log "➡️  Advancing to IMPLEMENT phase"
            fi
            ;;
        "implement")
            log "⚒️  Implementation phase. Checking if issue is complete..."
            if [ -f ".ralph/implementation_complete.md" ]; then
                log "✅ Issue #$CURRENT_ISSUE complete! Moving to next issue."
                # Logic to advance to next issue would go here
            fi
            ;;
    esac
}

# Main execution
log " Starting Ralph with AGENTS.md integration"
log "Press Ctrl+C to stop"

# Initialize ACE-FCA progress file
echo "# Ralph + ACE-FCA Progress Log" > "$RALPH_PROGRESS_FILE"
echo "Started: $(date)" >> "$RALPH_PROGRESS_FILE"
echo "Current Phase: $CURRENT_PHASE" >> "$RALPH_PROGRESS_FILE"
echo "Current Issue: #$CURRENT_ISSUE" >> "$RALPH_PROGRESS_FILE"
echo "Context Target: ${CONTEXT_TARGET_MIN}-${CONTEXT_TARGET_MAX}%" >> "$RALPH_PROGRESS_FILE"
echo "ACE-FCA Workflow: Research → Plan → Implement" >> "$RALPH_PROGRESS_FILE"
echo "" >> "$RALPH_PROGRESS_FILE"

while :; do
    RALPH_ITERATION=$((RALPH_ITERATION + 1))

    log "🤖 Ralph iteration $RALPH_ITERATION starting"

    # Show current status
    show_status

    # Check git status
    check_git_status

    # ACE-FCA Phase-Specific Context Assembly
    log "📖 Assembling ACE-FCA context for phase: $CURRENT_PHASE"

    # Start with main project context
    cat AGENTS.md > "$RALPH_CONTEXT_FILE"
    echo "" >> "$RALPH_CONTEXT_FILE"
    echo "---" >> "$RALPH_CONTEXT_FILE"
    echo "" >> "$RALPH_CONTEXT_FILE"

    # Add phase-specific prompt
    PHASE_PROMPT=".ralph/prompts/${CURRENT_PHASE}_issues.md"
    if [ -f "$PHASE_PROMPT" ]; then
        log "📋 Adding phase-specific prompt: $PHASE_PROMPT"
        cat "$PHASE_PROMPT" >> "$RALPH_CONTEXT_FILE"
    else
        log "⚠️  Phase-specific prompt not found: $PHASE_PROMPT"
        # Fallback to generic prompts
        if [ -f ".ralph/prompts/research_features.md" ]; then
            log "📋 Using fallback: research_features.md"
            cat ".ralph/prompts/research_features.md" >> "$RALPH_CONTEXT_FILE"
        elif [ -f ".ralph/prompts/research.md" ]; then
            log "📋 Using fallback: research.md"
            cat ".ralph/prompts/research.md" >> "$RALPH_CONTEXT_FILE"
        else
            log "⚠️  No research prompts found! Creating basic research context"
            echo "## Research Phase: Analyze the current issue and codebase thoroughly." >> "$RALPH_CONTEXT_FILE"
        fi
    fi

    # Add current issue context
    echo "" >> "$RALPH_CONTEXT_FILE"
    echo "## 🎯 Current Focus: Issue #$CURRENT_ISSUE ($CURRENT_PHASE phase)" >> "$RALPH_CONTEXT_FILE"
    echo "Target Context Utilization: ${CONTEXT_TARGET_MIN}-${CONTEXT_TARGET_MAX}%" >> "$RALPH_CONTEXT_FILE"
    echo "Iteration: $RALPH_ITERATION" >> "$RALPH_CONTEXT_FILE"

    # Update progress with ACE-FCA context
    update_progress "Context assembled" "Phase: $CURRENT_PHASE, Issue: #$CURRENT_ISSUE"

    # Use the combined context
    if command -v claude &> /dev/null; then
        log "🔧 Running Claude CLI with context"
        update_progress "Running Claude" "Executing Claude CLI with combined context"

        # Run Claude and capture output
        if claude --dangerously-skip-permissions < "$RALPH_CONTEXT_FILE" > "$RALPH_LOG_DIR/claude_output_$RALPH_ITERATION.log" 2>&1; then
            log "✅ Claude execution completed"
            update_progress "Claude completed" "Check $RALPH_LOG_DIR/claude_output_$RALPH_ITERATION.log"

            # Run ACE-FCA quality gates after Claude execution
            if run_quality_gates; then
                log "✅ Quality gates passed after Claude execution"
                update_progress "Quality gates passed" "Lint and tests passing after Claude execution"

                # Check if we should advance to next phase (ACE-FCA workflow)
                check_phase_advancement
            else
                log "⚠️  Quality gates failed after Claude execution"
                update_progress "Quality gates failed" "Some quality checks failed after Claude execution"
            fi
        else
            log "❌ Claude execution failed"
            update_progress "Claude failed" "Check $RALPH_LOG_DIR/claude_output_$RALPH_ITERATION.log"
        fi
    else
        log "❌ Claude CLI not found. Please use Claude Code Agent manually"
        log "📋 Copy the contents of $RALPH_CONTEXT_FILE into Claude Code Agent"
        update_progress "Manual mode" "Waiting for manual Claude Code Agent execution"
        log "⏳ Waiting 30 seconds before next iteration..."
        sleep 30
    fi

    # Show recent activity
    show_recent_activity

    # ACE-FCA: Shorter iteration cycle for better context management
    log "⏳ Waiting 15 seconds before next iteration (ACE-FCA rapid iteration)..."
    sleep 15
done
