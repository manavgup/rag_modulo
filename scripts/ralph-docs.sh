#!/usr/bin/env bash
set -euo pipefail

RALPH_DIR=.ralph
PHASES_DIR="$RALPH_DIR/phases"
COMPACT_DIR="$RALPH_DIR/compacted"
LOGS_DIR="$RALPH_DIR/logs"
mkdir -p "$PHASES_DIR" "$COMPACT_DIR" "$LOGS_DIR"

# Function to run documentation research
run_docs_research() {
    local research_file="$PHASES_DIR/docs_research_$(date +%s).md"

    echo "🔍 Starting Documentation Research Phase..."

    # Create research prompt
    cp "$RALPH_DIR/prompts/research_documentation.md" "$research_file"

    # Run research
    while :; do
        echo "$(date): Documentation research iteration..."
        cat "$research_file" | npx --yes @sourcegraph/amp 2>&1 | tee -a "$LOGS_DIR/docs_research.log"

        if grep -q "Next Steps:" "$LOGS_DIR/docs_research.log"; then
            echo "✅ Documentation research phase completed"
            break
        fi
        sleep 30
    done
}

# Function to run documentation planning
run_docs_planning() {
    local plan_file="$PHASES_DIR/docs_plan_$(date +%s).md"

    echo "📋 Starting Documentation Planning Phase..."

    # Create planning prompt
    cp "$RALPH_DIR/prompts/plan_documentation.md" "$plan_file"

    # Run planning
    while :; do
        echo "$(date): Documentation planning iteration..."
        cat "$plan_file" | npx --yes @sourcegraph/amp 2>&1 | tee -a "$LOGS_DIR/docs_planning.log"

        if grep -q "Phase 3:" "$LOGS_DIR/docs_planning.log"; then
            echo "✅ Documentation planning phase completed"
            break
        fi
        sleep 30
    done
}

# Function to run documentation implementation
run_docs_implementation() {
    local impl_file="$PHASES_DIR/docs_impl_$(date +%s).md"

    echo "🚀 Starting Documentation Implementation Phase..."

    # Create implementation prompt
    cp "$RALPH_DIR/prompts/implement_documentation.md" "$impl_file"

    # Run implementation
    while :; do
        echo "$(date): Documentation implementation iteration..."
        cat "$impl_file" | npx --yes @sourcegraph/amp 2>&1 | tee -a "$LOGS_DIR/docs_implementation.log"

        if grep -q "Documentation completed" "$LOGS_DIR/docs_implementation.log"; then
            echo "✅ Documentation implementation phase completed"
            break
        fi
        sleep 60
    done
}

# Function to run full documentation workflow
run_docs_workflow() {
    echo "🚀 Starting Documentation Workflow with Ralph"

    # Phase 1: Documentation Research
    run_docs_research

    # Phase 2: Documentation Planning
    run_docs_planning

    # Phase 3: Documentation Implementation
    run_docs_implementation

    echo "✅ Documentation workflow completed"
}

case "${1:-}" in
    research) run_docs_research;;
    plan) run_docs_planning;;
    implement) run_docs_implementation;;
    full) run_docs_workflow;;
    *) echo "Usage: $0 {research|plan|implement|full}"; exit 1;;
esac
